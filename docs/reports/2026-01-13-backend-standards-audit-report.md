> Status: Draft
> Owner: WhaleFall Team
> Created: 2026-01-13
> Updated: 2026-01-13
> Scope: 复核 `docs/Obsidian/standards/backend/**` 标准一致性, 并对 `app/**/*.py` 做全量静态审计
> Related:
> - `docs/Obsidian/standards/backend/README.md`
> - `docs/Obsidian/standards/backend/layer/README.md`
> - `docs/Obsidian/standards/backend/layer/api-layer-standards.md`
> - `docs/Obsidian/standards/backend/error-message-schema-unification.md`
> - `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md`
> - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md`
> - `docs/Obsidian/standards/backend/write-operation-boundary.md`

# 后端标准全量审计报告 (2026-01-13)

## 1. 目标

1) 全量通读 `docs/Obsidian/standards/backend/**`，找出 MUST/MUST NOT/SHOULD 等约束之间的冲突或不可执行点。
2) 全量扫描 `app/**/*.py`，在“强约束 + 证据清晰”前提下标注违规；对 SHOULD/模糊条款仅给出“疑似问题/建议改进”。
3) 盘点 `app/**` 内的防御/兼容/回退/适配逻辑，重点关注 `or`/truthy 兜底链与数据结构兼容（alias/迁移/版本化/序列化形状稳定）。

## 2. 审计方法与证据

### 2.1 已执行的仓库门禁脚本

> 说明：门禁脚本可能覆盖仓库其它目录；本报告的“违规判定”仅对 `app/**/*.py` 生效。

- `./scripts/ci/api-layer-guard.sh`: PASS（未发现 models/routes 依赖或 DB/query）
- `./scripts/ci/tasks-layer-guard.sh`: PASS（未发现 query/execute/add/delete/merge/flush）
- `./scripts/ci/forms-layer-guard.sh`: PASS（未发现跨层依赖/DB/query）
- `./scripts/ci/services-repository-enforcement-guard.sh`: PASS（命中数 0）
- `./scripts/ci/error-message-drift-guard.sh`: PASS（命中数 0）
- `./scripts/ci/db-session-write-boundary-guard.sh`: PASS（routes 未直写 db.session 写操作；commit allowlist 命中 28 且均在允许位置）
- `./scripts/ci/secrets-guard.sh`: PASS（`env.example` 未发现非空敏感值）
- `./scripts/ci/pyright-guard.sh`: FAIL（命中位于 `tests/unit/**`，不在本次 `app/**` 违规判定范围；建议另行修复或更新 baseline）

### 2.2 已执行的补充静态扫描

- Settings env 单一入口（0 命中）：
  - `rg -n "os\\.(environ\\.get|getenv)\\(" app | rg -v "app/settings\\.py|app\\.py|wsgi\\.py"`
  - `rg -n "os\\.environ\\[" app | rg -v "app/settings\\.py|app\\.py|wsgi\\.py"`
- Routes / API 禁止直连 DB/query（0 命中）：
  - `rg -n "Model\\.query\\b|\\bdb\\.session\\b|\\.query\\b" app/routes`
  - `rg -n "Model\\.query\\b|\\bdb\\.session\\b|\\.query\\b" app/api`
- Services 禁止依赖 request（0 命中）：
  - `rg -n "from flask import request|flask\\.request" app/services`
- Services/Repositories 禁止 commit/rollback 漂移（0 命中）：
  - `rg -n "db\\.session\\.(commit|rollback)\\(" app/services`
  - `rg -n "db\\.session\\.commit\\(" app/repositories`
- Schemas/Types 禁止跨层依赖（0 命中）：
  - `rg -n "from app\\.(models|services|repositories|routes|api)\\.|db\\.session\\b" app/schemas`
  - `rg -n "from app\\.(models|services|repositories|routes|api)\\.|db\\.session\\b" app/core/types`
- Action endpoint 返回值陷阱（0 命中）：
  - `rg -n "\\(Response,\\s*status" app/api/v1/namespaces`
  - `rg -n "return\\s+response\\s*,\\s*status" app/api/v1/namespaces`
- Entrypoint `os.environ.setdefault(...)` allowlist（仅命中 `FLASK_APP/FLASK_ENV`）：
  - `app.py:21`, `app.py:22`, `wsgi.py:22`, `wsgi.py:23`

### 2.3 AST 语义扫描

> 目的：验证 “必须使用 `safe_route_call/safe_call`” 这类 grep 难以完全覆盖的语义约束。

- Routes：扫描 `app/routes/**` 所有 `@blueprint.route(...)` 函数，均包含 `safe_route_call(...)` 调用（缺失 0）。
- API v1：扫描 `app/api/v1/namespaces/**` 所有 `class X(BaseResource)` 的 HTTP 方法（`get/post/put/patch/delete`），均包含 `self.safe_call(...)` 或 `safe_route_call(...)` 调用（缺失 0）。

### 2.4 可执行约束索引（摘录）

> 说明：本节只收录“可执行/可验证”的关键约束（优先 MUST/MUST NOT 或等价强制措辞），并给出典型反例形态以便 code review/门禁落地。

#### 2.4.1 分层职责与依赖方向

- API 层职责与依赖（禁止 DB/Repo，必须 safe_call）：
  - 位置：`docs/Obsidian/standards/backend/layer/api-layer-standards.md:46`, `docs/Obsidian/standards/backend/layer/api-layer-standards.md:48`, `docs/Obsidian/standards/backend/layer/api-layer-standards.md:199`, `docs/Obsidian/standards/backend/layer/api-layer-standards.md:214`
  - 典型反例：在 `app/api/**` 中直接 `Model.query` / `db.session`；或 API 直接 import `app.repositories.*`；或 HTTP 方法未走 `safe_call(...)`。
- Routes 层职责与兜底（必须 safe_route_call，禁止 DB/Repo）：
  - 位置：`docs/Obsidian/standards/backend/layer/routes-layer-standards.md:41`, `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:48`, `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:75`
  - 典型反例：Routes 内出现 `Model.query` / `db.session`；Routes 直接 import `app.repositories.*`；Routes 里手写错误 JSON。
- Service 层输入治理（字段级规则必须下沉 schema）：
  - 位置：`docs/Obsidian/standards/backend/layer/services-layer-standards.md:43`, `docs/Obsidian/standards/backend/layer/services-layer-standards.md:81`
  - 典型反例：service 内 `data.get("x") or default` / `strip()` / `int(...)`；service 里解析 `flask.request`。
- Repository 层事务与职责（可 flush，不可 commit）：
  - 位置：`docs/Obsidian/standards/backend/layer/repository-layer-standards.md:47`
  - 典型反例：`app/repositories/**` 内出现 `db.session.commit()` 或把业务判断放进仓储。
- Tasks 层上下文与 DB 边界（必须 app_context，禁止直写/直查）：
  - 位置：`docs/Obsidian/standards/backend/layer/tasks-layer-standards.md:40`, `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md:46`, `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md:47`
  - 典型反例：task 函数直接 `Model.query` 或 `db.session.execute/add/flush`；无 `app.app_context()`。

#### 2.4.2 事务边界（提交点 vs 决策点）

- 事务提交/回滚只发生在提交点；可复用层不得 commit/rollback：
  - 位置：`docs/Obsidian/standards/backend/write-operation-boundary.md:19`
  - 典型反例：`app/services/**` 里 `db.session.commit()` 或 `rollback()`（事务语义漂移）。

#### 2.4.3 错误消息字段与互兜底链禁止

- Producer 必须写入 `message`；禁止在消费侧写 `error/message` 互兜底链：
  - 位置：`docs/Obsidian/standards/backend/error-message-schema-unification.md:34`, `docs/Obsidian/standards/backend/error-message-schema-unification.md:42`
  - 典型反例：`msg = result.get("error") or result.get("message")`。
- 对外 API 错误封套必须用 `message_code`；`error_code` 仅内部字段：
  - 位置：`docs/Obsidian/standards/backend/error-message-schema-unification.md:38`, `docs/Obsidian/standards/backend/layer/api-layer-standards.md:138`

#### 2.4.4 请求 payload 解析与 schema 校验

- 写路径必须 `parse_payload(...)`（一次请求只执行一次）+ `validate_or_raise(...)`：
  - 位置：`docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:38`, `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:47`
  - 典型反例：API/Routes/Service 多处重复 strip/list 折叠；或 service 直接消费 raw dict。

#### 2.4.5 内部数据契约（version + 单入口 canonicalization）

- internal payload 必须包含 `version`；未知版本必须 fail-fast；禁止在业务层写形状兜底链：
  - 位置：`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54`, `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:63`
  - 典型反例：`_ensure_str_list_from_dicts(x) or _ensure_str_list(x)` 这类“形状兼容链”散落在 service/repo。

## 3. 标准冲突或歧义

### 3.1 本次未发现新的 MUST 级别“互相矛盾”条款（并修复了 2026-01-12 关注点）

2026-01-13 的标准更新使以下口径更收敛、可执行：

- API -> Repository 例外口径已收敛为“一律禁止”（避免评审口径分裂）：
  - `docs/Obsidian/standards/backend/layer/api-layer-standards.md:214`
  - `docs/Obsidian/standards/backend/layer/README.md:43`
- 依赖图补齐 “Overview + Exceptions” 说明，避免依赖图被误读为“无例外强约束”：
  - `docs/Obsidian/standards/backend/layer/README.md:56`
- `error_code`（内部）与 `message_code`（对外）边界已明确，减少下游互兜底动机：
  - `docs/Obsidian/standards/backend/error-message-schema-unification.md:38`

### 3.2 `error_code` 是否允许出现在对外 error envelope 的 `extra` 中：口径仍偏模糊

- 位置：`docs/Obsidian/standards/backend/error-message-schema-unification.md:38`
  - 表述为“不得透传 `error_code` **作为对外稳定字段**”，但未定义：
    - `extra` 是否属于“稳定字段”（对前端/调用方而言 `extra.error_code` 仍会被依赖）。
- 位置：`docs/Obsidian/standards/backend/layer/api-layer-standards.md:144`
  - 允许 `extra` 承载“非敏感诊断字段”，但未明确 “允许/禁止” 暴露内部 `error_code`。

风险（实现分裂方式）：
- 一部分端点开始输出 `extra.error_code`，另一部分不输出；下游最终引入 `extra.get("error_code") or ...` 的互兜底分支（标准明确禁止）。

建议：
- 二选一收敛为可执行规则：
  - (A) **对外一律不输出 `error_code`**（即使放 `extra` 也不允许）；如需诊断用 `error_id`。
  - (B) 允许 `extra.error_code` 作为“非稳定诊断字段”，但必须：
    - 统一命名（例如 `diagnostic_error_code`），并在标准中明确“不保证稳定/禁止业务依赖”；
    - 仅在 debug/admin 或特定环境暴露（需与敏感数据标准对齐）。

### 3.3 internal contract 的 “adapter/normalizer 单入口” 落点缺少目录级约束，导致实现者容易误放在 service

- 位置：`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:62`
  - 要求“收敛到 adapter/normalizer（单入口）”，但未明确建议落点（例如 `app/schemas/**`、`app/utils/**`、或 `app/services/<domain>/adapters/**`）。

风险（实现分裂方式）：
- 兼容链以“helper”形式散落在多个 service/repo 文件中；后续无法一次性删除兼容分支，最终形成长期 `or` 互兜底链（与标准目标相悖）。

建议：
- 给出可执行落点约定（并在依赖图/层规范中写明例外）：
  - 推荐：internal payload 的 normalizer 统一放在 `app/schemas/internal_contracts/**`（pydantic 模型 + normalize 函数）
  - 或：按域放在 `app/services/<domain>/adapters/**`，但必须是单入口且禁止被多处复制粘贴

### 3.4 “业务关键路径必须结构化日志”是强约束，但触发条件仍偏主观

- 位置：`docs/Obsidian/standards/backend/layer/services-layer-standards.md:164`
  - MUST 要求记录结构化日志，但“关键路径”的定义未落为可审计判据（容易出现“我以为不是关键”）。

风险（实现分裂方式）：
- 某些写服务/后台任务全量打点，另一些完全无日志；排障依赖人肉猜测，门禁也难覆盖。

建议：
- 将“关键路径”拆成可执行 checklist（至少满足其一即必须打点），例如：
  - 写操作（create/update/delete/restore）
  - 与外部依赖交互（DB connect / remote fetch / scheduler modify）
  - 产生对外 action（`/actions/*`）
  - 有兼容/降级/回退分支（必须包含 `fallback=true` 等字段）

### 3.5 回退/降级标准要求 `fallback=true`，但缺少统一 helper/门禁形态

- 位置：`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46`
  - 规定任何降级必须记录 `fallback=true` 与 `fallback_reason`。

风险（实现分裂方式）：
- 业务代码以“写一条 warning 文本”替代结构化字段；不同模块使用不同 key（`fallback_sqlite_enabled` / `fallback` / `degraded`），导致无法统一检索与告警。

建议：
- 增加统一 helper（例如 `log_fallback(...)`）并在标准中规定其字段集；或在 `log_with_context(...)` 的 options 中提供 `fallback_reason=...` 并自动补齐 `fallback=true`。

### 3.6 写操作边界标准的“强约束”用词明确，但 MUST/MUST NOT 关键词不统一，影响自动化抽取

- 位置：`docs/Obsidian/standards/backend/write-operation-boundary.md:19`, `docs/Obsidian/standards/backend/write-operation-boundary.md:50`
  - 文本表达为“只发生/不得/不允许”，语义强，但不含 MUST/MUST NOT 关键字，工具化抽取成本更高。

建议：
- 将关键条款补齐为 MUST/MUST NOT（保持与其它 layer 标准一致），并标注对应门禁脚本（已有脚本可复用）。

## 4. 不符合标准的代码行为(需要修复)

> 判定说明：仅当标准为 MUST/MUST NOT/等价强制措辞且证据清晰时，才标注为“违规”。

### 4.1 internal payload 形状兼容链散落在 Service 内（违反 internal contract 单入口要求）

标准依据：
- `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:62` internal payload 的形状兼容必须收敛到 adapter/normalizer 单入口
- `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:63` MUST NOT 在 Service/Repository/业务逻辑中写结构兼容链（示例包含 `_ensure_str_list_from_dicts(x) or _ensure_str_list(x)`）

发现（典型形态：`_ensure_*(...) or _ensure_*(...)`）：
- `app/services/accounts_permissions/facts_builder.py:148`
- `app/services/accounts_permissions/facts_builder.py:153`
- `app/services/accounts_permissions/facts_builder.py:161`
- `app/services/accounts_permissions/facts_builder.py:163`
- `app/services/accounts_permissions/facts_builder.py:170`

风险：
- 形状兼容规则以 “or 兜底链” 形式存在于 service 内，未来新增消费方容易复制粘贴，违背“单入口 canonicalization”。
- 当 `[]/{}` 等空值在某些字段语义上变为合法值时，truthy `or` 会引入隐式优先级与语义漂移。

建议：
- 将 `permission_snapshot(v4)` 的 categories/type_specific 形状规范化收敛为一个 adapter/normalizer（例如 pydantic model + `normalize_*` 函数），让 facts_builder 只消费 canonical 形状（不再需要 `or` 兼容链）。
- 为兼容分支补单测并写明退出条件（对齐 `compatibility-and-deprecation`）。

### 4.2 连接适配器 `test_connection` 失败结果缺失 `message`（违反 error/message Producer 契约）

标准依据：
- `docs/Obsidian/standards/backend/error-message-schema-unification.md:34` 产生方必须写入 `message`

发现（失败结果仅包含 `error`，缺失 `message`）：
- `app/services/connection_adapters/adapters/mysql_adapter.py:106`
- `app/services/connection_adapters/adapters/mysql_adapter.py:118`
- `app/services/connection_adapters/adapters/postgresql_adapter.py:102`
- `app/services/connection_adapters/adapters/postgresql_adapter.py:115`
- `app/services/connection_adapters/adapters/sqlserver_adapter.py:161`
- `app/services/connection_adapters/adapters/sqlserver_adapter.py:174`
- `app/services/connection_adapters/adapters/oracle_adapter.py:152`
- `app/services/connection_adapters/adapters/oracle_adapter.py:164`

风险：
- 上游不写 `message` 会迫使下游写 `error/message` 互兜底链（标准明确禁止），并导致错误统计/治理口径漂移。

建议：
- 统一失败结果最小结构：`{"success": False, "message": "...", "error": "...(optional)"}`；并明确 `message` 的“可展示摘要”语义。
- 若该 `test_connection` 已不再被业务链路使用，建议标注弃用并删除（避免未来误用形成新的漂移源）。

## 5. 符合标准的关键点(通过项摘要)

- 分层依赖与 DB 边界门禁通过：
  - API/Routes/Tasks/Forms 未发现直连 DB/query 或跨层反向依赖（见 2.1）。
  - Services/Repositories 未发现 `commit/rollback` 漂移（见 2.1 与 2.2）。
- 错误消息字段漂移门禁通过：`error/message` 互兜底链命中 0（见 2.1）。
- 写操作事务边界门禁通过：routes 未直写 db.session 写操作；commit allowlist 命中均位于允许位置（见 2.1）。
- safe_call/safe_route_call 覆盖良好：Routes 与 API v1 AST 扫描缺失 0（见 2.3）。
- Entrypoint 默认值策略可审计：`os.environ.setdefault(...)` 仅命中 allowlist 的 `FLASK_APP/FLASK_ENV`（见 2.2）。

## 6. 防御/兼容/回退/适配逻辑清单(重点: `or` 兜底)

> 说明：本节只盘点 `app/**/*.py`。对每条 `or` 兜底标注“合理回退/危险兜底候选”，并给出可落地建议。

### 6.1 事务边界与异常兜底（Infra）

- 位置：`app/infra/route_safety.py:110`
  - 类型：防御/回退
  - 描述：`fallback_exception = options.get("fallback_exception", SystemError)` 对未显式配置的异常类型做兜底；异常转换为统一对外 `public_error`。
  - 建议：将 `fallback_exception` 的使用场景纳入“回退/降级可观测性”口径（例如在调用点补 `fallback_reason`），避免被当作“静默吞异常”的借口。

- 位置：`app/infra/route_safety.py:132`
  - 类型：防御/fail-safe
  - 描述：`except Exception` 兜底：统一 rollback + 记录 `unexpected=true` + 抛出 `fallback_exception(public_error)`，避免未分类异常泄露到客户端。
  - 建议：对可预期失败尽量收敛进 `expected_exceptions`（减少“所有异常都进兜底”的语义损失），并确保 `public_error` 不包含敏感信息。

- 位置：`app/infra/route_safety.py:147`
  - 类型：防御/fail-safe
  - 描述：commit 失败同样 rollback 并抛兜底异常，避免“提交失败但返回成功”。
  - 建议：维持 `commit_failed=true` 作为告警维度；必要时对 commit 失败做专门的 error_id/告警策略。

### 6.2 配置回退与 canonicalization（Settings）

- 位置：`app/settings.py:218`
  - 类型：兼容/规范化（`or` 合理使用）
  - 描述：`value.strip() or None` 将空白字符串 canonicalize 为 `None`（语义明确：空白视为缺省）。
  - 建议：保持该策略集中在 Settings/schema 层，避免业务层重复实现导致漂移。

- 位置：`app/settings.py:339`
  - 类型：回退（开发环境）
  - 描述：`SECRET_KEY` / `JWT_SECRET_KEY` 缺失时，非 production 生成随机值并 warning（production fail-fast）。
  - 建议：对齐 “回退/降级可观测性”字段（至少在结构化日志里可检索到该回退发生）。

- 位置：`app/settings.py:366`
  - 类型：回退（开发环境）
  - 描述：`DATABASE_URL` 缺失且非 production 回退 SQLite，并仅记录 `sqlite_db_file` 等非敏感信息。
  - 建议：考虑统一 `fallback=true`/`fallback_reason` 字段口径（见标准歧义 3.5）。

### 6.3 请求 payload 适配与前向兼容（Utils/Schemas）

- 位置：`app/utils/request_payload.py:50`
  - 类型：适配/兼容
  - 描述：把 MultiDict/Mapping 适配为稳定 dict；`getlist(key) or []` 固定 list 形状；支持 checkbox 缺失补 False；并提供 `preserve_raw_fields` 以避免敏感字段被 strip/NUL 清理破坏语义。
  - 建议：保持“一次请求链路只执行一次”的约束；避免 API+Service 双重 parse 导致语义漂移。

- 位置：`app/schemas/base.py:16`
  - 类型：兼容（前向兼容）
  - 描述：`extra=\"ignore\"` 默认忽略未知字段，允许客户端携带扩展字段而不导致写路径失败。
  - 建议：对需要严格拒绝未知字段的 schema，按标准在具体 schema 内显式开启严格模式并补单测。

### 6.4 internal contract：版本化与 fail-fast（Permission snapshot / DSL）

- 位置：`app/services/accounts_permissions/snapshot_view.py:21`
  - 类型：兼容（版本化）/防御（fail-fast）
  - 描述：只接受 `permission_snapshot.version == 4`；snapshot 缺失/非 v4 直接抛错，避免静默兜底。
  - 建议：将“可观测性/退出机制”与 internal-data-contract 标准对齐（例如对未知版本的错误类型与诊断字段统一化）。

- 位置：`app/utils/account_classification_dsl_v4.py:44`
  - 类型：适配（optional dependency）
  - 描述：`prometheus_client` 缺失时回退 `_NoopMetric`（polyfill/shim），保证核心逻辑不依赖可选依赖。
  - 建议：在标准中明确这类 optional dependency 的“可观测性/性能影响”检查点（例如是否需要在日志/metrics 中标注禁用状态）。

- 位置：`app/utils/account_classification_dsl_v4.py:100`
  - 类型：防御（fail-closed）
  - 描述：DSL `version` 不匹配时直接返回校验错误；未知 function/非法 args 走 fail-closed（返回 False），避免放宽策略导致越权。
  - 建议：为关键规则表达式补覆盖测试（至少覆盖未知 function 与 version 不匹配场景）。

### 6.5 业务层 `or` 兜底：合理回退与危险兜底候选

- 位置：`app/services/accounts_sync/adapters/sqlserver_adapter.py:446`
  - 类型：适配/防御
  - 描述：`(precomputed_* or {})` 兜底 None，保证后续 `.get(...)` 可用；`roles or []` 保证 list 形状稳定。
  - 建议：对外部输入（预计算缓存）建议在入口做一次类型断言/normalize，避免在循环内多处散落兜底。

- 位置：`app/services/connection_adapters/adapters/postgresql_adapter.py:56`
  - 类型：回退（默认值链）
  - 描述：`database_name or get_default_schema(...) or \"postgres\"` 为 DB 名称提供默认回退链（空白视为缺省）。
  - 建议：明确 `database_name` 为空/缺失时的语义（是“连接默认库”还是“拒绝连接”），并保证失败结果遵循 `message` 契约（见 4.2）。

- 位置：`app/repositories/capacity_databases_repository.py:40`
  - 类型：防御（危险兜底候选）
  - 描述：`int(getattr(row, \"id\", 0) or 0) or None` 通过 truthy `or` 把 `0` 视为缺省并返回 `None`（语义隐含，且链条可读性差）。
  - 建议：改为显式 `is None` 判定或显式变量（例如 `row_id = getattr(row, \"id\", None)`），避免将来出现“0 为合法值”时被误覆盖。

- 位置：`app/utils/logging/handlers.py:180`
  - 类型：防御/回退
  - 描述：`module = event_dict.get(\"module\") or ... or \"app\"` 为缺失 module 的日志事件提供回退值，保证落库 schema 可用。
  - 建议：对 `module` 的取值范围做约束（例如非空字符串），减少把“空字符串”误当作缺省的风险。

## 7. 修复优先级建议

### 7.1 P0 (优先级最高：明确违规且会导致口径漂移)

- 修复 internal payload 形状兼容链散落在 service（见 4.1），将 compatibility/canonicalization 收敛到 adapter/normalizer 单入口。
- 修复连接适配器 `test_connection` 失败结果缺失 `message`（见 4.2），避免诱发 `error/message` 互兜底链。

### 7.2 P1 (高收益：减少长期漂移/提升可审计性)

- 收敛 `error_code` 对外暴露边界：明确是否允许出现在 error envelope 的 `extra`，并给出统一字段/禁用策略（见 3.2）。
- 为回退/降级补齐统一结构化字段（`fallback=true`、`fallback_reason`）并提供 helper，避免各处自定义 key（见 3.5）。
- 将 “业务关键路径” 日志要求细化为 checklist（见 3.4），便于评审与门禁。

### 7.3 P2 (工程治理/可读性优化)

- 补齐 `write-operation-boundary.md` 的 MUST/MUST NOT 关键词，使“强约束”可被工具稳定抽取（见 3.6）。
- 逐步减少“语义不明确的 `or` 链”并以显式 `is None` 判定替代（优先从 repository/infra 的可疑兜底开始，见 6.5）。

