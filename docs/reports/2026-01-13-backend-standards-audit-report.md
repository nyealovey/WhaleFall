> Status: Draft
> Owner: WhaleFall Team
> Created: 2026-01-13
> Updated: 2026-01-13
> Scope: 复核 `docs/Obsidian/standards/backend/**` 标准一致性(冲突/歧义), 并对 `app/**` 做全量静态审计
> Related:
> - `docs/Obsidian/standards/backend/README.md`
> - `docs/Obsidian/standards/backend/layer/README.md`
> - `docs/Obsidian/standards/backend/write-operation-boundary.md`
> - `docs/Obsidian/standards/backend/error-message-schema-unification.md`
> - `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md`

# 后端标准全量审计报告 (2026-01-13)

## 1. 目标

1) 检查 `docs/Obsidian/standards/backend/**` 内部是否存在冲突或歧义（尤其是事务边界、payload/schema、错误封套字段）。
2) 全量扫描 `app/**`, 找出不符合标准的行为与边界漂移。
3) 盘点防御/兼容/回退/适配逻辑, 重点关注 `or` 兜底与数据结构兼容(字段/形状/版本迁移)。

## 2. 审计方法与证据

### 2.0 审计范围（标准文件清单）

本次审计覆盖 `docs/Obsidian/standards/backend/**` 下全部 24 份标准文件（含 `layer/` 子目录）：

- Top-level:
  - `docs/Obsidian/standards/backend/README.md`
  - `docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md`
  - `docs/Obsidian/standards/backend/bootstrap-and-entrypoint.md`
  - `docs/Obsidian/standards/backend/configuration-and-secrets.md`
  - `docs/Obsidian/standards/backend/database-migrations.md`
  - `docs/Obsidian/standards/backend/error-message-schema-unification.md`
  - `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md`
  - `docs/Obsidian/standards/backend/sensitive-data-handling.md`
  - `docs/Obsidian/standards/backend/shared-kernel-standards.md`
  - `docs/Obsidian/standards/backend/task-and-scheduler.md`
  - `docs/Obsidian/standards/backend/write-operation-boundary.md`
- Layer:
  - `docs/Obsidian/standards/backend/layer/README.md`
  - `docs/Obsidian/standards/backend/layer/api-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/constants-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/forms-views-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/infra-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/models-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/repository-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/routes-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/services-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/settings-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/types-layer-standards.md`
  - `docs/Obsidian/standards/backend/layer/utils-layer-standards.md`

### 2.1 已执行的仓库门禁脚本

- `./scripts/ci/api-layer-guard.sh`: PASS
- `./scripts/ci/tasks-layer-guard.sh`: PASS
- `./scripts/ci/forms-layer-guard.sh`: PASS
- `./scripts/ci/services-repository-enforcement-guard.sh`: PASS
- `./scripts/ci/error-message-drift-guard.sh`: PASS
- `./scripts/ci/db-session-write-boundary-guard.sh`: PASS
- `./scripts/ci/secrets-guard.sh`: PASS
- `./scripts/ci/pyright-guard.sh`: FAIL（新增 diagnostics；见 `docs/reports/artifacts/2026-01-13-pyright-guard.log`）
- `./scripts/ci/ruff-style-guard.sh`: FAIL（baseline 为空导致“全量都算新增”；见 `docs/reports/artifacts/2026-01-13-ruff-style-guard.log`）

补充说明:
- `scripts/ci/baselines/pyright.txt` 当前为空(0 行), 因此任何 Pyright diagnostics 都会被判定为“新增”。
- `scripts/ci/baselines/ruff_style.txt` 当前为空(0 行), 因此任何 Ruff style 命中都会被判定为“新增”。

### 2.2 已执行的补充静态扫描

- Routes DB 边界(未发现直连 DB/query):
  - `rg -n "Model\\.query\\b|\\bdb\\.session\\b|\\.query\\b" app/routes`
- Settings env 单一入口(未发现业务模块散落 env 读取):
  - `rg -n "os\\.(environ\\.get|getenv)\\(" app | rg -v "app/settings\\.py|app\\.py|wsgi\\.py"`
  - `rg -n "os\\.environ\\[" app | rg -v "app/settings\\.py|app\\.py|wsgi\\.py"`
- Services 禁止依赖 request(未发现 `flask.request`):
  - `rg -n "from flask import request|flask\\.request" app/services`
- Services 禁止 `commit/rollback`(未发现):
  - `rg -n "db\\.session\\.(commit|rollback)\\(" app/services`
- Repositories 禁止 `commit`(未发现):
  - `rg -n "db\\.session\\.commit\\(" app/repositories`
- Action endpoint 返回值陷阱(未发现 `(Response, status)`):
  - `rg -n "return\\s+response\\s*,\\s*status" app/api/v1/namespaces`
  - `rg -n "\\(Response,\\s*status" app/api/v1/namespaces`

### 2.3 AST 语义扫描(一次性脚本)

- `app/routes/**`: 所有带 `@blueprint.route(...)` 的路由函数均包含 `safe_route_call(...)`. 缺失: 0.
- `app/api/v1/namespaces/**`: 所有 `Resource` HTTP 方法均包含 `self.safe_call(...)` 或 `safe_route_call(...)`. 缺失: 0.

## 3. 标准冲突与模糊定义

### 3.1 事务边界定义冲突（“提交点” vs “决策点”混用）

- 位置: `docs/Obsidian/standards/backend/write-operation-boundary.md:19`
  - 表述: “事务提交/回滚只发生在事务边界入口”, 且列出 HTTP 写入口由 `safe_route_call` 执行 `commit/rollback`（`docs/Obsidian/standards/backend/write-operation-boundary.md:36`、`docs/Obsidian/standards/backend/write-operation-boundary.md:54`）。
- 位置: `docs/Obsidian/standards/backend/layer/services-layer-standards.md:90`
  - 表述: “Web 请求写路径：Service 为事务边界入口；Routes/API 不得自行 commit/rollback”。
- 位置: `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:76`
  - 表述: “Routes MUST NOT db.session(事务边界由 Service 控制)”。
- 位置: `docs/Obsidian/standards/backend/layer/repository-layer-standards.md:48`
  - 表述: “写操作事务边界由 Service 控制”。

问题:
- “事务边界入口”在不同文档中被用于描述两件事:
  1) **提交点(commit/rollback 实际发生的位置)**：HTTP 写路径是 `safe_route_call`（Infra）；
  2) **决策点(通过抛异常/返回来决定 commit/rollback 的业务代码位置)**：通常在 Service（或其下游）通过异常控制流影响 `safe_route_call`。

风险:
- 评审口径分裂：有人会把“Service 为事务边界入口”理解为“Service 可以/应该直接 commit/rollback”(但写边界标准又禁止)。
- 长期导致标准被“口头修正”，门禁脚本难以覆盖真实意图。

建议:
- 统一术语并在 `write-operation-boundary.md` 与 `services-layer-standards.md` 中显式区分：
  - **提交点**：HTTP 写入口为 `safe_route_call`；tasks/scripts 为各自入口。
  - **决策点**：Service 通过抛出受控异常/返回业务失败响应影响提交策略。
- 在 `services-layer-standards.md` 将“Service 为事务边界入口”改为“Service 为事务边界**决策点**（通过异常控制提交/回滚）”，避免误导。

### 3.2 API v1 的“RESTX model/parse_payload/pydantic schema”关系仍偏口头约定

位置(分散定义):
- `docs/Obsidian/standards/backend/layer/api-layer-standards.md:45` 说明 API 层负责参数解析/校验与封套。
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:34` 要求写路径在边界使用 `parse_payload`。
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:42` 要求写路径 schema 在 `app/schemas/**` 且由 service `validate_or_raise`。

问题:
- API v1 端点普遍使用 `@ns.expect(Model, validate=False)`，同时又自行 `parse_payload(...)` + 手写校验；但“哪些校验必须放 schema、哪些允许在 API”缺少统一判据。

风险:
- 校验策略在端点之间漂移，长期容易出现 `or` 兜底链与合法空值覆盖。
- 直接带来类型不稳定：本次 Pyright 门禁新增 diagnostics 主要集中在“parse_payload 返回 union，端点手写校验后仍无法静态收敛”的场景（见 4.5）。

建议:
- 在 `api-layer-standards.md` 增加一段“写路径推荐流水线”(可执行、可检查)：
  - API: `raw` → `parse_payload(...)`（只做形状/基础规范化）
  - Service: `validate_or_raise(PayloadSchema, sanitized)`（产出 typed payload）
  - Service: 只消费 schema 对象，禁止对 raw dict 做 `get(...) or default` 链
  - RESTX model: 仅用于 OpenAPI 文档(默认 `validate=False`)，避免与 schema 重复校验导致口径分裂

### 3.3 Entrypoint 允许的 `os.environ.setdefault` 缺少 allowlist（可执行判据不足）

- 位置: `docs/Obsidian/standards/backend/bootstrap-and-entrypoint.md:56`
  - 表述: 入口脚本 MAY 使用 `os.environ.setdefault(...)` 写入“少量运行默认值”。

问题:
- “少量/哪些变量允许”缺少明确列表与审计口径（例如是否允许写入 `FLASK_ENV`、是否允许写入 feature flag）。

建议:
- 在标准中维护 allowlist（变量名 + 理由），或约束为“只允许 setdefault 非敏感、非业务语义、且不影响安全边界的变量”(并给出示例/反例)。

## 4. 不符合标准的代码行为(需要修复)

### 4.1 内部结果结构违反 `error/message` Producer 契约

标准依据:
- `docs/Obsidian/standards/backend/error-message-schema-unification.md:34` 产生方 MUST 写入 `message`。
- `docs/Obsidian/standards/backend/error-message-schema-unification.md:42` 消费方 MUST NOT 新增 `error/message` 互兜底链（因此 producer 更必须稳定输出）。

发现:
- 位置: `app/services/connection_adapters/connection_factory.py:88`
  - 类型: 标准反向暗示/兼容风险
  - 描述: docstring 宣称 “`{'success': bool, 'error': str}` 或 `{'success': bool, 'message': str}`”，会诱导下游写互兜底链。
  - 建议: 文档与返回值统一为 canonical：失败也必须包含 `message`，可选包含 `error` 作为诊断字段。
- 位置: `app/services/connection_adapters/connection_factory.py:98`
  - 类型: 数据结构契约漂移/兼容风险
  - 描述: `test_connection` 失败分支返回 `{success: False, error: ...}`，缺失 `message`。
  - 建议: 返回 `{success: False, message: "...", error: "..."}` 或仅 `{success: False, message: "..."}`；避免下游互兜底。

### 4.2 Settings 输出 SQLite fallback 连接串到日志（敏感信息）

标准依据:
- `docs/Obsidian/standards/backend/configuration-and-secrets.md:61` 禁止把连接串原文写入日志。
- `docs/Obsidian/standards/backend/sensitive-data-handling.md:36` 禁止把连接串原文写入日志。
- `docs/Obsidian/standards/backend/layer/settings-layer-standards.md:66` 禁止把连接串原文写入日志。

发现:
- 位置: `app/settings.py:392`
  - 类型: 防御不足/敏感数据泄露风险
  - 描述: `logger.warning(..., database_url)` 会把 SQLite 连接串完整输出到日志。
  - 建议: 仅记录“fallback_sqlite_enabled=true + sqlite 文件 basename/是否为相对路径”等非敏感信息；不要打印完整 URL。

### 4.3 写路径 Service 未下沉到 schema 层（手写校验 + truthy/`or` 兜底链）

标准依据:
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:42` 写路径 schema MUST 放在 `app/schemas/**` 并继承 `PayloadSchema`。
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:43` service MUST 使用 `validate_or_raise(...)`。
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:50` service MUST 消费 schema 对象，禁止对 raw dict 做 `data.get("x") or default` 兜底。
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:51` update MUST 用 `model_fields_set` 判定字段是否传入，禁止 truthy 分支判断更新。

发现:
- 位置: `app/services/accounts/account_classifications_write_service.py:341`
  - 类型: 边界职责漂移/校验口径漂移
  - 描述: Service 内部直接对 dict payload 做 `.get(...)`、`.strip()`、默认值与合法性校验（应由 schema 层集中治理）。
  - 建议: 为 AccountClassification/Rule 写路径补齐 `app/schemas/**`，将字段级校验、默认值策略、DSL v4 expression 校验入口收敛到 schema，并用 `validate_or_raise` 产出 typed payload。
- 位置: `app/services/accounts/account_classifications_write_service.py:392`
  - 类型: truthy 兜底风险
  - 描述: `missing = [field for field in required_fields if not payload.get(field)]` 会把合法空值当作缺失；属于典型 “truthy 判断导致语义漂移”。
  - 建议: 用 schema 的 required/optional 机制表达“是否必须传入”，并在 update 场景使用 `model_fields_set`。

### 4.4 Scheduler 写路径 Service 未使用 schema（手写触发器校验）

标准依据:
- 同 4.3（`request-payload-and-schema-validation.md:42` / `:43` / `:50`）。

发现:
- 位置: `app/services/scheduler/scheduler_job_write_service.py:64`
  - 类型: 边界职责漂移/校验口径漂移
  - 描述: `upsert` 直接对 `payload` 做 `dict(payload)` + `.get(...)` + `.strip()` 校验与默认值处理，未通过 schema 固化结构与错误口径。
  - 建议: 新增 `app/schemas/scheduler_jobs.py`（示例命名）定义写路径 schema（`trigger_type`, `retention/cron_expression` 等），service 用 `validate_or_raise` 消费 typed payload。

### 4.5 API Action endpoint 仍存在“端点手写校验 + 类型不稳定”路径（触发 Pyright 门禁）

标准依据:
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:42` 写路径 schema MUST 放在 `app/schemas/**`。
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:43` service MUST 使用 `validate_or_raise(...)`。

发现（与 `docs/reports/artifacts/2026-01-13-pyright-guard.log` 对应）:
- 位置: `app/api/v1/namespaces/instances.py:884`
  - 类型: 校验口径漂移/类型不稳定
  - 描述: `batch-delete` 仅 `parse_payload(..., list_fields=["instance_ids"])` 后直接读取 `payload.get("instance_ids")` 传入 service；未通过 schema 收敛为 `list[int]`。
  - 建议: 为 batch-delete 引入 schema（例如 `InstancesBatchDeletePayload`），并在 service 层 `validate_or_raise` 后再调用批量删除逻辑；API 只负责调用 service。
- 位置: `app/api/v1/namespaces/tags.py:506`
  - 类型: 校验口径漂移/类型不稳定
  - 描述: `batch-delete` 在 API 端点手写 `tag_ids` 校验；静态类型无法稳定收敛（Pyright 报告多条 `ScalarValue` 相关错误）。
  - 建议: 把 `tag_ids` 的 list[int] 校验与“必须为正整数”规则下沉到 schema，并用 typed payload 驱动 service。
- 位置: `app/api/v1/namespaces/partition.py:355`
  - 类型: 校验口径漂移/类型不稳定
  - 描述: `cleanup` 在端点直接 `int(raw_retention)`，`raw_retention` 来自 `parse_payload` 的 union；触发 Pyright `reportArgumentType`。
  - 建议: 以 schema 约束 `retention_months` 的类型与范围（并统一错误文案），避免端点内重复写 try/except + 类型转换。

## 5. 符合标准的关键点(通过项摘要)

- Routes 全量使用 `safe_route_call(...)`(AST 扫描缺失 0), 符合 `docs/Obsidian/standards/backend/layer/routes-layer-standards.md`.
- API v1 Resource 全量使用 `self.safe_call(...)`/`safe_route_call(...)`(AST 扫描缺失 0), 符合 `docs/Obsidian/standards/backend/layer/api-layer-standards.md`.
- 写操作事务边界门禁有效:
  - routes 未直写 `db.session` 写操作(门禁 PASS)。
  - `app/services/**` 未发现 `db.session.commit/rollback`(静态扫描 0)。
  - repositories 未发现 `db.session.commit`(静态扫描 0)。
- 业务模块未散落读取 env, Settings 维持单一真源(静态扫描 0)。
- 未发现 `error/message` 与 `message_code/error_code` 互兜底链(门禁命中 0)。

## 6. 防御/兼容/回退/适配逻辑清单(重点: `or` 兜底)

### 6.1 事务边界与异常兜底

- 位置: `app/infra/route_safety.py:110`
  - 类型: 防御/回退
  - 描述: `options.get("fallback_exception", SystemError)` 默认兜底异常类型.
  - 建议: 限制 `fallback_exception` 的允许范围并记录使用场景, 避免错误语义漂移.

- 位置: `app/infra/route_safety.py:132`
  - 类型: 防御/回退
  - 描述: `except Exception` 兜底回滚并抛出 `fallback_exception(public_error)`, 防止未分类异常泄露.
  - 建议: 对可预期失败优先显式加入 `expected_exceptions`, 并确保 `public_error` 稳定且不包含敏感信息.

- 位置: `app/infra/route_safety.py:145`
  - 类型: 防御/fail-safe
  - 描述: commit 失败也会 rollback 并抛兜底异常, 避免 "提交失败但返回成功".
  - 建议: 维持 `commit_failed=true` 作为告警维度.

### 6.2 数据结构规范化与前向兼容

- 位置: `app/utils/request_payload.py:23`
  - 类型: 适配/兼容
  - 描述: 将 JSON mapping 与 MultiDict 统一适配为稳定 dict, 并做基础字符串规范化与 list 形状稳定化.
  - 建议: 写路径坚持 `parse_payload` + schema, 避免端点/服务重复实现导致口径漂移.

- 位置: `app/schemas/base.py:16`
  - 类型: 兼容(前向兼容)
  - 描述: `extra=\"ignore\"` 忽略未知字段, 允许客户端携带扩展字段而不导致校验失败.
  - 建议: 对需要严格拒绝未知字段的接口, 在具体 schema 中显式开启严格模式并补单测.

### 6.3 配置回退与 legacy 拒绝策略

- 位置: `app/settings.py:389`
  - 类型: 回退
  - 描述: `DATABASE_URL` 缺失时, 非 production 回退 SQLite.
  - 建议: 生产环境维持 fail-fast；同时禁止打印连接串全文(见 4.2).

- 位置: `app/settings.py:351`
  - 类型: 兼容(弃用强约束)
  - 描述: legacy env `JWT_REFRESH_TOKEN_EXPIRES_SECONDS` 触发 fail-fast 并提示迁移到新变量.
  - 建议: 记录迁移窗口, 迁移完成后删除 legacy 检查.

- 位置: `app/settings.py:353`
  - 类型: 兼容(弃用强约束)
  - 描述: legacy env `REMEMBER_COOKIE_DURATION_SECONDS` 触发 fail-fast 并提示迁移到新变量.
  - 建议: 同上.

### 6.4 时间戳兜底链

- 位置: `app/repositories/scheduler_jobs_repository.py:68`
  - 类型: 回退
  - 描述: `completed_at or updated_at or started_at or created_at` 时间戳兜底链, 保障 "last run" 可解析.
  - 建议: 在 docstring 写清优先级语义, 避免 "隐含规则" 漂移.

## 7. 修复优先级建议

### 7.1 P0 (优先级最高)

- 修复 `app/settings.py:392` 的连接串日志输出, 避免明文输出(见 4.2).
- 修复 `app/services/connection_adapters/connection_factory.py:98` 的结果结构, 失败结果也必须包含 `message`(见 4.1).

### 7.2 P1 (高收益, 降低长期漂移)

- 为 account classifications / scheduler job 写路径补 schema 并迁移字段校验/默认值/兼容策略到 schema(见 4.3/4.4).
- 处理 API action endpoints 的“手写校验 + union 类型”问题, 以清理 Pyright 门禁并统一口径(见 4.5).

### 7.3 P2 (工程治理)

- 初始化 Ruff style baseline:
  - `./scripts/ci/ruff-style-guard.sh --update-baseline`
  - 之后再以 "允许减少, 禁止新增" 的方式推进增量治理.
- 决策 Pyright baseline 策略:
  - 若要“强约束 0 diagnostics”：保持 baseline 为空, 逐步修复并达成 0；
  - 若要“增量治理”：先 `./scripts/ci/pyright-guard.sh --update-baseline`, 再逐步减少。
