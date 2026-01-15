> Status: Draft (static audit)
> Owner: Codex (后端标准审计员/代码合规审计员)
> Created: 2026-01-15
> Updated: 2026-01-15
> Scope:
> - Standards: `docs/Obsidian/standards/backend/**/*.md`（全量）
> - Code (strict): `app/**/*.py`（全量静态扫描；不扫描/不判定 `app/**` 之外任何代码）
> Related:
> - `docs/Obsidian/standards/backend/README.md`
> - `docs/Obsidian/standards/backend/layer/api-layer-standards.md`
> - `docs/Obsidian/standards/backend/layer/routes-layer-standards.md`
> - `docs/Obsidian/standards/backend/layer/services-layer-standards.md`
> - `docs/Obsidian/standards/backend/write-operation-boundary.md`
> - `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md`
> - `docs/Obsidian/standards/backend/error-message-schema-unification.md`
> - `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md`
> - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md`
> - `docs/Obsidian/standards/backend/compatibility-and-deprecation.md`

# 后端标准全量审计报告 (2026-01-15)

## 1. 目标

1) 找出后端标准内部的冲突/歧义/不可执行点（以 MUST/MUST NOT/SHOULD 为核心证据）。
2) 基于“明确强约束”（MUST/MUST NOT/等价强制措辞），识别 `app/**/*.py` 内需修复的违规行为，并为每条提供：
   - 标准依据：`标准文件:行号`
   - 代码位置：`app/...:行号`
3) 盘点 `app/**/*.py` 内的防御/兼容/回退/适配逻辑（重点：`or`/truthy 兜底链、数据结构兼容、版本化/迁移/序列化形状稳定）。

## 2. 审计方法与证据

> 说明：用户提供的参考文件 `docs/reports/2026-01-12-backend-standards-audit-report.md` 在当前仓库中不存在；本报告结构按“用户强制章节清单”对齐，并参考已存在的 `docs/reports/2026-01-14-backend-standards-audit-report.md` 的写法/粒度。

### 2.1 已执行的仓库门禁脚本

本次为“只读静态审计”，未执行会扫描 `app/**` 之外路径的门禁脚本；仅执行了可限制到 `app/**` 的补充静态分析：

- Ruff（仅 `app/**`）：`uv run ruff check app`
  - 结果：`All checks passed!`
- Pyright（仅 `app/**`）：`uv run pyright app`
  - 结果：`0 errors, 0 warnings, 0 informations`

> 说明：Ruff/Pyright 的问题不等价于“后端标准违规”。本报告仅在能回链到后端标准强约束时，才在 “## 4” 标注为“违规需要修复”；否则放入“疑似问题/建议改进”。

### 2.2 已执行的补充静态扫描

使用 `rg -n` 对 `app/**/*.py` 做了强约束相关的针对性定位（仅列出与本报告结论直接相关的扫描项）：

- 事务提交/回滚位置（提交点漂移检查）
  - `rg -n "db\\.session\\.(commit|rollback)\\(" app --glob "app/**/*.py"`
  - 结果：命中 32 处，均位于允许的事务边界入口（`app/tasks/**`、`app/infra/route_safety.py`、`app/infra/logging/queue_worker.py`），未发现 `app/services/**`/`app/repositories/**`/`app/routes/**`/`app/api/**` 直接提交/回滚。
- API/Routes/Tasks 直连 DB（禁止 `Model.query/db.session/session.execute`）
  - `rg -n "Model\\.query|db\\.session\\b|session\\.execute\\(" app/api app/routes app/tasks --glob "app/**/*.py"`
  - 结果：未命中。
- 环境变量读取漂移（业务模块禁止 `os.environ.get/os.getenv`）
  - `rg -n "os\\.(environ\\.get|getenv)\\(" app --glob "app/**/*.py"`
  - 结果：未命中。
- 错误字段互兜底链（禁止 `error/message`、`message_code/error_code` 互兜底）
  - `rg -n --pcre2 "\\.get\\(['\\\"]error['\\\"]\\)\\s*or\\s*\\.get\\(['\\\"]message['\\\"]\\)" app --glob "app/**/*.py"`
  - `rg -n --pcre2 "\\.get\\(['\\\"]message_code['\\\"]\\)\\s*or\\s*\\.get\\(['\\\"]error_code['\\\"]\\)" app --glob "app/**/*.py"`
  - 结果：未命中。
- API 写路径 `@ns.expect(Model)` 的 `validate=False`（避免 RESTX 运行期校验口径漂移）
  - `rg -n "@ns\\.expect\\(" app/api/v1/namespaces --glob "app/**/*.py"`
  - 结果：涉及 payload 的 `@ns.expect(...)` 均显式 `validate=False`；query parser 的 `@ns.expect(parser)` 不需要 `validate=False`。
- Routes 统一兜底（所有路由函数必须通过 `safe_route_call(...)` 包裹）
  - `rg -n "@\\w+\\.route\\(" app/routes --glob "app/**/*.py"`
  - `rg -n "safe_route_call\\(" app/routes --glob "app/**/*.py"`
  - 结果：二者命中数一致（均为 26），未发现未包裹的 route handler。

### 2.3 AST 语义扫描

为避免只靠 grep 漏掉“非字符串形态”的兜底逻辑，本次做了 AST 扫描（仅 `app/**/*.py`）：

- `or` 兜底（过滤掉 `if/while/assert/ifexp/comprehension ifs` 等“条件语境”，仅统计“值语境”的 `x or y`）
  - 总计 648 处（粗分：`.get(...)` 起始 154；`or ""` 104；`or 0/数字` 106；`or {}` 38；`or []` 30；`or None` 21；其他 195）
- 宽泛异常捕获（`except Exception/BaseException/bare except`）
  - 总计 65 处，其中 18 处为“非 raise”分支（返回兜底值/继续执行/吞掉异常等）；这些分支按 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:55` 的判据通常属于 fallback，需要重点核对 `fallback=true/fallback_reason` 可观测性（见 “## 4”）。

### 2.4 可执行约束索引（摘要）

> 本索引只收敛“可执行约束”（尤其 MUST/MUST NOT），用于支撑后续“标准→代码”的映射；不复述 SHOULD 的建议项。

| 主题 | 可执行约束摘要 | 标准位置 | 影响范围 | 典型反例 |
|---|---|---|---|---|
| API 职责边界 | API 只做端点/解析/校验/调用 Service；禁止 API 直连 DB | `docs/Obsidian/standards/backend/layer/api-layer-standards.md:46` `docs/Obsidian/standards/backend/layer/api-layer-standards.md:48` | `app/api/**` | API 内 `Model.query` / `db.session` |
| API 写路径校验分层 | `@ns.expect(Model)` 写路径必须 `validate=False`；字段级规则必须在 schema | `docs/Obsidian/standards/backend/layer/api-layer-standards.md:67` `docs/Obsidian/standards/backend/layer/api-layer-standards.md:68` | `app/api/v1/**` + `app/schemas/**` | API 内 `data.get(...) or .../int/strip` |
| API 统一兜底 | 所有 `Resource` 方法必须通过 `BaseResource.safe_call(...)`/`safe_route_call(...)` | `docs/Obsidian/standards/backend/layer/api-layer-standards.md:200` | `app/api/v1/namespaces/**` | 端点内 `try/except Exception` 吞异常后继续返回成功 |
| Routes 统一兜底 | 所有路由函数必须通过 `safe_route_call(...)` 包裹 | `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:48` | `app/routes/**` | route handler 直接执行 service 且无兜底 |
| 写操作事务边界 | `commit/rollback` 只发生在事务边界入口；可复用层禁止 `commit/rollback` | `docs/Obsidian/standards/backend/write-operation-boundary.md:21` `docs/Obsidian/standards/backend/write-operation-boundary.md:22` | `app/infra/**` `app/tasks/**` | `app/services/**` 内 `db.session.commit()` |
| 回退/降级可观测性 | fallback/workaround 必须记录结构化日志且包含 `fallback=true`/`fallback_reason`；禁止 silent fallback | `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50` | `app/**` | `except Exception: return default` 且无日志 |
| 错误字段统一 | 禁止新增 `error/message`、`message_code/error_code` 互兜底链 | `docs/Obsidian/standards/backend/error-message-schema-unification.md:43` `docs/Obsidian/standards/backend/error-message-schema-unification.md:46` | `app/**` | `result.get(\"error\") or result.get(\"message\")` |
| Settings 单一入口 | 业务模块禁止新增 `os.environ.get`；配置必须经 `Settings` | `docs/Obsidian/standards/backend/configuration-and-secrets.md:36` `docs/Obsidian/standards/backend/configuration-and-secrets.md:38` | `app/**` | `timeout = int(os.environ.get(...))` |
| Tasks 禁止直连 DB | task 禁止 `Model.query/db.session.query/execute`，禁止 `db.session.add/delete/flush` | `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md:46` `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md:47` | `app/tasks/**` | task 内 `db.session.execute(...)` |
| Internal Contract 版本化 | internal payload 必须有 `version`；未知版本禁止静默兜底为 `{}`/`[]` | `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54` `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:61` | `app/schemas/internal_contracts/**` + 调用方 | `unknown_version -> return {}` |
| 兼容分支落点与退出 | 禁止业务代码新增 `data.get(new) or data.get(old)` 兼容链；兼容分支必须可删除 | `docs/Obsidian/standards/backend/compatibility-and-deprecation.md:53` `docs/Obsidian/standards/backend/compatibility-and-deprecation.md:64` | `app/**` | Service 内字段 alias 互兜底长期保留 |
| Schemas 依赖约束 | schema 禁止 DB 与 models/services/repositories 依赖 | `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md:44` `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md:45` | `app/schemas/**` | schema `from app.models...` / `db.session` |
| Shared Kernel 依赖约束 | shared kernel 禁止依赖 HTTP/DB/业务层 | `docs/Obsidian/standards/backend/shared-kernel-standards.md:50` `docs/Obsidian/standards/backend/shared-kernel-standards.md:54` `docs/Obsidian/standards/backend/shared-kernel-standards.md:67` | `app/core/**` | `app/core/**` import Flask/db/service |

## 3. 标准冲突或歧义

### 3.1 `or` 兜底“强度口径”不一致（MUST NOT vs SHOULD）

- 证据：
  - Settings/Config 明确为 MUST NOT：`docs/Obsidian/standards/backend/layer/settings-layer-standards.md:60`
  - 配置与密钥明确为 MUST NOT：`docs/Obsidian/standards/backend/configuration-and-secrets.md:69`
  - 但回退/内部契约中写为 SHOULD（且用词仍是“禁止”）：`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:78`、`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:114`
- 影响：
  - 同一主题（“合法空值是否可被 `or` 覆盖”）在不同标准中强度不同，导致评审/门禁难以形成一致判定；下游实现会出现“有的地方严格 `is None`，有的地方继续用 `or`”的漂移。
- 建议：
  - 统一措辞与强度：要么将相关条款统一为 MUST NOT，要么保留 SHOULD 但删除“禁止”字样并明确 scope（例如仅对 Settings 为 MUST NOT，其余为 SHOULD）。

### 3.2 Error Envelope 必填字段缺少可执行枚举/来源（`category`/`severity`）

- 证据：失败封套要求 `category` 与 `severity` 必填，但标准未给出枚举或落点：`docs/Obsidian/standards/backend/layer/api-layer-standards.md:136` `docs/Obsidian/standards/backend/layer/api-layer-standards.md:137`
- 影响：
  - 产生方只能“凭感觉”造字符串，后续会形成不可治理的口径分裂（统计/告警维度失真）。
- 建议：
  - 在标准中明确单一真源（例如固定枚举落点到 `app/core/constants/**`），并要求错误映射/统一错误处理器从该枚举产出 `category/severity`（标准引用“实现真源”而不是重复定义）。

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
  - 虽给了示例，但缺少可执行 checklist（例如“允许的编排深度/允许循环+写入吗/是否允许做事务语义决策”等），评审容易出现多解。
- 建议：
  - 将“复杂”拆为可检查条目（例如：是否出现循环+写、是否出现跨实体聚合、是否出现权限规则、是否出现事务语义决策等），并给出 3-5 个可复制的正例模板。

### 3.5 “`parse_payload` 一次链路只允许执行一次”缺少可验证门禁

- 证据：
  - `parse_payload` MUST 只执行一次：`docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:38`
  - API 标准重复强调：`docs/Obsidian/standards/backend/layer/api-layer-standards.md:70`
- 问题：
  - 当前缺少可执行门禁（例如 request-scope marker 或统一 wrapper），只能依赖人工 review，容易出现“API parse + Service parse”双重解析导致语义漂移。
- 建议：
  - 增加轻量门禁：在 `parse_payload` 内写入 request-scope 标记（例如 `flask.g`/contextvars），二次调用策略明确化（抛错或写结构化 warning）。

### 3.6 `action-endpoint-failure-semantics` 的 “(Response, status_code) 禁止项”scope 容易被误读

- 证据：
  - 标准写法为 “Resource 只允许返回 … / MUST NOT 返回 `(Response, status_code)`”：`docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md:68` `docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md:71`
  - 但同一 scope (`app/api/v1/**`) 内存在 blueprint route 返回 `(Response, 200)`：`app/api/v1/__init__.py:68` `app/api/v1/__init__.py:69`
- 影响：
  - 若读者按“文件路径 scope”理解，会误判 blueprint route 也必须禁用 `(Response, status_code)`；若按“Resource 方法”理解，则又缺少“哪些 endpoint 不受约束”的显式例外，导致评审口径不稳定。
- 建议：
  - 在标准中明确：该约束是否仅针对 Flask-RESTX `Resource` 方法；如果是，请补充“非 Resource 的 blueprint routes（如 openapi.json）”是否允许 `(Response, status_code)` 的例外条款与理由。

## 4. 不符合标准的代码行为(需要修复)

> 仅在“标准为明确强约束 + 证据清晰”时标注为违规。

### 4.1 回退/降级存在但日志缺少 `fallback=true`/`fallback_reason`（可观测性不达标）

- 标准依据：
  - `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46` `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:48`
  - `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:55`（判据：异常后继续执行/降级也算 fallback）
  - Service 回退分支要求：`docs/Obsidian/standards/backend/layer/services-layer-standards.md:170`
- 违规代码位置（均为“异常→继续执行/降级”的回退分支，但日志字段不满足最小口径）：
  - `app/__init__.py:143`（调度器初始化失败后继续启动；仅 `exception(...)`，缺少 `fallback=true/fallback_reason`，见 `app/__init__.py:146`）
  - `app/infra/logging/queue_worker.py:185`（写入 unified logs 失败后吞掉异常并继续；仅 `queue_logger.exception(...)`，缺少 `fallback=true/fallback_reason`，见 `app/infra/logging/queue_worker.py:186`）
  - `app/services/capacity/instance_capacity_sync_actions_service.py:115`（容量同步后触发聚合失败被吞并继续返回成功；仅 `log_warning(...)`，缺少 `fallback=true/fallback_reason`，见 `app/services/capacity/instance_capacity_sync_actions_service.py:116`）
  - `app/infra/database_batch_manager.py:276`（rollback 防御性兜底吞异常；仅 `logger.exception(...)`，缺少 `fallback=true/fallback_reason`，见 `app/infra/database_batch_manager.py:277`）
- 修复建议：
  - 统一改为调用 `app/infra/route_safety.py:78` 的 `log_fallback(...)`（或在现有日志里补齐 `fallback=true` 与 `fallback_reason`，并在 `context/extra` 写入关键维度）。
  - 若其中某些分支不应被视为 fallback（例如“仅日志写入失败，不影响主业务”），请在 `resilience-and-fallback-standards.md` 明确该类场景的例外判据（否则应按 MUST 执行）。

### 4.2 存在 silent fallback（吞异常并返回兜底，不记录任何日志/告警）

- 标准依据：`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50`
- 违规代码位置：
  - `app/models/account_permission.py:91`（`db.session.get_bind()` 异常被吞并并回退 `dialect_name=""`，无任何日志/告警，见 `app/models/account_permission.py:92`）
  - `app/services/database_sync/table_size_adapters/oracle_adapter.py:84`（查询 CURRENT_SCHEMA 失败时静默回退 `result=[]`，无任何日志/告警，见 `app/services/database_sync/table_size_adapters/oracle_adapter.py:85`）
- 修复建议：
  - 以“低噪音”方式补齐可观测性：至少 `log_fallback(..., fallback_reason=exc.__class__.__name__)`，并避免记录敏感信息（见 `docs/Obsidian/standards/backend/sensitive-data-handling.md:36`）。
  - 对“确实只允许 best-effort”的场景，在函数 docstring 写清楚 best-effort 语义与边界（避免调用方误以为该逻辑是强一致保障）。

## 5. 符合标准的关键点(通过项摘要)

### 5.1 分层依赖与 DB 边界

- API 层未发现 `Model.query/db.session/原生 SQL` 直连（对齐 `docs/Obsidian/standards/backend/layer/api-layer-standards.md:48`）。
- Routes 层未发现 `Model.query/db.session/原生 SQL` 直连（对齐 `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:42`）。
- Tasks 层未发现 `Model.query/db.session.query/execute`，且未发现 `db.session.add/delete/flush/merge`（对齐 `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md:46` `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md:47`）。

### 5.2 事务边界（commit/rollback 漂移）

- `app/services/**`/`app/repositories/**`/`app/routes/**`/`app/api/**` 未发现 `db.session.commit/rollback`（对齐 `docs/Obsidian/standards/backend/write-operation-boundary.md:22`）。
- `db.session.commit/rollback` 仅出现在允许的事务边界入口（任务入口、`safe_route_call`、log worker）（对齐 `docs/Obsidian/standards/backend/write-operation-boundary.md:44`）。

### 5.3 错误字段与兼容链治理

- 未发现 `error/message` 或 `message_code/error_code` 互兜底链（对齐 `docs/Obsidian/standards/backend/error-message-schema-unification.md:43`）。
- 未发现 “业务层字段 alias 互兜底链”（`data.get(new) or data.get(old)`）扩散到 service/repository（对齐 `docs/Obsidian/standards/backend/compatibility-and-deprecation.md:53` 与 `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:105`）。

### 5.4 Settings 与环境变量读取

- `app/**` 未发现 `os.environ.get/os.getenv`（对齐 `docs/Obsidian/standards/backend/configuration-and-secrets.md:38` 与 `docs/Obsidian/standards/backend/layer/settings-layer-standards.md:43`）。

## 6. 防御/兼容/回退/适配逻辑清单(重点: or 兜底)

> 说明：
> - 本节仅覆盖 `app/**/*.py`。
> - “or 兜底”分为：合理回退（语义明确且不覆盖合法空值）与危险兜底（覆盖合法空值/引入隐式优先级/掩盖错误）。
> - 输出格式：位置 / 类型 / 描述 / 建议。

### 6.1 数据结构版本化/兼容（Internal Contract）

- 位置：`app/schemas/internal_contracts/permission_snapshot_v4.py:42`
  - 类型：适配/版本化/单入口 canonicalization
  - 描述：internal contract 读入口显式校验 `version`，未知版本返回统一错误结构（`ok=false` + `error_code`），避免下游写字段 alias/兜底链（符合 “单入口 canonicalization” 方向）。
  - 建议：明确调用方在 `ok=false` 时必须“停止进一步消费”的策略（标准要求，见 `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:61`）；避免把该错误结构直接塞进对外 error envelope（外部禁止 `error_code`，见 `docs/Obsidian/standards/backend/error-message-schema-unification.md:39`）。

- 位置：`app/services/accounts_permissions/snapshot_view.py:18`
  - 类型：兼容策略/fail-fast
  - 描述：V4 决策“拒绝 legacy”：仅接受 `snapshot.version==4`，否则直接抛 `ConflictError`，避免 silent fallback。
  - 建议：在变更文档或实现处补齐“为何不兼容 legacy”的退出/迁移说明（对齐 `docs/Obsidian/standards/backend/compatibility-and-deprecation.md:64` `docs/Obsidian/standards/backend/compatibility-and-deprecation.md:65` 的“可删除”要求）。

### 6.2 回退/降级/容错（重点：可观测性字段）

- 位置：`app/infra/route_safety.py:78`
  - 类型：防御/回退/统一记录器
  - 描述：提供 `log_fallback(...)` 单入口，强制写入 `fallback=true` 与 `fallback_reason`，用于避免字段命名漂移与漏打点。
  - 建议：将各层“异常→兜底值/continue”的分支尽量统一改为使用该入口（见 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:51`）。

- 位置：`app/utils/rate_limiter.py:155`
  - 类型：回退/降级（cache → 内存）
  - 描述：缓存限流检查失败时降级到内存模式，日志包含 `fallback=true` 与 `fallback_reason`，属于标准定义的 failover。
  - 建议：为降级触发补充阈值策略（例如连续 N 次失败才降级），并在日志中补齐 `window/limit` 等关键维度，便于排障（见 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46`）。

- 位置：`app/services/cache_service.py:172`
  - 类型：回退/降级（cache get/set best-effort）
  - 描述：缓存读写异常时保留主业务路径并记录 `fallback=true/fallback_reason`，避免 cache 故障导致业务全挂。
  - 建议：对“缓存 miss（正常条件分支） vs cache 异常（fallback）”继续保持区分（符合 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:64` 的判定说明）。

- 位置：`app/services/sync_session_service.py:432`
  - 类型：回退/partial failure（查询失败返回空列表）
  - 描述：查询会话列表异常时返回 `[]` 并记录 `fallback=true/fallback_reason`，属于 best-effort 读取路径的降级。
  - 建议：确保调用方不会把 `[]` 误判为“真实无数据”（可在上层 UI/接口返回中额外提示降级发生）。

- 位置：`app/routes/instances/statistics.py:45`
  - 类型：回退/页面降级
  - 描述：实例统计页面拉取失败时回退到空统计并提示用户，同时使用 `log_fallback(...)` 记录可观测性字段。
  - 建议：在 `context/extra` 中持续维护可检索维度（例如 `endpoint`），避免页面类降级日志难以聚合。

### 6.3 `or` 兜底模式（摘要：数量与风险）

- 位置：`app/**`（AST 汇总）
  - 类型：兼容/防御（truthy 兜底广泛存在）
  - 描述：值语境 `or` 兜底共 648 处，主要集中在 `.get(...)` 兜底（154）与字符串/数字缺省（`or \"\"` 104、`or 0/数字` 106）。这类模式若用于“输入清洗/显示缺省”通常是合理回退；若用于“业务值/写入值”则可能覆盖合法空值，引入语义漂移（标准强调见 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:78`）。
  - 建议：优先在 schema/adapter 单入口把“空白视为缺省”的语义显式化；对可能合法为 `0/\"\"/[]/{}` 的业务字段，统一改用 `is None` 或显式缺失判定（对齐 `docs/Obsidian/standards/backend/layer/settings-layer-standards.md:60`）。

## 7. 修复优先级建议

- P0（必须修复，明确违规）
  - 统一补齐 fallback 可观测性字段：`app/__init__.py:143` `app/infra/logging/queue_worker.py:185` `app/services/capacity/instance_capacity_sync_actions_service.py:115` `app/infra/database_batch_manager.py:276`（对齐 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46`）。
  - 消除 silent fallback：`app/models/account_permission.py:91` `app/services/database_sync/table_size_adapters/oracle_adapter.py:84`（对齐 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50`）。
- P1（建议修复，降低后续漂移成本）
  - 在标准侧澄清 scope/例外：`docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md:68` 的约束是否覆盖 blueprint routes（见 “3.6”）。
  - 为 `category/severity` 增加可执行枚举与单一真源（见 “3.2”）。
  - 为 `parse_payload` “只执行一次”补可验证门禁（见 “3.5”）。
- P2（建议优化，属于 SHOULD/风险控制）
  - 对值语境 `or` 兜底做“边界集中化”治理：优先收敛到 schema/adapter/infra helpers，减少业务层散落（参考 “6.3” 与 `docs/Obsidian/standards/backend/compatibility-and-deprecation.md:53`）。
