> Status: Draft
> 
> Owner: Codex（后端标准审计员 + 代码合规审计员）
> 
> Created: 2026-01-15
> 
> Updated: 2026-01-15
> 
> Scope:
> - Standards: `docs/Obsidian/standards/backend/**/*.md`（31 个文件）
> - Code: `app/**/*.py`（仅此范围；共 432 个文件）
> 
> Related:
> - `docs/Obsidian/standards/backend/README.md`
> - `docs/Obsidian/standards/backend/layer/api-layer-standards.md`
> - `docs/Obsidian/standards/backend/layer/routes-layer-standards.md`
> - `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md`
> - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md`
> - `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md`
> - `docs/Obsidian/standards/backend/write-operation-boundary.md`
> - `docs/reports/2026-01-15-backend-standards-audit-fixlist.md`（全量修复清单）

# 后端标准全量审计报告 (2026-01-15)

## 1. 目标

- 标准侧：识别 `docs/Obsidian/standards/backend/**/*.md` 内部的冲突、歧义、不可执行点（尤其 MUST/MUST NOT/SHOULD）。
- 代码侧（严格限定 `app/**/*.py`）：
  - 仅基于“明确强约束”（MUST/MUST NOT 等价强制措辞）识别违规；每条违规必须回链到 `标准文件:行号` 与 `app/...:行号`。
  - 对 SHOULD / 模糊标准：只标注为“疑似问题/建议改进”，不强判违规。
- 盘点 `app/**` 内的防御/兼容/回退/适配逻辑，重点关注 `or`/truthy 兜底链与数据结构兼容。

## 2. 审计方法与证据

> 说明：这是一次只读静态审计；不修改代码、不修改标准文件；仅输出报告与可落地建议。
>
> 参考报告 `docs/reports/2026-01-12-backend-standards-audit-report.md` 在本仓库中不存在（2026-01-15 现状）。本报告按本次需求给定的强制章节结构输出，并尽量对齐仓库现有报告的表达风格（例如 `docs/reports/clean-code-analysis.md`）。

### 2.1 已执行的仓库门禁脚本

- 未执行。
- 原因：本次“代码违规判定”范围被严格限定为 `app/**/*.py`；仓库门禁脚本多为全仓或包含 `scripts/**`、`tests/**` 等路径，容易引入超范围证据。

### 2.2 已执行的补充静态扫描

- 标准侧全量扫描：遍历 `docs/Obsidian/standards/backend/**/*.md` 并抽取含 MUST/MUST NOT/SHOULD/MAY 的行级约束（共 523 条行级约束，用于后续映射与引用）。
- 代码侧限定扫描：所有 `rg -n` 均显式限定在 `app/**`（或其子目录）内执行。

本次用于“证据定位/排除项确认”的关键扫描命令（节选）：

```bash
# 标准文件计数
find docs/Obsidian/standards/backend -type f -name '*.md' | wc -l

# 代码扫描范围计数（仅 app/**/*.py）
rg --files app -g'*.py' | wc -l

# Settings 单一真源：排除 app/settings.py / app.py / wsgi.py 之外的 env 读取
rg -n "os\.(environ\.get|getenv)\(" app -g'*.py' | rg -v "app/settings\.py|app\.py|wsgi\.py"

# 事务提交点：定位 db.session.commit/rollback 的实际位置
rg -n "db\.session\.(commit|rollback)\(" app -g'*.py'

# 路由/任务/API/表单视图层：禁止直接 DB access（粗筛）
rg -n "\.query\b|db\.session\b" app/routes app/api app/tasks app/forms app/views -g'*.py'

# 错误消息漂移：禁止 error/message 与 message_code/error_code 互兜底链
rg -n 'get\("error"\)\s*or\s*.*get\("message"\)' app -g'*.py'
rg -n 'get\("message_code"\)\s*or\s*.*get\("error_code"\)' app -g'*.py'

# YAML 读取点定位（与 YAML 校验标准关联）
rg -n "yaml\.safe_load" app -g'*.py'
```

### 2.3 AST 语义扫描

- 目标：从语义层面盘点 `or`/truthy 兜底链与“异常捕获后返回兜底值”的防御/回退点。
- 方法：对 `app/**/*.py` 使用 `python3` 的 `ast.parse` + `ast.walk` 扫描。

AST 扫描结论（仅 `app/**`）：

- `or` BoolOp 总计：759 处（以 `(path, lineno, col)` 去重）。
- 分布（按 `app/<top_dir>` 统计，便于定位“兜底链”集中区）：

| Top Dir | BoolOp(or) 数量 |
|---|---:|
| `app/services` | 405 |
| `app/api` | 107 |
| `app/repositories` | 87 |
| `app/utils` | 50 |
| `app/schemas` | 42 |
| `app/views` | 22 |
| `app/routes` | 19 |
| `app/infra` | 6 |
| `app/core` | 6 |
| `app/tasks` | 5 |
| `app/models` | 5 |
| `app/__init__.py` | 2 |
| `app/settings.py` | 2 |
| `app/scheduler.py` | 1 |

- `try/except` 中存在 `return ...`（潜在回退/降级点）：113 处（用于第 6 节清单与风险评估，不直接等同违规）。

### 2.4 可执行约束索引（摘要版）

> 说明：backend standards 行级可执行约束共 523 条（机器抽取）。为避免在报告中“长篇粘贴标准原文”，此处仅给出可审计/可映射的摘要索引（覆盖本次代码审计最相关的强约束与典型反例）。

| 主题 | 约束摘要 | 位置（标准） | 影响范围 | 典型反例/示例 |
|---|---|---|---|---|
| 响应封套 | success 必须为 `success/error/message/timestamp` 统一口径；失败封套必须包含 `error_id/category/severity/message_code/recoverable/suggestions/context`；`extra` 禁止出现 `error_code` | `docs/Obsidian/standards/backend/layer/api-layer-standards.md:121` / `docs/Obsidian/standards/backend/layer/api-layer-standards.md:133` / `docs/Obsidian/standards/backend/layer/api-layer-standards.md:146` | `app/api/**`、Routes(JSON) | 反例：手写错误 JSON（`docs/Obsidian/standards/backend/layer/api-layer-standards.md:194`） |
| 错误字段漂移 | 产生方必须写 `message`；对外必须用 `message_code` 且 error envelope 任意位置不得出现 `error_code`；消费方禁止 `error/message` 或 `message_code/error_code` 互兜底链 | `docs/Obsidian/standards/backend/error-message-schema-unification.md:34` / `docs/Obsidian/standards/backend/error-message-schema-unification.md:38` / `docs/Obsidian/standards/backend/error-message-schema-unification.md:43` | 全层（producer/consumer） | 反例：`result.get("error") or result.get("message")`（`docs/Obsidian/standards/backend/error-message-schema-unification.md:83`） |
| 统一兜底 | Routes 必须 `safe_route_call(...)` 且入参至少包含 `module/action/public_error`；Resource 必须 `BaseResource.safe_call(...)` 或 `safe_route_call(...)` | `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:48` / `docs/Obsidian/standards/backend/layer/api-layer-standards.md:202` | `app/routes/**`、`app/api/**` | 禁止吞异常继续返回成功（`docs/Obsidian/standards/backend/layer/api-layer-standards.md:206`） |
| 事务边界 | commit/rollback 只能发生在提交点；可复用 service/repository 禁止直接 commit/rollback | `docs/Obsidian/standards/backend/write-operation-boundary.md:21` / `docs/Obsidian/standards/backend/write-operation-boundary.md:22` | `app/infra/**`、`app/tasks/**`、`app/services/**` | 提交点示例：`safe_route_call`（`docs/Obsidian/standards/backend/write-operation-boundary.md:46`） |
| Service 输入治理 | Service 核心逻辑前必须 `validate_or_raise(...)` 产出 typed payload；字段级规则必须收敛到 `app/schemas/**`；Service 禁止手写 `data.get("x") or default` 等字段级规则 | `docs/Obsidian/standards/backend/layer/services-layer-standards.md:43` / `docs/Obsidian/standards/backend/layer/services-layer-standards.md:81` | `app/services/**` | 反例：Service 直接依赖 `flask.request`（`docs/Obsidian/standards/backend/layer/services-layer-standards.md:45`） |
| parse_payload 单入口 | 写路径 body payload 在进入业务编排前必须 `parse_payload`；一次请求链路只允许执行一次；禁止在业务代码重复 strip/NUL 清理 | `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:38` / `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:42` | `app/utils/request_payload.py`、写路径 Service | 反例：在业务代码里 `(data.get("name") or "").strip()`（`docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:82`） |
| YAML 配置校验 | YAML 读取入口必须立即做 schema 校验与 canonicalization；校验失败必须抛异常且禁止 silent fallback 为 `{}`/`[]` | `docs/Obsidian/standards/backend/yaml-config-validation.md:35` / `docs/Obsidian/standards/backend/yaml-config-validation.md:37` | `app/config/*.yaml` 读取入口 | 禁止 `raw.get("x") or default` 修补形状（`docs/Obsidian/standards/backend/yaml-config-validation.md:36`） |
| Tasks app context | 请求上下文外运行的任务必须在 `app.app_context()` 中执行 | `docs/Obsidian/standards/backend/task-and-scheduler.md:34` | `app/tasks/**` | 示例：`with app.app_context(): ...`（`docs/Obsidian/standards/backend/task-and-scheduler.md:37`） |
| 回退可观测性 | 任何降级/failover/workaround 必须记录 `fallback=true` 与 `fallback_reason`；禁止 silent fallback（`except ...: return default` 且无日志） | `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46` / `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50` | 全层 | 建议优先使用 `log_fallback`（`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:51`） |
| 内部数据契约 | 内部结构化 payload（JSON column/snapshot/cache）必须包含显式 `version`；写入端必须写最新版本 canonical 形状；形状兼容必须收敛到 adapter/normalizer 单入口 | `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54` / `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:105` | 内部 JSON payload（非 HTTP/YAML） | 禁止业务层写 `data.get("new") or data.get("old")`（`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:106`） |

## 3. 标准冲突或歧义

> 判定规则：当标准本身存在冲突/歧义时，优先在本节收敛口径；相关代码点将进入“疑似漂移”，不强判违规。

### 3.1 `error` 字段语义存在边界混用风险（boolean vs string）

- 证据：
  - API JSON Envelope 把 `error` 定义为 boolean（`docs/Obsidian/standards/backend/layer/api-layer-standards.md:122` / `docs/Obsidian/standards/backend/layer/api-layer-standards.md:134`）。
  - “错误消息字段统一”把 `error` 作为“诊断信息摘要（可选）”字段写入示例结果对象（`docs/Obsidian/standards/backend/error-message-schema-unification.md:35` / `docs/Obsidian/standards/backend/error-message-schema-unification.md:72`）。
- 影响（导致实现分裂）：
  - 开发者可能把 `error: "诊断信息"` 误塞入对外 API 封套，从而与 `error: true/false` 发生类型冲突。
  - 消费方为兼容冲突字段，可能被迫写 `payload.get("error") or payload.get("message")` 这类互兜底链（标准明令禁止）。
- 建议（收敛口径）：
  - 在 `docs/Obsidian/standards/backend/error-message-schema-unification.md` 明确：
    - 对外 API envelope：`error` 永远是 boolean；诊断信息不得使用 `error` string。
    - 内部结果对象：允许 `error` string（或改名为 `diagnostic_error` 以彻底消歧）。

### 3.2 `error_code` 的“对外暴露边界”描述不足（envelope vs data payload）

- 证据：
  - error envelope 的 `extra` 禁止出现 `error_code`（`docs/Obsidian/standards/backend/layer/api-layer-standards.md:146`）。
  - error envelope 任意位置（含 `extra`）都不得出现 `error_code`（`docs/Obsidian/standards/backend/error-message-schema-unification.md:38`）。
  - 但 internal contract best-effort 错误结构又要求必须包含 `error_code`（`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:74`）。
- 影响（导致实现分裂）：
  - 当 internal contract 错误结果需要“透出给对外 API”（例如放入 `data.items[]` 做单项失败信息）时，标准未明确：是否允许对外携带 `error_code`。
  - 未收敛口径时，下游容易出现 `message_code/error_code` 的互兜底链与语义漂移。
- 建议（收敛口径）：
  - 明确一条可执行规则：对外 API（包括 `data`）若需要“机器可读错误码”，统一使用 `message_code`（或明确命名空间字段，如 `internal_contract_error_code`），并写出映射策略；避免复用 `error_code`。

### 3.3 `parse_payload` 与 schema 的 canonicalization 职责边界存在重叠点

- 证据：
  - `parse_payload` 被描述为“最小基础规范化（NUL 清理、字符串 strip、list 形状稳定）”（`docs/Obsidian/standards/backend/layer/api-layer-standards.md:62`）。
  - schema 同时要求负责字段级规范化（`str.strip()`、`"" -> None` 等）（`docs/Obsidian/standards/backend/layer/schemas-layer-standards.md:42` / `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md:43`）。
- 影响（导致实现分裂）：
  - 若未来出现“某字段必须保留前后空白”的需求，parse_payload 的全局 strip 与 schema 的字段级规则可能打架，迫使开发者通过 `or` 兜底或额外分支做修补。
- 建议（收敛口径）：
  - 在标准中给出“职责分界表”：
    - parse_payload：只做 shape-level + 安全的通用清理（NUL、必要 strip）且必须尊重 `preserve_raw_fields`。
    - schema：做语义级 canonicalization（`"" -> None`、类型转换、默认值、alias/迁移）。

### 3.4 schema 校验失败的异常类型链路描述不够“开箱即用”

- 证据：
  - service 侧必须用 `validate_or_raise` 并抛出项目 `ValidationError`（`docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:47`）。
  - 同时又要求 schema 校验失败用 `ValueError("...")` 表达（`docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:48`）。
- 影响（导致实现分裂）：
  - 未明确“ValueError 出现在哪一层、如何被 validate_or_raise 包装映射”，容易出现：Service/Routes 直接抛 ValueError，进而导致错误封套口径漂移。
- 建议（收敛口径）：
  - 在 `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md` 补充一段最小示例：pydantic validator 抛 ValueError/SchemaMessageKeyError → `validate_or_raise` 捕获并转换为项目 `ValidationError`（含 message_key/message_code 走向）。

### 3.5 “复杂/薄”等表述存在不可执行 MUST NOT（建议补可验证判据）

- 证据：Tasks 标准包含 `MUST NOT: 在任务函数内堆叠复杂业务逻辑`，但没有给出可验证判据（`docs/Obsidian/standards/backend/layer/tasks-layer-standards.md:49`）。
- 影响（导致实现分裂）：
  - 审计无法稳定判定；评审会回到“凭感觉”，导致开发者为通过评审而引入额外 wrapper/兜底链（反而增加复杂度）。
- 建议（收敛口径）：
  - 给出 2~3 条“触发条件”作为可验证判据（例如：单任务函数 >50 行则强制拆分到 runner/service；任务内出现多段事务提交、循环内 I/O 则必须解释原因并补测试）。

### 3.6 内部数据契约标准的 scope 过宽，可能与日志/审计类 JSON 冲突

- 证据：
  - 内部数据契约要求“长期存储的内部结构化 payload 必须包含 version”（`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54`）。
  - 结构化日志标准把 `context` 作为 JSON 字典写入 `UnifiedLog.context`，并未引入 version（`docs/Obsidian/standards/backend/structured-logging-minimum-fields.md:41` / `app/models/unified_log.py:65`）。
- 影响（导致实现分裂）：
  - 若按字面严格执行，`UnifiedLog.context` 也需要 version；这与“日志 context 的自由度”目标冲突，且会引发大量无意义的版本字段。
- 建议（收敛口径）：
  - 在内部数据契约标准中增加“排除项/例外清单”，至少明确日志类 JSON（如 `UnifiedLog.context`）不纳入 internal contract versioning；避免标准互相打架。

## 4. 不符合标准的代码行为(需要修复)

> 说明：本节只列“明确 MUST/MUST NOT 且证据清晰”的违规点；且仅覆盖 `app/**`。

### 4.1 (P0) DB JSON 字段 `sync_details` 未做内部数据契约版本化

- 标准依据：内部结构化 payload 必须包含显式 `version`（`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54`）。
- 违规位置（多处生产者写入/透传 `sync_details`，均未包含 version）：
  - `app/services/sync_session_service.py:259`（`record.complete_sync(... sync_details=...)` 把 dict 原样写入 record）
  - `app/tasks/accounts_sync_tasks.py:100`（写入 `sync_details=summary_dict`）
  - `app/services/capacity/capacity_collection_task_runner.py:155`（写入 `sync_details={"inventory": inventory_result}`）
  - `app/services/accounts_sync/accounts_sync_service.py:299`（写入 `sync_details=dict(details) ... else {}`）
- 现象与风险：
  - `sync_details` 当前是“无版本号的任意 dict”，一旦字段演进/重命名，下游很容易被迫写 `or` 兜底链或形状适配，违反 internal contract 的单入口原则。
- 可落地修复建议：
  1) 明确一个 internal contract：例如 `sync_details.version=1`（并在后续演进中递增）。
  2) 在 `app/schemas/internal_contracts/**` 增加 `sync_details` 的 adapter/normalizer（读入口做版本判定与 canonicalization；写入口只写最新版本）。
  3) 写入端统一由单入口构造 `sync_details`（避免各处随意拼 dict）。
  4) 如历史数据已存在：制定迁移/回填策略（最小：读入口对缺失 version 的旧数据做一次性迁移并记录命中；迁移完成后删除兼容分支，遵循 `docs/Obsidian/standards/backend/compatibility-and-deprecation.md:64`）。

### 4.2 (P1) 存储型 JSON 字段解析失败时存在 silent fallback（无任何日志/告警）

- 标准依据：禁止 silent fallback（`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50`）。
- 违规位置：
  - `app/models/account_classification.py:214`（`json.loads(...)` 失败直接 `return {}`）
  - `app/models/database_type_config.py:84`（`json.loads(...)` 失败直接 `return []`）
- 现象与风险：
  - 这类字段属于“持久化存储的内部数据形状”；解析失败通常意味着数据被污染或代码写入口径漂移。
  - 直接返回空结构会掩盖问题、造成“看似正常但结果异常”的长尾故障，并促使上层引入兼容兜底链。
- 可落地修复建议：
  - 二选一（需按业务影响选择）：
    1) fail-fast：抛出 `ValidationError/SystemError` 并让上层统一错误处理；
    2) 显式降级：允许返回空结构，但必须记录结构化日志并包含 `fallback=true` 与 `fallback_reason`（`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46`），且在调用方 UI/接口层明确提示“数据异常/需要修复”。

### 4.3 (P1) 审计/变更类 DB JSON 字段未版本化：`AccountChangeLog.privilege_diff/other_diff`

- 标准依据：内部结构化 payload 必须包含显式 `version`（`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54`）。
- 违规位置：
  - `app/models/account_change_log.py:50` / `app/models/account_change_log.py:51`（JSON 列本身无版本字段约束）
  - `app/services/accounts_sync/permission_manager.py:746` / `app/services/accounts_sync/permission_manager.py:747`（写入 list/dict，未包含 `version`）
- 现象与风险：
  - 该类“审计/变更差异”属于 internal payload 的适用范围；一旦条目结构演进（字段改名/新增/类型调整），下游消费会被迫写兼容兜底链。
- 可落地修复建议：
  1) 定义 diff contract（例如 `account_change_log_diff.version=1`），并明确 `privilege_diff/other_diff` 的 canonical 形状；
  2) 在写入前由 adapter/normalizer 单入口统一构造（避免业务层散落拼装 list/dict）；
  3) 若确需“半结构/自由扩展”：应先在标准侧显式增加例外条款，否则按现行 MUST 口径属于违规。

### 4.4 (P1) DB JSON 字段 `AccountPermission.type_specific` 未版本化

- 标准依据：内部结构化 payload 必须包含显式 `version`（`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54`）。
- 违规位置：
  - `app/models/account_permission.py:58`（JSON 列本身无版本字段约束）
  - `app/services/accounts_sync/permission_manager.py:486`（写入 dict，未包含 `version`）
- 现象与风险：
  - `type_specific` 属于长期存储的内部结构化 payload；字段扩展/语义变更会导致跨模块消费不稳定。
- 可落地修复建议：
  - 两种路径择一：
    1) version 化并建立 adapter/normalizer（与 permission_snapshot 的 v4 结构保持一致的命名与迁移策略）；
    2) 将 `type_specific` 完全收敛到已版本化的 `permission_snapshot` 内，并按弃用策略逐步下线独立列（需评估迁移成本与查询场景）。

## 5. 符合标准的关键点(通过项摘要)

> 本节为“代表性通过点”，用于确认关键约束已在代码中落地；不试图穷举全部实现点。

- Settings 单一真源（不在业务模块散落读取 env）：
  - 标准：`docs/Obsidian/standards/backend/configuration-and-secrets.md:36` / `docs/Obsidian/standards/backend/configuration-and-secrets.md:38`
  - 代码：`app/__init__.py:81`（`Settings.load()` 作为入口配置来源）
- Routes 统一兜底 `safe_route_call` 且包含必填字段：
  - 标准：`docs/Obsidian/standards/backend/layer/routes-layer-standards.md:48` / `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:49`
  - 代码：`app/routes/users.py:69`（`module/action/public_error` 齐全）
- API Resource 统一兜底 `BaseResource.safe_call` 并通过 `safe_route_call` 复用事务语义：
  - 标准：`docs/Obsidian/standards/backend/layer/api-layer-standards.md:202`
  - 代码：`app/api/v1/resources/base.py:58`
- 事务提交点集中在 `safe_route_call`（未发现 service/repository 直接 commit/rollback）：
  - 标准：`docs/Obsidian/standards/backend/write-operation-boundary.md:21` / `docs/Obsidian/standards/backend/write-operation-boundary.md:53`
  - 代码：`app/infra/route_safety.py:179`（commit 点）
- 写路径 schema + `parse_payload` + `validate_or_raise` 已形成可复用入口：
  - 标准：`docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:38` / `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:47`
  - 代码：`app/services/users/user_write_service.py:50`
- YAML 配置读取入口已在加载后立即做 pydantic 校验（未在运行期用 `raw.get(...) or default` 修补形状）：
  - 标准：`docs/Obsidian/standards/backend/yaml-config-validation.md:35` / `docs/Obsidian/standards/backend/yaml-config-validation.md:36`
  - 代码：`app/scheduler.py:588` / `app/services/accounts_sync/accounts_sync_filters.py:53`
- internal contract 已在 schema 层以“单入口 + 版本化 + 显式错误结构”落地（示例：permission snapshot v4）：
  - 标准：`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54` / `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:105`
  - 代码：`app/schemas/internal_contracts/permission_snapshot_v4.py:42`

## 6. 防御/兼容/回退/适配逻辑清单(重点: or 兜底)

> 说明：本节是“清单 + 风险提示”，不等同于违规判定。
>
> 统计口径：仅 `app/**`。`or` BoolOp 共 759 处（见 2.3），主要集中在 `app/services`/`app/api`/`app/repositories`。

### 6.1 典型“合理回退”（语义明确，不易覆盖合法空值）

- 位置：`app/utils/request_payload.py:26`
  - 类型：防御
  - 描述：`parse_payload` 通过 request marker 防止“一次请求链路重复解析”（抛 `RuntimeError`）。
  - 建议：保持此 guard；若未来需要在 tasks 链路复用，避免把 guard 扩展到无 request context 的场景。

- 位置：`app/utils/request_payload.py:96`
  - 类型：适配
  - 描述：MultiDict 解析时 `multi_dict.getlist(key) or []` 兜底为空列表，统一 list 形状，避免单值/多值漂移。
  - 建议：属于 shape-level 适配，合理；注意与 schema 的字段级 canonicalization 分工（见 3.3）。

- 位置：`app/schemas/account_classifications.py:55`
  - 类型：兼容/规范化
  - 描述：schema 内使用 `cleaned or None` 把空白视为缺省（符合 schema 层允许的 canonicalization）。
  - 建议：为每类 `cleaned or None` 的字段补充“语义说明 + 单测”（避免误把合法空串当缺省）。

- 位置：`app/routes/credentials.py:76`
  - 类型：防御
  - 描述：`raw_value or ""` 后续做 `strip/lower`，用于 query 参数规整。
  - 建议：只用于“空白等价缺省”的 query 字段；若出现“空串有业务语义”的字段，应改用 `is None` 分支。

- 位置：`app/models/account_permission.py:20`
  - 类型：回退
  - 描述：dialect 检测异常时记录 `fallback=True` 与 `fallback_reason`，并回退到默认表达式路径。
  - 建议：该回退点满足可观测性字段；建议补充触发条件说明（何种异常可忽略、是否需要告警）。

### 6.2 需要重点复核的 `or` 兜底（可能覆盖合法空值/引入隐式优先级）

> 这些点不直接强判违规，但很容易在未来演进中变成“危险兜底”。建议按“字段语义是否允许空值/0/空串/空列表”逐一确认。

- 位置：`app/tasks/accounts_sync_tasks.py:88`
  - 类型：防御
  - 描述：`summary_dict.get("inventory", {}) or {}`（以及 `collection` 同类）把空 dict 视为缺省。
  - 建议：若空 dict 与缺失具有不同语义（例如“任务返回了空结果” vs “未返回该节点”），应改为显式 `is None`/`in` 判断。

- 位置：`app/services/accounts_sync/accounts_sync_service.py:299`
  - 类型：防御/回退
  - 描述：`sync_details=dict(details) if isinstance(details, dict) else {}`，失败时兜底 `{}`。
  - 建议：结合 internal contract（见 4.1），兜底应变为“显式错误结构/带 version”，避免下游按空结构继续执行业务。

- 位置：`app/services/capacity/capacity_collection_task_runner.py:155`
  - 类型：数据契约（当前违规的伴生症状）
  - 描述：`sync_details={"inventory": inventory_result}` 未包含 version；长期会迫使消费方写形状兼容兜底。
  - 建议：按 4.1 进行 internal contract 收敛。

- 位置：`app/routes/credentials.py:57`
  - 类型：防御
  - 描述：`args.get("sort", "created_at", type=str) or "created_at"`（`order` 同类）在极端情况下会把空串覆盖成默认值。
  - 建议：如未来允许 sort/order 为空串表达“无排序/默认”，需要改为 `is None` 判断。

### 6.3 异常捕获后的“降级/回退”清单（人工复核重点）

- 位置：`app/routes/users.py:42`
  - 类型：回退/降级
  - 描述：页面路由捕获 `SystemError/Exception` 后降级渲染空列表，并通过 `log_fallback(...)` 写入 `fallback_reason`。
  - 建议：该模式满足可观测性（`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46`）；建议对“降级的用户可见提示”保持一致。

- 位置：`app/scheduler.py:544`
  - 类型：回退/降级
  - 描述：读取 `scheduler_tasks.yaml` 失败时记录异常并 `return`，让应用继续启动。
  - 建议：在关键生产环境可考虑：将该降级升级为“告警级日志 + 触发阈值/健康检查提示”（标准建议见 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:83`）。

- 位置：`app/models/account_classification.py:214`
  - 类型：回退（当前已判定为违规，见 4.2）
  - 描述：内部持久化 JSON 解析失败返回空 dict 且无日志。
  - 建议：fail-fast 或记录 fallback 日志（必须含 `fallback=true`）。

## 7. 修复优先级建议

- P0（阻断标准落地/未来演进风险高）
  - `sync_details` internal contract 版本化缺失：见 4.1。

- P1（可观测性与数据正确性风险）
  - 存储型 JSON 解析失败 silent fallback：见 4.2。
  - 审计/变更类 JSON 字段未版本化（`privilege_diff/other_diff`）：见 4.3。
  - `AccountPermission.type_specific` 未版本化：见 4.4。

- P2（标准口径收敛与长期维护成本）
  - 明确 `error`/`error_code` 对外边界：见 3.1、3.2。
  - 补齐 `parse_payload` vs schema 分工与异常类型链路示例：见 3.3、3.4。
  - 将“复杂/薄”类 MUST NOT 补充可验证判据：见 3.5。
