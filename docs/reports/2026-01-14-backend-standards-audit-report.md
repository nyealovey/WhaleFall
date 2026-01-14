> Status: Draft (static audit)
> Owner: Codex (后端标准审计员/代码合规审计员)
> Created: 2026-01-14
> Updated: 2026-01-14
> Scope:
> - Standards: `docs/Obsidian/standards/backend/**/*.md`（全量）
> - Code (strict): `app/**/*.py`（全量静态扫描；不扫描/不判定 `app/**` 之外任何代码）
> Related:
> - `docs/Obsidian/standards/backend/README.md`
> - `docs/Obsidian/standards/backend/layer/api-layer-standards.md`
> - `docs/Obsidian/standards/backend/layer/services-layer-standards.md`
> - `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md`
> - `docs/Obsidian/standards/backend/write-operation-boundary.md`
> - `docs/Obsidian/standards/backend/error-message-schema-unification.md`
> - `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md`
> - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md`

# 后端标准全量审计报告 (2026-01-14)

## 1. 目标

1) 找出后端标准内部的冲突/歧义/不可执行点（以 MUST/MUST NOT/SHOULD 为核心证据）。
2) 基于“明确强约束”（MUST/MUST NOT/等价强制措辞），识别 `app/**/*.py` 内需修复的违规行为，并为每条提供：
   - 标准依据：`标准文件:行号`
   - 代码位置：`app/...:行号`
3) 盘点 `app/**/*.py` 内的防御/兼容/回退/适配逻辑（重点：`or`/truthy 兜底链、数据结构兼容、版本化/迁移/序列化形状稳定）。

## 2. 审计方法与证据

### 2.1 已执行的仓库门禁脚本

本次为“只读静态审计”，未执行会扫描 `app/**` 之外路径的门禁脚本；仅执行了可限制到 `app/**` 的补充静态分析：

- Ruff（仅 `app/**`）：`uv run ruff check app`
  - 结果：发现 87 个问题（其中 51 个可自动修复；本次审计不改代码）。
- Pyright（仅 `app/**`）：`uv run pyright app`
  - 结果：6 个类型错误（主要集中在 `safe_call(context=...)` 的上下文类型与脱敏函数入参类型）。

> 说明：Ruff/Pyright 的问题不等价于“后端标准违规”。本报告仅在能回链到后端标准强约束时，才在 “## 4” 标注为“违规需要修复”；否则放入“疑似问题/建议改进”。

### 2.2 已执行的补充静态扫描

使用 `rg -n` 对 `app/**/*.py` 做了强约束相关的针对性定位（仅列出与本报告结论直接相关的扫描项）：

- 事务边界（commit/rollback 漂移）
  - `rg -n "db\\.session\\.(commit|rollback)\\(" app --glob "app/**/*.py"`
- DB 直连（Routes/API/Tasks 不应直接查库/写入）
  - `rg -n "Model\\.query|db\\.session|session\\.execute\\(" app/routes app/api app/tasks --glob "app/**/*.py"`
- 环境变量读取漂移（禁止业务模块 `os.environ.get/os.getenv`）
  - `rg -n "os\\.(environ\\.get|getenv)\\(" app --glob "app/**/*.py"`
- 错误字段互兜底链（禁止 `error/message`、`message_code/error_code` 互兜底）
  - `rg -n --pcre2 "\\.get\\(['\\\"]error['\\\"]\\)\\s*or\\s*\\.get\\(['\\\"]message['\\\"]\\)" app --glob "app/**/*.py"`

### 2.3 AST 语义扫描

为避免只靠 grep 漏掉“非字符串形态”的兜底逻辑，本次做了 AST 扫描（仅 `app/**/*.py`）：

- `or` 兜底（过滤掉 `if/while` 条件表达式，仅统计“值语境”的 `x or y`）：
  - 总计 643 处（按粗分类型：`.get` 兜底 143；`or ""` 122；`or 0/数字` 100；`or {}` 53；`or []` 32；`or None` 14；其他 179）
- 宽泛异常捕获（`except Exception/BaseException/bare except`）：
  - 总计 65 处，其中 18 处为“非 raise”分支（返回兜底值/continue/吞掉异常等），需要重点对齐 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50` 的可观测性要求。

### 2.4 可执行约束索引（摘要）

> 本索引只收敛“可执行约束”（尤其 MUST/MUST NOT），用于支撑后续“标准→代码”的映射；不复述 SHOULD 的建议项。

| 主题 | 可执行约束摘要 | 标准位置 | 影响范围 | 典型反例 |
|---|---|---|---|---|
| API 职责边界 | API 只做端点/参数解析/校验/调用 Service；禁止在 API 里写复杂业务/直连 DB | `docs/Obsidian/standards/backend/layer/api-layer-standards.md:46` `docs/Obsidian/standards/backend/layer/api-layer-standards.md:47` `docs/Obsidian/standards/backend/layer/api-layer-standards.md:48` | `app/api/**` | API 内 `Model.query` / 复杂编排 |
| API 写路径校验分层 | 写路径 `@ns.expect(Model)` 必须 `validate=False`；字段级校验/类型转换/兼容策略必须落在 `app/schemas/**`，禁止 API 手写 `data.get(...) or .../strip/int` | `docs/Obsidian/standards/backend/layer/api-layer-standards.md:67` `docs/Obsidian/standards/backend/layer/api-layer-standards.md:68` | `app/api/v1/**` + `app/schemas/**` | API 内 `int(data.get(...))` |
| 统一响应封套 | 成功/失败 JSON 必须走统一封套；禁止业务代码手写 `{success:..., error:...}` 结构 | `docs/Obsidian/standards/backend/layer/api-layer-standards.md:113` `docs/Obsidian/standards/backend/layer/api-layer-standards.md:116` `docs/Obsidian/standards/backend/layer/api-layer-standards.md:117` | `app/api/**` `app/routes/**` | `return jsonify({\"success\": False, ...})` |
| 错误字段统一 | 对外 error envelope 禁止出现 `error_code`（含 `extra`）；业务代码禁止写 `error/message` 或 `message_code/error_code` 互兜底链 | `docs/Obsidian/standards/backend/error-message-schema-unification.md:38` `docs/Obsidian/standards/backend/error-message-schema-unification.md:39` `docs/Obsidian/standards/backend/error-message-schema-unification.md:43` `docs/Obsidian/standards/backend/error-message-schema-unification.md:46` `docs/Obsidian/standards/backend/error-message-schema-unification.md:48` | 全层（尤其 API/错误处理） | `payload.get(\"message_code\") or payload.get(\"error_code\")` |
| 写操作事务边界 | commit/rollback 只允许在提交点（`safe_route_call`/tasks/worker）；其余层禁止直接 commit/rollback | `docs/Obsidian/standards/backend/write-operation-boundary.md:21` `docs/Obsidian/standards/backend/write-operation-boundary.md:22` | 全层 | Service 内 `db.session.commit()` |
| Service 职责边界 | Service 必须通过 `app.repositories.*` 做数据访问与 Query 组装 | `docs/Obsidian/standards/backend/layer/services-layer-standards.md:44` | `app/services/**` | Service 内 `db.session.add(...)` / `Model.query` |
| 回退/降级可观测性 | 任何 fallback/workaround/partial failure 必须结构化日志包含 `fallback=true` 与 `fallback_reason`；禁止 silent fallback | `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:47` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:48` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:59` | 全层（services/infra/tasks/routes） | `except Exception: return default` 且不记录 |
| Schema 依赖边界 | schema 禁止依赖 models/services/repositories/db.session | `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md:44` `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md:45` | `app/schemas/**` | schema 内 `from app.models...` |
| Internal Contract 版本化 | 内部结构化 payload 必须显式 `version`；未知版本默认 fail-fast（或 best-effort 返回统一错误结构） | `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54` `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:58` `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:59` `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:60` `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:65` | 内部 JSON payload（snapshot/cache/JSON column） | 未带 version 的 snapshot 被下游 `or {}` 吞掉 |
| Settings 单一真源 | 配置读取收敛到 `app/settings.py`，业务模块禁止 `os.environ.get`；对可能合法为 `0/\"\"/[]` 的配置值禁止 `or` 兜底 | `docs/Obsidian/standards/backend/configuration-and-secrets.md:36` `docs/Obsidian/standards/backend/configuration-and-secrets.md:38` `docs/Obsidian/standards/backend/configuration-and-secrets.md:69` | `app/settings.py` + 全层 | 业务代码 `os.environ.get(...)` / `timeout or 30` |
| Tasks 上下文边界 | 请求上下文外运行的任务必须在 `app.app_context()` 中执行 | `docs/Obsidian/standards/backend/task-and-scheduler.md:34` `docs/Obsidian/standards/backend/task-and-scheduler.md:37` | `app/tasks/**` | 任务里直接 `Model.query` 且无 app_context |

## 3. 标准冲突或歧义

### 3.1 `or` 兜底“强度口径”不一致（MUST NOT vs SHOULD）

- 证据：
  - Settings/Config 明确为 MUST NOT：`docs/Obsidian/standards/backend/layer/settings-layer-standards.md:60`
  - 配置与密钥明确为 MUST NOT：`docs/Obsidian/standards/backend/configuration-and-secrets.md:69`
  - 但回退/内部契约中写为 SHOULD（且用词仍是“禁止”）：`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:78`、`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:114`
- 影响：
  - 同一主题（“合法空值是否可被 `or` 覆盖”）在不同标准中强度不同，导致评审/门禁难以形成一致判定；下游实现会出现“有的地方严格 is None，有的地方继续用 `or`”的漂移。
- 建议：
  - 统一措辞与强度：要么将相关条款统一为 MUST NOT，要么保留 SHOULD 但删除“禁止”字样并明确 scope（例如仅对 Settings 为 MUST NOT，其余为 SHOULD）。

### 3.2 Error Envelope 必填字段缺少可执行枚举/来源（`category`/`severity`）

- 证据：失败封套要求 `category` 与 `severity` 必填，但未给出枚举或落点：`docs/Obsidian/standards/backend/layer/api-layer-standards.md:136` `docs/Obsidian/standards/backend/layer/api-layer-standards.md:137`
- 影响：
  - 产生方只能“凭感觉”造字符串，后续会形成不可治理的口径分裂（统计/告警维度失真）。
- 建议：
  - 在 `app/core/constants/**` 固化枚举（例如 `ErrorCategory`/`ErrorSeverity`），并在错误映射/统一错误处理器提供单入口映射；标准文档引用该枚举为单一真源。

### 3.3 “密钥读取工具封装层”例外不可执行（缺少 allowlist）

- 证据：业务模块禁止 `os.environ.get`，但允许“密钥读取工具封装层”例外，且要求“在本文件明确记录”：`docs/Obsidian/standards/backend/configuration-and-secrets.md:38`
- 问题：
  - 标准本身未列出“哪些模块属于例外”，导致落地时无法审计、无法门禁化（也无法避免新增 silent fallback）。
- 建议：
  - 在 `configuration-and-secrets.md` 增加 allowlist（模块路径 + 理由 + 删除条件），并同步对齐 `docs/Obsidian/standards/backend/layer/settings-layer-standards.md:43` 的表述。

### 3.4 “复杂业务逻辑”的判定边界偏模糊（强约束但缺少 checklist）

- 证据：
  - API 层 MUST NOT “复杂业务逻辑”：`docs/Obsidian/standards/backend/layer/api-layer-standards.md:47`
  - Routes 层 MUST NOT “复杂业务逻辑”：`docs/Obsidian/standards/backend/layer/routes-layer-standards.md:43`
- 问题：
  - 虽给了示例，但缺少可执行 checklist（例如“允许的编排深度/允许调用次数/是否允许循环+写入”等），评审容易出现多解。
- 建议：
  - 将“复杂”拆为可检查条目（例如：是否出现循环+写、是否出现跨实体聚合、是否出现权限规则、是否出现事务语义决策等），并给出 3-5 个可复制的正例模板。

### 3.5 “`parse_payload` 一次链路只允许执行一次”缺少可验证门禁

- 证据：`parse_payload` MUST 只执行一次：`docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:38`；API 标准重复强调：`docs/Obsidian/standards/backend/layer/api-layer-standards.md:70`
- 问题：
  - 当前缺少可执行门禁（例如 request-scope marker 或统一 wrapper），只能依赖人工 review，容易出现“API parse + Service parse”双重解析导致语义漂移。
- 建议：
  - 增加轻量门禁：在 `parse_payload` 内写入 request-scope 标记（例如 `flask.g`/contextvars），二次调用直接抛错或写结构化 warning（需明确策略）。

## 4. 不符合标准的代码行为(需要修复)

> 仅在“标准为明确强约束 + 证据清晰”时标注为违规。

### 4.1 回退/降级/partial failure 存在但日志缺少 `fallback=true`/`fallback_reason`

- 标准依据：
  - `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:47` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:48`
  - `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:59`（partial failure 也算 fallback）
  - Service 关键路径 checklist：`docs/Obsidian/standards/backend/layer/services-layer-standards.md:166` `docs/Obsidian/standards/backend/layer/services-layer-standards.md:170`
- 违规代码位置（示例，均为“异常→兜底值/继续执行”的回退分支）：
  - `app/services/sync_session_service.py:435`（异常时返回 `[]`，日志未包含 `fallback=true/fallback_reason`）
  - `app/services/accounts_sync/permission_manager.py:509`（构建 facts 失败后写入兜底 `permission_facts`，日志未包含 `fallback=true/fallback_reason`）
  - `app/tasks/capacity_collection_tasks.py:56`（循环中单项失败后继续执行；日志未包含 `fallback=true/fallback_reason`）
  - `app/infra/database_batch_manager.py:168`（循环中单项失败后 continue；日志未包含 `fallback=true/fallback_reason`）
- 修复建议：
  - 统一改为调用 `app/infra/route_safety.py:78` 的 `log_fallback(...)`（或等价地在现有日志里补齐 `fallback=true` 与 `fallback_reason`）。
  - 对 “返回 `[]/{}` 继续跑” 的 best-effort 路径，补齐 docstring 的语义声明（为什么允许 best-effort、什么场景必须 fail-fast）。

### 4.2 存在 silent fallback（吞异常并返回兜底，不记录任何日志/告警）

- 标准依据：`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50`
- 违规代码位置：
  - `app/views/mixins/resource_forms.py:252`（`url_for` 异常被吞并直接回退首页，无任何结构化日志）
  - `app/services/connection_adapters/adapters/oracle_adapter.py:66`（探测 `oracledb.is_thin()` 异常被吞并，静默回退为 `is_thin=False`）
- 修复建议：
  - 以“低噪音”方式补齐可观测性：至少 `log_fallback(..., fallback_reason=exc.__class__.__name__)`，并避免记录敏感信息（见 `docs/Obsidian/standards/backend/sensitive-data-handling.md:36`）。

### 4.3 Service 层未通过 Repository 组织数据写入（直接使用 `db.session.add/delete/flush`）

- 标准依据：
  - Service 必须通过 Repository 执行数据访问：`docs/Obsidian/standards/backend/layer/services-layer-standards.md:44`
- 违规代码位置（示例，Service 内直接写 session）：
  - `app/services/auth/change_password_service.py:43`
  - `app/services/sync_session_service.py:102`
  - `app/services/accounts_sync/inventory_manager.py:87`
  - `app/services/database_sync/inventory_manager.py:194`
  - `app/services/instances/batch_service.py:194`
  - `app/services/instances/batch_service.py:317`
- 修复建议：
  - 将 `add/delete/flush` 收敛到对应 `app/repositories/**`（Repository 提供稳定方法；Service 只做编排/语义决策）。
  - 若存在“历史原因必须在 Service 直接写 session”的例外，请在标准中补充明确例外条款与门禁判据（否则按 MUST 视为违规）。

## 5. 符合标准的关键点(通过项摘要)

### 5.1 API/Routers/事务边界

- API 层未发现 `Model.query/db.session/原生 SQL` 直连（对齐 `docs/Obsidian/standards/backend/layer/api-layer-standards.md:48`）。
- API 写路径 `@ns.expect(Model)` 均显式 `validate=False`（对齐 `docs/Obsidian/standards/backend/layer/api-layer-standards.md:67`）。
- Routes 层路由文件均出现 `safe_route_call(...)`（对齐 `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:48`）。
- `app/services/**` 与 `app/repositories/**` 未发现 `db.session.commit/rollback`（对齐 `docs/Obsidian/standards/backend/write-operation-boundary.md:21` `docs/Obsidian/standards/backend/write-operation-boundary.md:22`）。

### 5.2 Schema/Settings/错误字段治理

- `app/schemas/**` 未发现对 `app.models/app.services/app.repositories/db.session` 的依赖（对齐 `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md:44` `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md:45`）。
- 未发现 `error/message` 或 `message_code/error_code` 互兜底链（对齐 `docs/Obsidian/standards/backend/error-message-schema-unification.md:43` `docs/Obsidian/standards/backend/error-message-schema-unification.md:46`）。
- `app/**` 未发现 `os.environ.get/os.getenv` 配置读取漂移（对齐 `docs/Obsidian/standards/backend/configuration-and-secrets.md:38` 与 `docs/Obsidian/standards/backend/layer/settings-layer-standards.md:43`）。

### 5.3 Internal Contract 版本化

- 已存在 internal contract 单入口适配：`app/schemas/internal_contracts/permission_snapshot_v4.py:42`（包含显式 `version` 判定与“未知版本→错误结构”的 best-effort 返回），整体对齐 `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54` `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:58` `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:60` `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:65`。

## 6. 防御/兼容/回退/适配逻辑清单(重点: or 兜底)

> 说明：
> - 本节仅覆盖 `app/**/*.py`。
> - “or 兜底”分为：合理回退（语义明确且不覆盖合法空值）与危险兜底（覆盖合法空值/引入隐式优先级/掩盖错误）。
> - 输出格式：位置 / 类型 / 描述 / 建议。

### 6.1 数据结构版本化/兼容（Internal Contract）

- 位置：`app/schemas/internal_contracts/permission_snapshot_v4.py:42`
  - 类型：适配/版本化/单入口 canonicalization
  - 描述：internal contract 读入口显式校验 `version`，未知版本返回统一错误结构（而非下游 `or {}` 静默兜底），避免业务层写字段 alias/兜底链。
  - 建议：明确调用方在 `ok=false` 时必须“停止进一步消费”的策略（标准要求，见 `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:60` `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:61`）；单测门禁需补（tests 不在本次扫描范围内）。

- 位置：`app/services/accounts_permissions/snapshot_view.py:18`
  - 类型：兼容策略/fail-fast
  - 描述：V4 决策“拒绝 legacy”：仅接受 `snapshot.version==4`，否则直接抛 `ConflictError`，避免 silent fallback。
  - 建议：在变更文档或实现处补齐“为何不兼容 legacy”的退出/迁移说明（对齐 `docs/Obsidian/standards/backend/compatibility-and-deprecation.md:64` `docs/Obsidian/standards/backend/compatibility-and-deprecation.md:65` 的“可删除/可解释”要求）。

### 6.2 回退/降级/容错（重点：可观测性字段）

- 位置：`app/infra/route_safety.py:78`
  - 类型：防御/回退/统一记录器
  - 描述：提供 `log_fallback(...)` 单入口，统一写入 `fallback=true` 与 `fallback_reason`，用于避免字段命名漂移。
  - 建议：将各层“异常→兜底值/continue”的分支尽量统一改为使用该入口（见 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:51`）。

- 位置：`app/tasks/capacity_collection_tasks.py:56`
  - 类型：回退/partial failure（循环中单项失败继续）
  - 描述：单实例同步异常后 `rollback` 并继续处理其他实例，属于标准定义的 fallback/partial failure。
  - 建议：补齐 `fallback=true` 与 `fallback_reason`（当前仅 `sync_logger.exception(...)`，不满足 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:47` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:48`）。

- 位置：`app/infra/database_batch_manager.py:168`
  - 类型：回退/partial failure（批处理单项失败 continue）
  - 描述：单操作失败被捕获并 `continue`，批次允许部分成功；属于 fallback/partial failure。
  - 建议：补齐 `fallback=true` 与可枚举的 `fallback_reason`（例如 `"db_batch_op_failed"` + `operation_type`），并在批次汇总日志中体现 `fallback_count` 以便观测。

- 位置：`app/views/mixins/resource_forms.py:252`
  - 类型：回退（silent fallback）
  - 描述：`url_for` 异常时静默回退到首页，属于 silent fallback。
  - 建议：至少记录一次结构化 warning（可用 `log_fallback`），避免“导航异常被吞掉导致长期隐患”。

### 6.3 `or` 兜底（形状稳定/默认值/危险兜底）

- 位置：`app/services/connections/instance_connections_write_service.py:25`
  - 类型：防御/形状兜底（dict）
  - 描述：`payload or {}`：将缺失 payload 统一为 `{}` 后进入 `parse_payload` + schema 校验，避免 None 分支散落。
  - 建议：若 payload 可能是空 `MultiDict`，`payload or {}` 会丢失类型信息；可改为 `payload if payload is not None else {}`（避免把合法“空但有类型”的值当作缺失）。

- 位置：`app/services/tags/tags_bulk_actions_service.py:96`
  - 类型：防御/形状兜底（dict）
  - 描述：`parse_payload(payload or {}, ...)`：对 bulk action payload 做形状兜底，避免 `None` 分支。
  - 建议：同上，建议用 `is None` 显式判定缺失，避免 truthy 覆盖“合法空容器”的语义。

- 位置：`app/repositories/capacity_databases_repository.py:27`
  - 类型：适配/注入（session fallback）
  - 描述：`session or db.session`：允许外部注入 session，否则回退到全局 session。
  - 建议：若未来引入“可为 falsy 的 session 包装器”，此写法可能误回退；更稳妥为 `session if session is not None else db.session`。

- 位置：`app/repositories/instance_database_sizes_repository.py:149`
  - 类型：危险兜底（布尔覆盖/隐式优先级）
  - 描述：`include_placeholder_inactive = options.include_inactive or not latest`：当 `latest` 为空时，即使 `include_inactive=False` 也会回退为 True（覆盖合法 False），属于“隐式优先级”。
  - 建议：改为显式表达优先级并写注释（例如 `include_placeholder_inactive = (options.include_inactive is True) or (not latest)`），避免误读为“普通默认值兜底”。

- 位置：`app/services/connection_adapters/adapters/postgresql_adapter.py:56`
  - 类型：适配/回退链（多级 schema 解析）
  - 描述：`database_name or get_default_schema(...) or "postgres"`：多级回退，避免未配置 schema 时连接失败。
  - 建议：确认空串是否应视为缺省（若空串为合法值，则该 `or` 会覆盖）；并将回退原因纳入可观测性（连接失败/降级时）。

- 位置：`app/services/connection_adapters/adapters/oracle_adapter.py:57`
  - 类型：适配/默认值（危险兜底：空串覆盖）
  - 描述：`service_name = self.instance.database_name or "ORCL"`：当 `database_name` 为空串时会回退到 `"ORCL"`。
  - 建议：若空串仅代表缺省则合理；否则应改为 `if database_name is None` 的判定，避免覆盖合法空值。

## 7. 修复优先级建议

### P0（必须尽快修复，影响可观测性与标准一致性）

- 回退/降级/partial failure 分支补齐 `fallback=true` 与 `fallback_reason`（`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:47` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:48`）。
  - 重点先覆盖：批处理 continue、best-effort 返回 `[]/{}`、silent fallback。

### P1（重要修复，影响分层一致性与长期可维护性）

- Service 层数据访问收敛到 Repository（`docs/Obsidian/standards/backend/layer/services-layer-standards.md:44`）。
  - 建议按域拆分迁移：先补 Repository 方法（add/delete/flush/select），再逐步搬迁 Service 直写 session 的代码。

### P2（规范完善与治理项，避免后续口径漂移）

- 统一 `or` 兜底的强度口径（MUST NOT vs SHOULD），并补齐例外场景与判据（见 “## 3.1”）。
- 固化 error envelope 的 `category/severity` 枚举与映射单入口（见 “## 3.2”）。
- 为“密钥读取工具封装层”补 allowlist 与删除计划（见 “## 3.3”）。
