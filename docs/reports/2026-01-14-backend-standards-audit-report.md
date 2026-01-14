> Status: Draft
> Owner: WhaleFall Team
> Created: 2026-01-14
> Updated: 2026-01-14
> Scope: 复核 `docs/Obsidian/standards/backend/**` 标准一致性, 并对 `app/**/*.py` 做全量静态审计（违规判定严格限定 `app/**`）
> Related:
> - `docs/Obsidian/standards/backend/README.md`
> - `docs/Obsidian/standards/backend/layer/README.md`
> - `docs/Obsidian/standards/backend/layer/routes-layer-standards.md`
> - `docs/Obsidian/standards/backend/layer/api-layer-standards.md`
> - `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md`
> - `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md`
> - `docs/Obsidian/standards/backend/write-operation-boundary.md`
> - `docs/Obsidian/standards/backend/error-message-schema-unification.md`

# 后端标准全量审计报告 (2026-01-14)

## 1. 目标

1) 全量通读 `docs/Obsidian/standards/backend/**`，识别标准内部冲突与不可执行/易误读点（尤其 MUST/MUST NOT/SHOULD/MAY）。
2) 全量扫描 `app/**/*.py`，仅在“强约束 + 证据清晰”前提下标注为 **违规**；对 SHOULD/模糊条款只给出 **疑似问题/建议改进**。
3) 盘点 `app/**` 内的防御/兼容/回退/适配逻辑，重点关注 `or`/truthy 兜底链与数据结构兼容（alias/迁移/版本化/序列化形状稳定）。

## 2. 审计方法与证据

### 2.1 已执行的仓库门禁脚本

本次未执行门禁脚本（原因：门禁脚本的扫描范围可能覆盖 `app/**` 之外目录；本报告要求“违规判定严格限定 `app/**`”，为避免越界输出与误判，本次只保留 `rg -n` + AST 的“范围可控”证据链）。

如需补跑门禁，可另开一轮并在报告中明确“门禁输出仅作提示，违规判定仍以 `app/**` 为准”。

### 2.2 已执行的补充静态扫描（`rg -n`）

标准侧（约束抽取与对照）：

- 约束关键词分布（用于人工对照，不直接作为结论）：`rg -n "\\bMUST NOT\\b|\\bMUST\\b|\\bSHOULD\\b|\\bMAY\\b" docs/Obsidian/standards/backend --glob='*.md'`

代码侧（仅 `app/**`）：

- API 写路径双重 `parse_payload` 触发点（用于定位“API+Service 双重解析”）：`rg -n "\\bpayload\\s*=\\s*_parse_payload\\(" app/api/v1/namespaces --glob='*.py'`
- Services/Repositories `commit/rollback` 漂移（0 命中）：`rg -n "db\\.session\\.(commit|rollback)\\(" app/services app/repositories --glob='*.py'`
- Routes/API 直连 DB/query（0 命中）：`rg -n "Model\\.query\\b|\\bdb\\.session\\b" app/routes app/api --glob='*.py'`
- Services 依赖 request/Response（0 命中）：`rg -n "from flask import request|flask\\.request\\b|from flask import Response|flask\\.Response\\b" app/services --glob='*.py'`
- 错误字段互兜底链（0 命中）：`rg -n "get\\(\\\"error\\\"\\)\\s*or\\s*get\\(\\\"message\\\"\\)|get\\(\\\"message\\\"\\)\\s*or\\s*get\\(\\\"error\\\"\\)" app --glob='*.py'`

### 2.3 AST 语义扫描

目的：覆盖 grep 难以精准表达的语义约束（例如“必须通过 safe_call/safe_route_call 包裹”）。

结论摘要：

- API v1：扫描 `app/api/**` 内 `Resource/BaseResource` 的 HTTP 方法（`get/post/put/patch/delete`），均包含 `self.safe_call(...)` 或 `safe_route_call(...)` 调用（缺失 0）。
- Routes：扫描 `app/routes/**` 所有 `@blueprint.route(...)` 路由函数，均包含 `safe_route_call(...)` 调用（缺失 0）；但发现 3 个路由存在“捕获 `SystemError` 后返回 fallback 页面”的分支，该分支绕过 `safe_route_call` 且未记录 `fallback=true`（见 4.2）。

### 2.4 可执行约束索引（摘录）

> 说明：本节只收录“可执行/可验证”的关键约束（优先 MUST/MUST NOT 或等价强制措辞），并给出典型反例形态，便于 code review 与门禁落地。

#### 2.4.1 分层职责与依赖方向

- API 层职责（必须 service、禁止 DB、必须 safe_call）：
  - 位置：`docs/Obsidian/standards/backend/layer/api-layer-standards.md:46`, `docs/Obsidian/standards/backend/layer/api-layer-standards.md:48`, `docs/Obsidian/standards/backend/layer/api-layer-standards.md:200`
  - 反例形态：在 `app/api/**` 中出现 `Model.query` / `db.session`；或 HTTP 方法未走 `safe_call(...)`；或直接 import `app.repositories.*`（`docs/Obsidian/standards/backend/layer/api-layer-standards.md:215`）。
- Routes 层兜底与 DB 边界（必须 safe_route_call、禁止 DB/Repo）：
  - 位置：`docs/Obsidian/standards/backend/layer/routes-layer-standards.md:42`, `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:48`, `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:75`
  - 反例形态：路由函数出现 `Model.query/db.session`；或未将主要执行逻辑包裹在 `safe_route_call(...)`。
- Service/Repository 的事务边界与输入契约（禁止 commit/rollback 漂移）：
  - 位置：`docs/Obsidian/standards/backend/write-operation-boundary.md:21`, `docs/Obsidian/standards/backend/write-operation-boundary.md:22`
  - 反例形态：`app/services/**` 或 `app/repositories/**` 内出现 `db.session.commit/rollback`。

#### 2.4.2 输入解析与 schema 校验（写路径）

- `parse_payload` 必须且只执行一次（避免 API+Service 双重解析）：
  - 位置：`docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:38`, `docs/Obsidian/standards/backend/layer/api-layer-standards.md:70`
  - 反例形态：API 端点先 `parse_payload(...)`，随后 service 再次 `parse_payload(...)`。

#### 2.4.3 错误字段统一（禁止互兜底链）

- 产生方必须写 `message`，消费方禁止 `error/message` 互兜底：
  - 位置：`docs/Obsidian/standards/backend/error-message-schema-unification.md:34`, `docs/Obsidian/standards/backend/error-message-schema-unification.md:43`
  - 反例形态：`result.get(\"error\") or result.get(\"message\")`。

#### 2.4.4 回退/降级可观测性（重点）

- 任何降级/failover/workaround 必须记录 `fallback=true` 与 `fallback_reason`：
  - 位置：`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46`
  - 反例形态：捕获异常后返回默认值/空结果，但没有任何结构化字段标记降级发生。

## 3. 标准冲突或歧义

### 3.1 MUST/MUST NOT 级别的直接冲突：未发现

本次对 `docs/Obsidian/standards/backend/**` 全量对照后，未发现同一主题出现“可被同时满足但语义相互矛盾”的 MUST/MUST NOT 级别条款。

### 3.2 `message_code` 的“domain 语义”缺少可执行的注册口径（易导致各模块自造 code）

- 位置：`docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md:92`
  - 问题：要求 `message_code` 表达 domain 语义，但未给出“集中枚举/注册”的落点（例如 `app/core/constants/message_codes.py`）与评审规则（新增 code 的命名/分组/生命周期）。

风险（实现分裂方式）：
- 多个模块各自定义 `message_key` 字符串；最终下游被迫维护“同义 code”映射或互兜底逻辑，削弱错误治理能力。

建议：
- 为 `message_code` 增加单一真源（常量表 + 文档），并明确：
  - 新增 code 的命名规范、分组（system/auth/permission/…）、弃用窗口；
  - 是否允许在 `extra` 中携带“诊断用非稳定字段”（与敏感数据标准对齐）。

### 3.3 internal contract 的 scope 定义较宽，但 adapter/normalizer 推荐落点未固化为单一路径

- 位置：`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:37`, `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:62`
  - 问题：标准清晰表达“必须单入口 canonicalization”，但未把 adapter/normalizer 的推荐目录固化为“单一路径约定”（容易出现 adapter 放在 utils/service/<domain>/helpers 多处的实现分裂）。

风险（实现分裂方式）：
- 同一 internal payload 的兼容逻辑被复制到多个 service/repo；后续无法一次性删除兼容分支。

建议：
- 将 internal contract 的 adapter/normalizer 推荐落点明确为：
  - 首选：`app/schemas/internal_contracts/**`（pydantic model + normalize 函数），并在依赖图/层标准中补充“这是允许的例外路径”。

### 3.4 “退出条件/迁移完成”是强约束，但缺少最小记录模板（可执行性仍不足）

- 位置：`docs/Obsidian/standards/backend/compatibility-and-deprecation.md:64`, `docs/Obsidian/standards/backend/compatibility-and-deprecation.md:65`
  - 问题：要求“兼容分支必须可删除、迁移完成后必须删除”，但缺少“最小记录模板”（实现处需要写哪些字段才能让评审与后续清理可执行）。

风险（实现分裂方式）：
- 兼容分支长期保留，直到无人敢删；系统逐步沉淀为“永久兼容层”。

建议：
- 给出最小模板（可写在标准或 PR 模板中），例如：
  - `legacy_shape` / `new_shape` / `exit_criteria` / `deadline` / `telemetry`（日志/指标/单测）/ `owner`。

## 4. 不符合标准的代码行为(需要修复)

> 判定说明：仅当标准为 MUST/MUST NOT/等价强制措辞且证据清晰时，才标注为“违规”。

### 4.1 API 写路径出现 `parse_payload` 双重解析（API + Service），违反“一次请求链路只执行一次”

标准依据：
- `docs/Obsidian/standards/backend/layer/api-layer-standards.md:70`
- `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:38`

发现（典型形态：API 端点 `payload = _parse_payload()`，而对应 service 内仍执行 `parse_payload(...)`）：

- Auth 修改密码：
  - `app/api/v1/namespaces/auth.py:229`
  - `app/services/auth/change_password_service.py:34`
- Credentials 创建/更新：
  - `app/api/v1/namespaces/credentials.py:232`
  - `app/api/v1/namespaces/credentials.py:294`
  - `app/services/credentials/credential_write_service.py:48`
  - `app/services/credentials/credential_write_service.py:78`
- Tags 创建/更新：
  - `app/api/v1/namespaces/tags.py:313`
  - `app/api/v1/namespaces/tags.py:434`
  - `app/services/tags/tag_write_service.py:60`
  - `app/services/tags/tag_write_service.py:89`
- Users 创建/更新：
  - `app/api/v1/namespaces/users.py:224`
  - `app/api/v1/namespaces/users.py:291`
  - `app/services/users/user_write_service.py:50`
  - `app/services/users/user_write_service.py:77`
- Instances 创建/更新：
  - `app/api/v1/namespaces/instances.py:549`
  - `app/api/v1/namespaces/instances.py:689`
  - `app/services/instances/instance_write_service.py:58`
  - `app/services/instances/instance_write_service.py:113`

风险：
- 双重解析会带来语义漂移入口（两个位置的 `list_fields/preserve_raw_fields/checkbox` 策略一旦不一致，就会出现端点口径分裂）。
- 重复工作与可读性下降（“到底 canonicalization 在哪里发生”不再单一）。

建议：
- 二选一收敛（按标准优先 Service 入口）：
  - API 层：只负责拿到 raw payload（JSON dict 或 MultiDict）并传入 service；
  - Service 层：唯一执行 `parse_payload(...)` + `validate_or_raise(...)` 的入口（保持可被 tasks/scripts 复用）。

### 4.2 Routes 存在 fallback 分支绕过 `safe_route_call` 且未记录 `fallback=true`

标准依据：
- `docs/Obsidian/standards/backend/layer/routes-layer-standards.md:48`（所有路由函数必须通过 `safe_route_call(...)` 包裹实际执行逻辑）
- `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46`（任何降级/failover/workaround 必须记录 `fallback=true` 与 `fallback_reason`）

发现（典型形态：`try: safe_route_call(...) except SystemError: return <fallback>`）：

- `app/routes/accounts/statistics.py:57`
- `app/routes/instances/statistics.py:38`
- `app/routes/users.py:49`

风险：
- 路由存在“非 safe_route_call 覆盖路径”，会导致异常处理/事务语义/日志上下文不一致（尤其是 fallback 分支未来新增逻辑时容易引入漂移）。
- fallback 分支缺少 `fallback=true/fallback_reason` 结构化字段，不利于统一检索与告警（标准明确要求可观测性）。

建议：
- 将 fallback 收敛到“仍在 `safe_route_call` 内”的路径，并显式记录 `fallback=true/fallback_reason`：
  - 方案 A：在 `_execute()` 内捕获预期异常并调用 `app.infra.route_safety.log_fallback(...)` 后返回 fallback 页面；
  - 方案 B：将 fallback 语义上移为业务结果（例如返回 error envelope 或渲染统一错误页），避免“看起来成功但数据为空”的隐式降级。

## 5. 符合标准的关键点(通过项摘要)

- API/Routes DB 边界清晰：未发现 `app/routes/**` / `app/api/**` 直连 `Model.query` / `db.session`（见 2.2）。
- Service/Repository 写边界满足：`app/services/**` / `app/repositories/**` 未发现 `db.session.commit/rollback` 漂移（见 2.2）。
- `safe_call/safe_route_call` 覆盖良好：API v1 HTTP 方法 AST 缺失 0；Routes AST 缺失 0（见 2.3）。
- 错误字段漂移控制有效：未发现 `error/message` 或 `message_code/error_code` 互兜底链（见 2.2）。
- internal contract 已出现“单入口 normalize”的正例：`permission_snapshot(v4)` 的 categories normalize 收敛到 `app/schemas/internal_contracts/permission_snapshot_v4.py:34`（见 6.4）。

## 6. 防御/兼容/回退/适配逻辑清单(重点: `or` 兜底)

> 说明：本节只盘点 `app/**/*.py`。对每条 `or`/兜底逻辑标注“合理回退/危险兜底候选”，并给出可落地建议。

### 6.1 事务边界与异常兜底（Infra）

- 位置：`app/infra/route_safety.py:143`
  - 类型：防御/回退
  - 描述：`fallback_exception = options.get("fallback_exception", SystemError)` 默认将“非预期异常”转换为统一对外错误类型；避免异常泄露。
  - 判定：合理回退（fail-safe），但需配合可观测性。
  - 建议：对关键降级场景优先走 `log_fallback(...)`（见 6.5），避免被误用成“吞异常继续跑”。

- 位置：`app/infra/route_safety.py:165`
  - 类型：防御/fail-safe
  - 描述：`except Exception` 兜底：rollback + 记录 `unexpected=true` + 抛出 `fallback_exception(public_error)`。
  - 判定：合理回退（边界层兜底符合标准意图）。
  - 建议：对可预期失败尽量收敛到 `expected_exceptions`，减少“所有异常都走兜底”的语义损失。

- 位置：`app/infra/route_safety.py:78`
  - 类型：回退/可观测性
  - 描述：`log_fallback(...)` 强制补齐 `fallback=true` 与 `fallback_reason`，并与 `log_with_context(...)` 统一字段口径。
  - 判定：合理回退（标准推荐形态）。
  - 建议：将业务层/路由层的降级分支尽量收敛到该 helper（见 4.2 的违规点）。

### 6.2 配置回退与 canonicalization（Settings）

- 位置：`app/settings.py:218`
  - 类型：兼容/规范化
  - 描述：`value.strip() or None` 将空白字符串 canonicalize 为 `None`（语义明确：空白视为缺省）。
  - 判定：合理回退（不会覆盖合法非空值）。
  - 建议：保持该策略集中在 Settings/schema 层，避免业务层重复实现导致口径漂移。

- 位置：`app/settings.py:343`
  - 类型：回退（开发环境）
  - 描述：`SECRET_KEY/JWT_SECRET_KEY` 缺失时，非 production 生成随机值并 warning（production fail-fast）。
  - 判定：合理回退（符合“生产严格、开发可用”的常见策略）。
  - 建议：若要对齐降级标准，可在结构化日志中标注 `fallback=true/fallback_reason=missing_secret_key`（避免仅靠文本 warning）。

- 位置：`app/settings.py:372`
  - 类型：回退（开发环境）
  - 描述：`DATABASE_URL` 缺失且非 production 回退 SQLite，并只记录 `sqlite_db_file`（避免泄露连接串）。
  - 判定：合理回退（符合敏感数据标准）。
  - 建议：同上，建议补齐统一 `fallback=true/fallback_reason` 口径以便检索。

### 6.3 请求 payload 适配与前向兼容（Utils/Schemas）

- 位置：`app/utils/request_payload.py:50`
  - 类型：适配/兼容
  - 描述：统一适配 Mapping 与 MultiDict；对 checkbox 缺失补 False；支持 `preserve_raw_fields` 保留敏感字段 raw 值。
  - 判定：合理回退（输入边界适配属于预期职责）。
  - 建议：严格遵守“一次请求链路只执行一次”（见 4.1 违规点）。

- 位置：`app/utils/request_payload.py:84`
  - 类型：防御（形状兜底）
  - 描述：`multi_dict.getlist(key) or []` 确保 list 形状稳定（避免 MultiDict 异常返回破坏后续逻辑）。
  - 判定：合理回退（形状兜底，不覆盖合法值）。
  - 建议：可考虑去掉冗余 `or []`（`getlist` 通常返回 list），但属于可读性优化而非必需。

- 位置：`app/schemas/base.py:16`
  - 类型：兼容（前向兼容）
  - 描述：`extra=\"ignore\"` 默认忽略未知字段，允许客户端携带扩展字段而不导致写路径失败。
  - 判定：合理回退（前向兼容策略）。
  - 建议：对“必须严格拒绝未知字段”的接口，在具体 schema 显式开启严格模式并补单测。

### 6.4 internal contract：版本化、单入口 normalize 与 fail-fast

- 位置：`app/services/accounts_permissions/snapshot_view.py:21`
  - 类型：防御（fail-fast）/版本化
  - 描述：只接受 `permission_snapshot.version == 4`；缺失或非 v4 直接抛错，避免静默兜底。
  - 判定：合理回退（internal contract 倾向 fail-fast）。
  - 建议：如未来需要支持历史版本，应按标准新增 adapter/normalizer 并写明退出条件。

- 位置：`app/schemas/internal_contracts/permission_snapshot_v4.py:34`
  - 类型：适配/兼容（单入口 canonicalization）
  - 描述：将 `permission_snapshot(v4)` 的历史形状差异收敛到 schema 层（例如 list[str] vs list[dict]）。
  - 判定：合理回退（符合 internal contract 标准的“单入口”目标）。
  - 建议：为每个历史形状分支补单测，并枚举“支持的历史版本/形状集合”（便于后续删除）。

### 6.5 降级/回退可观测性正例（带 `fallback=true`）

- 位置：`app/services/accounts_sync/adapters/sqlserver_adapter.py:684`
  - 类型：回退/降级（failover）
  - 描述：SID 路径拿到空权限时，回退到“按用户名查询”，并使用 `log_fallback(..., fallback_reason=...)` 记录降级发生。
  - 判定：合理回退（且可观测）。
  - 建议：为该降级分支补单测或运行期告警阈值（避免长期处于降级态无人发现）。

### 6.6 业务层/边界层 `or` 兜底典型形态

- 位置：`app/services/accounts_sync/permission_manager.py:187`
  - 类型：防御/回退
  - 描述：`message or summary.get(\"message\") or \"权限同步失败\"` 为异常消息提供多级兜底（保证对外/对日志的最小可读性）。
  - 判定：合理回退（消息字段“空白视为缺省”语义明确）。
  - 建议：确保 `summary` 的 `message` 字段为 canonical（避免未来引入 `error/message` 二选一结构）。

- 位置：`app/services/connection_adapters/adapters/postgresql_adapter.py:56`
  - 类型：回退（默认值链）
  - 描述：`database_name or get_default_schema(...) or \"postgres\"` 为连接默认库提供回退链。
  - 判定：合理回退（但需语义明确）。
  - 建议：在 adapter docstring 写清“为空时连接默认库”的业务语义（避免未来误以为应 fail-fast）。

- 位置：`app/api/v1/namespaces/dashboard.py:264`
  - 类型：适配/规范化
  - 描述：`(args.get(\"type\") or \"all\").strip() or \"all\"` 将空白参数 canonicalize 为默认值。
  - 判定：合理回退（空白视为缺省）。
  - 建议：对“合法空值”场景（例如允许 `0`）避免使用 truthy `or`（改用 `is None` 或显式缺失判定）。

- 位置：`app/schemas/tags.py:59`
  - 类型：兼容/规范化
  - 描述：`cleaned or (fallback or \"primary\")` 将空白 color 归一化为默认主题色。
  - 判定：合理回退（字段语义明确：color 不应为空）。
  - 建议：保持该逻辑仅出现在 schema（避免业务层再写一遍产生口径分裂）。

## 7. 修复优先级建议

### 7.1 P0（明确违规 + 易导致口径漂移）

- 收敛 API 写路径的 `parse_payload` 执行次数：修复 `app/api/v1/namespaces/{auth,credentials,tags,users,instances}.py` 的 API+Service 双重解析（见 4.1）。
- 修复 3 个 Routes 的 fallback 分支：确保 fallback 仍在 `safe_route_call` 覆盖范围内，并记录 `fallback=true/fallback_reason`（见 4.2）。

### 7.2 P1（标准可执行性增强：减少实现分裂）

- 为 `message_code` 增加单一真源与评审规则（见 3.2）。
- 为兼容分支补齐“退出条件/迁移完成”最小记录模板（见 3.4）。
- 明确 internal contract adapter/normalizer 的推荐落点为单一路径（见 3.3）。

### 7.3 P2（工程治理/可读性）

- 逐步减少“无意义的 `or {}` / `or []`”冗余兜底（在不改变语义前提下提升可读性），并优先把默认值策略下沉到 schema/adapter 单入口。
