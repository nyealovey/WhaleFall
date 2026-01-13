> Status: Draft
> Owner: WhaleFall Team
> Created: 2026-01-12
> Updated: 2026-01-12
> Scope: 复核 `docs/Obsidian/standards/backend/**` 标准一致性, 并对 `app/**` 做全量静态审计
> Related:
> - `docs/Obsidian/standards/backend/README.md`
> - `docs/Obsidian/standards/backend/layer/README.md`
> - `docs/Obsidian/standards/backend/write-operation-boundary.md`
> - `docs/Obsidian/standards/backend/error-message-schema-unification.md`
> - `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md`

# 后端标准全量审计报告 (2026-01-12)

## 1. 目标

1) 检查 `docs/Obsidian/standards/backend/**` 内部是否存在冲突或歧义.
2) 全量扫描 `app/**`, 找出不符合标准的行为与边界漂移.
3) 盘点防御/兼容/回退/适配逻辑, 重点关注 `or` 兜底与数据结构兼容(字段/形状/版本迁移).

## 2. 审计方法与证据

### 2.1 已执行的仓库门禁脚本

- `./scripts/ci/api-layer-guard.sh`: PASS
- `./scripts/ci/tasks-layer-guard.sh`: PASS
- `./scripts/ci/forms-layer-guard.sh`: PASS
- `./scripts/ci/services-repository-enforcement-guard.sh`: PASS
- `./scripts/ci/error-message-drift-guard.sh`: PASS
- `./scripts/ci/db-session-write-boundary-guard.sh`: PASS
- `./scripts/ci/secrets-guard.sh`: PASS
- `./scripts/ci/pyright-guard.sh`: PASS

说明:
- `./scripts/ci/ruff-style-guard.sh`: FAIL. 原因是 `scripts/ci/baselines/ruff_style.txt` 为空, 当前仓库存在 188 条 `ruff check . --select D,I,PLC,G` 命中, 会被门禁当作 "新增"(见 7.3).

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

### 2.3 AST 语义扫描(一次性脚本)

- `app/routes/**`: 所有 `@blueprint.route(...)` 路由函数均包含 `safe_route_call(...)`. 缺失: 0.
- `app/api/v1/namespaces/**`: `Resource` HTTP 方法未统一包含 `safe_route_call(...)` 或 `self.safe_call(...)`. 缺失: 5(见 4.1).

## 3. 标准冲突或歧义

### 3.1 API 层依赖方向不一致(API -> Services vs API -> Repositories)

- 位置: `docs/Obsidian/standards/backend/layer/api-layer-standards.md:46`
  - 问题: 要求 API 层 MUST 调用 `app.services.*`.
- 位置: `docs/Obsidian/standards/backend/layer/api-layer-standards.md:188`
  - 问题: 又允许 API 层 MAY 依赖 `app.repositories.*` 做简单只读查询(需评审说明).
- 位置: `docs/Obsidian/standards/backend/layer/README.md:43`
  - 问题: 依赖图仅体现 `API --> Services & Utils & Infra`, 未体现 API -> Repository 的例外边.
- 风险: 评审口径分裂, 端点逐步产生依赖漂移(部分端点绕过 services 直连 repositories).
- 建议:
  - 二选一明确: (A) 严禁 API -> Repository, 或 (B) 明确允许但写清触发条件并增加门禁脚本约束.
  - 若选择 (B), 建议在 `docs/Obsidian/standards/backend/layer/README.md` 的图或备注中标注 "reviewed exception".

### 3.2 `error_code` vs `message_code` 字段口径可能漂移

- 位置: `docs/Obsidian/standards/backend/error-message-schema-unification.md:36`
  - 问题: 建议机器字段为 `error_code`.
- 位置: `docs/Obsidian/standards/backend/layer/api-layer-standards.md:113`
  - 问题: API 错误封套强约束字段为 `message_code`.
- 风险: 不同子系统各自造字段, 下游最终新增被禁止的 `or` 互兜底链.
- 建议:
  - 明确两者关系: 要么统一只用 `message_code`, 要么明确 `error_code` 仅内部字段并在边界层映射为 `message_code`(且只允许发生一次 canonicalization).

### 3.3 依赖图为概览, 但缺少对 "例外" 的显式说明

- 位置: `docs/Obsidian/standards/backend/layer/services-layer-standards.md:109`
  - 说明: services MAY 依赖 `app.models.*`(类型标注/实例化).
- 位置: `docs/Obsidian/standards/backend/layer/README.md:43`
  - 问题: 图中未体现 services -> models 的例外边, 容易被误读为一律禁止.
- 建议: 在图下补充 "overview + exceptions" 说明, 列出允许的 type-only/instantiation-only 例外.

## 4. 不符合标准的代码行为(需要修复)

### 4.1 API 端点未满足 MUST 的 `safe_route_call` 包裹

标准依据:
- `docs/Obsidian/standards/backend/layer/api-layer-standards.md:174` 要求所有 `Resource` 方法 MUST 通过 `safe_route_call(...)` 包裹.

发现:
- 位置: `app/api/v1/namespaces/auth.py:126`
  - 类型: 防御缺失/边界不一致
  - 描述: `CsrfTokenResource.get` 未通过 `self.safe_call(...)` 包裹.
  - 建议: 改为 `return self.safe_call(_execute, module=..., action=..., public_error=..., context=...)`.
- 位置: `app/api/v1/namespaces/auth.py:147`
  - 类型: 防御缺失/边界不一致
  - 描述: `LoginResource.post` 未通过 `self.safe_call(...)` 包裹.
  - 建议: 同上.
- 位置: `app/api/v1/namespaces/auth.py:173`
  - 类型: 防御缺失/边界不一致
  - 描述: `LogoutResource.post` 未通过 `self.safe_call(...)` 包裹.
  - 建议: 同上.
- 位置: `app/api/v1/namespaces/auth.py:253`
  - 类型: 防御缺失/边界不一致
  - 描述: `MeResource.get` 未通过 `self.safe_call(...)` 包裹.
  - 建议: 同上.
- 位置: `app/api/v1/namespaces/health.py:133`
  - 类型: 防御缺失/边界不一致
  - 描述: `HealthPingResource.get` 未通过 `self.safe_call(...)` 包裹.
  - 建议: 同上.

### 4.2 API 层重复实现 payload 解析, 未收敛到 `parse_payload`

标准依据:
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:34` 要求边界层 MUST 使用 `app/utils/request_payload.py::parse_payload`.

发现(重复实现 `_parse_payload()`):
- `app/api/v1/namespaces/auth.py:113`
- `app/api/v1/namespaces/credentials.py:118`
- `app/api/v1/namespaces/instances_connections.py:136`
- `app/api/v1/namespaces/instances.py:391`
- `app/api/v1/namespaces/tags.py:248`
- `app/api/v1/namespaces/users.py:146`

补充发现(反例形态: truthy `or` + strip):
- `app/api/v1/namespaces/auth.py:150`

风险:
- 请求规范化(strip, list 形状, checkbox 语义, raw password 保留)会在端点之间漂移.
- 容易反复引入不安全的 `or` 兜底(合法空值被覆盖).

建议:
- 将 namespace 内 `_parse_payload()` 统一收敛到 `parse_payload(...)`.
- 写路径建议走: `parse_payload(...)` -> `validate_or_raise(...)` -> service 消费 typed payload.

关于 "parse + sanitized 交给 service" vs "restx_models 负责序列化" 的说明:
- 这里的建议是针对 "请求" 侧(输入解析与规范化), 与 "响应序列化" 是两件事.
- 本仓库当前 API v1 主要通过 `BaseResource.success()` -> `unified_success_response(...)` 产出封套与 JSON 载荷, 并通过 `_ensure_json_serializable(...)` 做基础可序列化处理(见 `app/utils/response_utils.py`).
- `app/api/v1/restx_models/**` 的定位更偏向 OpenAPI/RESTX schema(model/fields)与文档. 当前仓库未使用 `marshal_with` 来做运行期输出裁剪, 可用命令验证:
  - `rg -n "marshal_with\\(" app/api/v1`

### 4.3 内部结果结构违反 `error/message` Producer 契约

标准依据:
- `docs/Obsidian/standards/backend/error-message-schema-unification.md:33` 要求产生方 MUST 写入 `message`.

发现:
- 位置: `app/services/connection_adapters/connection_factory.py:98`
  - 类型: 数据结构契约漂移/兼容风险
  - 描述: 失败结果只包含 `error`, 未包含 `message`.
  - 建议: 失败也写 `message`, 允许额外写 `error` 用于诊断.
- 位置: `app/services/connection_adapters/connection_factory.py:87`
  - 类型: 标准反向暗示
  - 描述: docstring 允许 "error/message 二选一", 会诱导消费方写互兜底链.
  - 建议: 明确禁止 "error/message 二选一" 结构, 以 `message` 为 canonical 字段.

### 4.4 写路径 service 手写校验, 未下沉到 schema 层

标准依据:
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:42` 写路径 schema 应在 `app/schemas/**` 并继承 `PayloadSchema`.
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:43` services 应使用 `validate_or_raise(...)` 并消费 typed payload.

发现:
- 位置: `app/services/accounts/account_classifications_write_service.py:384`
  - 类型: 边界职责漂移
  - 描述: service 内部直接对 dict payload 做必填校验与规范化.
  - 建议: 为该写路径补齐 `app/schemas/**` schema, 迁移字段级校验与 canonicalization 到 schema.
- 位置: `app/services/scheduler/scheduler_job_write_service.py:73`
  - 类型: 边界职责漂移
  - 描述: service 内部手写 `trigger_type` 等校验.
  - 建议: 同上, 为 scheduler 写路径补 schema 并收敛校验策略.

### 4.5 敏感信息处理: 日志打印连接串风险

标准依据:
- `docs/Obsidian/standards/backend/sensitive-data-handling.md:18` 禁止把连接串明文写入日志.

发现:
- 位置: `app/settings.py:232`
  - 类型: 防御不足/敏感数据泄露风险
  - 描述: 直接把 `database_url` 输出到日志(即使是 SQLite, 也属于连接信息).
  - 建议: 仅记录非敏感信息(例如 "fallback_sqlite_enabled=true" 与 sqlite 文件名 basename), 不打印完整 URL.

## 5. 符合标准的关键点(通过项摘要)

- Routes 全量使用 `safe_route_call(...)`(AST 扫描缺失 0), 符合 `docs/Obsidian/standards/backend/layer/routes-layer-standards.md`.
- 写操作事务边界门禁有效:
  - `app/services/**` 未发现 `db.session.commit/rollback`.
  - routes 未直接进行 `db.session` 写操作, 且 commit 位置与 allowlist 匹配.
- 业务模块未散落读取 env, Settings 维持单一真源.
- 未发现 `error/message` 互兜底链(门禁命中 0).

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
  - 建议: 所有 HTTP 入口统一调用该函数, 避免重复实现与口径漂移.

- 位置: `app/schemas/base.py:16`
  - 类型: 兼容(前向兼容)
  - 描述: `extra="ignore"` 忽略未知字段, 允许客户端携带扩展字段而不导致校验失败.
  - 建议: 对需要严格拒绝未知字段的接口, 在具体 schema 中显式开启严格模式并补单测.

### 6.3 配置回退与 legacy 拒绝策略

- 位置: `app/settings.py:226`
  - 类型: 回退
  - 描述: `DATABASE_URL` 缺失时, 非 production 回退 SQLite.
  - 建议: 禁止打印连接串全文, production 维持 fail-fast.

- 位置: `app/settings.py:210`
  - 类型: 兼容(弃用强约束)
  - 描述: legacy env `JWT_REFRESH_TOKEN_EXPIRES_SECONDS` 触发 fail-fast 并提示迁移到新变量.
  - 建议: 记录迁移窗口, 迁移完成后删除 legacy 检查.

- 位置: `app/settings.py:330`
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

- 给 5 个 API 端点补齐 `safe_call` 包裹(见 4.1).
- 修复 `app/services/connection_adapters/connection_factory.py:98` 的结果结构, 失败结果也必须包含 `message`.
- 修复 `app/settings.py:232` 的连接串日志输出, 避免明文输出.

### 7.2 P1 (高收益, 降低长期漂移)

- 将 API 各 namespace 的 `_parse_payload()` 收敛到 `app/utils/request_payload.py:23`.
- 为 `account_classifications_write_service` 与 `scheduler_job_write_service` 引入写路径 schema, 并迁移字段校验/默认值/兼容策略到 schema.

### 7.3 P2 (工程治理)

- 初始化 Ruff style baseline:
  - `./scripts/ci/ruff-style-guard.sh --update-baseline`
  - 之后再以 "允许减少, 禁止新增" 的方式推进增量治理.

