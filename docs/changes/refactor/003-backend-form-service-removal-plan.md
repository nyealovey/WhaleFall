# 后端 form_service 全量移除方案（长期策略：写链路统一到 Service/Repository）

> 状态：Draft
> 负责人：WhaleFall Team
> 创建：2025-12-26
> 更新：2025-12-26
> 范围：后端写操作与表单写链路；彻底移除 `app/services/form_service/**`
> 关联：
> - `docs/changes/refactor/001-backend-repository-serializer-boundary-plan.md`
> - `docs/changes/refactor/002-backend-write-operation-boundary-plan.md`

---

## 1. 动机与范围

### 1.1 动机

`form_service` 当前承担了多重职责（sanitize/validate/assign/after_save + 持久化 + commit/rollback），导致：

1. **事务边界不可控**：写操作既可能在 `safe_route_call` 里 commit，也可能在 `form_service` 内部 commit（甚至存在二次 commit/部分落库风险）。
2. **职责耦合**：校验/模型赋值/关联同步/日志/缓存失效混在一个“表单服务”里，难以单元测试与复用，也难以与 `Repository/Service` 分层对齐。
3. **调用面分裂**：同一资源的写入同时存在“API route 直调 form_service”和“HTML 表单视图通过 ResourceFormView 直调 form_service”，导致迁移与门禁困难。
4. **长期维护成本高**：大量兜底/兼容逻辑散落在 form_service 与视图层（`or` 兜底、字段别名、多来源 payload），没有显式的“兼容期限/收敛策略”。

### 1.2 范围（要做）

- 全量移除目录：`app/services/form_service/**`（含 `BaseResourceService` / `ServiceResult` 及各资源表单服务）。
- 将写入能力收敛为：`routes → write services → repositories(写)`；事务边界统一到 `safe_route_call`（或显式事务管理器）。
- 将“表单专属能力”收敛为：表单 view/adapters（payload 提取、上下文构造、错误展示），不再承担持久化与事务。
- 迁移并保留现有行为：API 契约、错误口径（message/message_key）、HTML 表单交互与 flash 文案。

### 1.3 不在范围（不做）

- 不做数据库 schema 变更（除非后续独立迁移计划）。
- 不改动对外 API 的字段与语义（除非独立提案并同步前端）。
- 不引入长期双写/影子写对比；迁移以“直迁 + 小步可回退”为原则。

---

## 2. 不变约束（必须满足）

- 行为不变：现有写接口与表单交互保持一致（成功/失败条件、消息文案与 `message_key`）。
- 事务语义不降级：同一请求内写操作保持原子性；失败时能 rollback（详见 002 的事务边界策略）。
- 分层边界清晰：Repository 不 commit；Service 不 commit；commit 仅存在于 `safe_route_call` 与 tasks（或显式事务管理器）。
- 兼容逻辑可追踪：任何字段别名/兜底必须显式记录“来源/期限/移除条件”，避免永久化。

---

## 3. 现状与依赖面（需要被迁走/拆开）

### 3.1 调用面清单（关键入口）

API routes（直调 form_service.upsert）：

- `app/routes/tags/manage.py`：create/update
- `app/routes/credentials.py`：create/update（通过 `_save_via_service`）
- `app/routes/users.py`：create/update
- `app/routes/auth.py`：change password
- `app/routes/accounts/classifications.py`：create/update classification & rule

HTML 表单（ResourceFormView → BaseResourceService.upsert）：

- `app/views/mixins/resource_forms.py`（通用 GET/POST）
- `app/forms/definitions/*.py`（`service_class=...FormService`）
- `app/views/scheduler_forms.py`（scheduler job PUT 仍复用 form_service 的 ServiceResult 语义）

单元测试（直接引用 form_service）：

- `tests/unit/services/test_user_form_service.py`
- `tests/unit/services/test_classification_form_service.py`
- `tests/unit/services/test_classification_rule_form_service.py`

### 3.2 典型耦合点（阻碍移除的原因）

- `ResourceFormDefinition.service_class` 当前类型绑定 `BaseResourceService`（`app/forms/definitions/base.py`）。
- `ResourceFormView.post()` 直接依赖 `service.upsert()` 返回 `ServiceResult`（`app/views/mixins/resource_forms.py`）。
- 部分 form_service 内部存在“额外 commit/rollback”（如实例标签同步），与 002 的统一事务策略冲突。

---

## 4. 目标架构（无 form_service）

### 4.1 分层边界（写链路）

允许依赖：

- `routes/views → write services`
- `write services → repositories(写)`
- `write services → validators/normalizers`（可选）
- `repositories → models/db.session.add/delete/flush`（仅 flush，不 commit）

禁止依赖：

- `repositories → commit()`（禁止）
- `write services → commit()`（禁止）
- `views/forms → repositories`（必须经 write services）

### 4.2 关键抽象（建议落点）

#### Write Services（域写服务）

- 位置建议：`app/services/<domain>/*_write_service.py`
- 职责：
  - 规范化与校验（可委托 validator）
  - 调用 repository 执行 add/delete/flush 与关系维护
  - 触发审计日志、缓存失效（允许失败时降级记录）
- 错误处理：
  - 面向 API：抛 `ValidationError/NotFoundError/SystemError`（由 `safe_route_call` 统一 rollback + 错误封装）
  - 面向 HTML 表单：在 view 层捕获并转为可展示错误（flash + form_errors）

#### Repositories（写能力扩展）

- 在现有 read repository 基础上补齐写方法（如 `add/delete/flush/sync_relations`）。
- 仅负责 DB 语义（包含关系维护），不做业务校验与消息文案。

#### Form Adapters（表单适配层）

表单（HTML/部分 JSON PUT）本质是“展示与交互”，建议将其与“持久化/事务”彻底解耦：

- 位置建议：`app/forms/handlers/**` 或 `app/views/forms/**`
- 职责：
  - payload 提取与字段兼容（短期保留，长期收敛）
  - 上下文构造（options 列表等）
  - 将 write service 的异常映射为 UI 可展示错误
- 不做：
  - 不直接操作 `db.session`（不 add/delete/commit）

### 4.3 事务策略（依赖 002 的决策）

以 002 推荐的 `safe_route_call` 统一 commit 为前置条件：

- 所有写 route 必须通过 `safe_route_call` 执行业务函数（或采用统一事务管理器）。
- HTML 表单写入也必须纳入同一事务策略（推荐：在 `ResourceFormView.post()` 内引入 `safe_route_call` 包装）。

---

## 5. 迁移策略（长期：彻底移除）

### 5.1 总体原则

- **先收敛事务，再迁走能力，最后删除目录**：
  1) 先让所有写入都在统一事务边界内（否则“移除 form_service”会放大 commit/rollback 问题）。
  2) 将各资源写入能力迁移到 domain write services + repositories。
  3) 用表单适配层替代“表单服务”概念。
  4) 删除 form_service 与其导出入口、测试引用。

### 5.2 兼容/兜底逻辑处理原则（重要）

- **短期保留**：迁移时必须保持现有兜底/别名行为（否则会出现“重构顺手改坏输入兼容”的风险）。
- **中期收敛**：将兼容逻辑集中到“输入规范化层”（normalizer/adapter），并补齐测试覆盖。
- **长期移除**：当调用方（前端/模板/第三方）已全部迁移到 canonical 字段后，删除别名与兜底分支。

> 兼容/兜底逻辑的现状清单见“附录 A”。

---

## 6. 分阶段计划

### Phase F0：前置条件与门禁（必须先完成）

- [ ] 完成 `002` 的 Phase W1：移除 form_service 内部 `commit()`，改为 `flush()` 或交由上层事务统一处理。
- [ ] 补齐写 route 的 `safe_route_call` 覆盖：create/update 等写入口必须纳入统一事务边界。
- [ ] 为“将被迁移的写端点/表单”补齐最小契约测试/单测（至少覆盖错误 message_key）。

验收：

- `rg -n \"db\\.session\\.commit\\(\" app/services/form_service` 结果为 0（直到目录被删除）。
- `pytest -m unit` 通过。

### Phase F1：以 Tags 为样板（首个域直迁）

- [ ] 扩展 `app/repositories/tags_repository.py`：新增写方法（add/delete/flush + 关系维护）。
- [ ] 新增 `app/services/tags/tag_write_service.py`：迁移 TagFormService 的 normalize/validate/assign/after_save（日志）逻辑。
- [ ] routes 迁移：`app/routes/tags/manage.py` 的 create/update 改为调用 `TagWriteService`，并纳入 `safe_route_call`。
- [ ] HTML 表单迁移：从 `ResourceFormDefinition.service_class` 逐步切换到“表单适配层”（详见 Phase F4）。

验收：

- 现有标签创建/编辑 API 行为一致（包括错误信息与状态码）。
- `make typecheck`、`ruff check app tests`、`pytest -m unit` 通过。

### Phase F2：Credentials / Users（包含 message_key 兼容）

- [ ] `CredentialWriteService`：保留“密码非必填（更新）”等校验规则与 db 错误归一化语义。
- [ ] `UserWriteService`：保留“最后一个管理员不可禁用/降级”防御逻辑与 `message_key`。
- [ ] 迁移 routes：`app/routes/credentials.py`、`app/routes/users.py`。
- [ ] 更新单测：将 `tests/unit/services/test_user_form_service.py` 迁移为 write service/validator 测试。

验收：

- 原有 `UserFormService.MESSAGE_LAST_ADMIN_REQUIRED`/`MESSAGE_USERNAME_EXISTS` 的行为由新层承接（message_key 不漂移）。
- `pytest -m unit` 通过。

### Phase F3：Instances（处理标签同步与关系写入）

- [ ] 迁移 InstanceFormService 的 “tag_names 规范化 + 标签同步” 到 repository（关系维护）或专用同步服务。
- [ ] 彻底移除 `_sync_tags()` 内的 commit/rollback；关系写入仅做 `flush()`，统一由事务边界 commit。
- [ ] HTML 表单链路验证：实例创建/编辑表单流程可用。

验收：

- “实例保存 + 标签同步”在一个事务内（任一步失败可 rollback）。
- `pytest -m unit` 通过（如无覆盖，补齐最小单测）。

### Phase F4：表单系统解耦（移除 BaseResourceService 依赖）

- [ ] 将 `app/forms/definitions/base.py` 的 `service_class` 类型从 `BaseResourceService` 改为更窄的 Protocol（如 `ResourceFormHandler`）。
- [ ] `ResourceFormView` 改为依赖新 Protocol，并在 view 内接入 `safe_route_call` 事务包装（HTML 表单也统一 commit/rollback）。
- [ ] 为各表单资源提供 handler/adapters（只做 payload 适配 + 调用 write services + build_context）。

验收：

- `app/forms/definitions/*.py` 不再 import `app.services.form_service.*`。
- HTML 表单与原交互一致（成功重定向/失败回显/flash 文案）。

### Phase F5：Scheduler Jobs（从 form_service 迁出）

- [ ] 将 `SchedulerJobFormService` 迁移到 `app/services/scheduler/`（例如 `scheduler_job_write_service.py`），去除对 `BaseResourceService/ServiceResult` 的依赖。
- [ ] `app/views/scheduler_forms.py` 改为调用新服务，并维持现有错误封装结构。

验收：

- 内置任务触发器更新行为一致（Cron/Interval/Date）。
- 兼容字段别名（`cron_weekday/cron_day_of_week/day_of_week/weekday`）策略明确（见附录 A）。

### Phase F6：删除 form_service 与清理导出入口

- [ ] 删除 `app/services/form_service/**`，并清理：
  - `app/services/auth/__init__.py`
  - `app/services/users/__init__.py`
  - `app/services/scheduler/__init__.py`
  - 以及所有引用路径
- [ ] 更新/迁移单测：移除对旧路径的 import。
- [ ] 增加门禁（脚本或 CI 检查）：禁止出现 `app.services.form_service` import。

验收：

- `rg -n \"app\\.services\\.form_service\" app tests` 结果为 0。
- `pytest -m unit`、`make typecheck` 通过。

---

## 7. 验证与门禁（建议固定为每个 PR 的 Checklist）

- `ruff check app tests`
- `make typecheck`
- `pytest -m unit`
- 代码门禁（至少其一）：
  - `rg -n \"app\\.services\\.form_service\" app tests` 必须为 0
  - `rg -n \"db\\.session\\.commit\\(\" app | rg -v \"safe_route_call\"`（人工审查例外：tasks/脚本）

---

## 8. 风险与回滚

| 风险 | 场景 | 缓解 | 回滚 |
|------|------|------|------|
| 事务不一致 | 移除内部 commit 后，route/view 未纳入统一事务边界 | Phase F0 先补齐 `safe_route_call` 覆盖 | `git revert` 单 PR |
| 错误口径漂移 | message/message_key 与前端/模板期望不一致 | 迁移前先锁单测/契约；迁移中保持 message_key 不变 | revert + 补测试 |
| 兼容逻辑丢失 | 字段别名/兜底被“顺手清理” | 将兼容点写入附录清单并逐条迁移 | revert + 逐项补回 |
| 表单交互回退 | HTML 表单失败回显/重定向逻辑变化 | Phase F4 单独推进，先做 adapter 再删 base | revert |

---

## 附录 A：现存兼容/防御/回退/适配逻辑清单（迁移时必须逐条承接）

> 说明：本附录用于“迁移时保持行为不变”的核对清单；当迁移完成并确认调用方已收敛到 canonical 字段后，才能删除对应兜底分支。

- 位置：`app/services/form_service/resource_service.py:130`
  - 类型：兼容/防御
  - 描述：`dict(payload or {})` 允许 payload 为空时回退空 dict，避免 `NoneType` 崩溃。
  - 建议：迁移到统一的 payload normalizer（或 view adapter），并在类型上明确“允许空 payload”的语义。

- 位置：`app/services/form_service/resource_service.py:211`
  - 类型：防御/回退
  - 描述：`resource or self._create_instance()` 在创建/编辑场景兜底实例来源。
  - 建议：在 write service 层显式区分 create/update（避免隐式分支扩散）。

- 位置：`app/services/form_service/tag_service.py:193`
  - 类型：兼容
  - 描述：颜色字段 `as_str(...).strip() or "primary"`，空值回退默认颜色。
  - 建议：保留默认值策略，但将默认值来源（前端默认/后端默认）统一为单点配置。

- 位置：`app/services/form_service/tag_service.py:209`
  - 类型：防御/Workaround
  - 描述：`_create_instance()` 使用占位值规避 Tag 构造函数必填参数约束。
  - 建议：长期应消除“占位实体”概念（改为显式 create DTO → entity 构造）。

- 位置：`app/services/form_service/instance_service.py:123`
  - 类型：防御
  - 描述：端口赋值 `as_int(..., default=instance.port) or instance.port`，避免空值覆盖既有端口。
  - 建议：在 normalizer 中将 port 设为“必填且只允许 int”；update 场景用显式“是否提交该字段”判断。

- 位置：`app/services/form_service/instance_service.py:213`
  - 类型：兼容
  - 描述：`if not tag_field: return []`，允许 tag_names 缺失/空值回退为空列表。
  - 建议：保留缺省行为；长期将 tag_names 字段固定为 list[str]（由输入适配层完成解析）。

- 位置：`app/services/form_service/instance_service.py:242`
  - 类型：防御/回退
  - 描述：`_sync_tags()` 内部存在 commit/rollback 与异常吞吐（失败降级记录）。
  - 建议：按 002 统一事务边界；关系同步失败应导致整体失败或显式策略化（禁止隐藏部分落库）。

- 位置：`app/services/form_service/credential_service.py:207`
  - 类型：兼容
  - 描述：`db_type_raw = data.get(...) if ... is not None else resource.db_type ...`，支持更新场景字段缺失时回退旧值。
  - 建议：在 update DTO 中区分“字段缺失”与“字段置空”，避免 `None` 语义混淆。

- 位置：`app/services/form_service/credential_service.py:239`
  - 类型：防御/回退
  - 描述：占位密码优先读取 `WHF_PLACEHOLDER_CREDENTIAL_SECRET`，否则随机生成。
  - 建议：长期应移除占位密码路径；在模型层/工厂层提供无占位的创建方式。

- 位置：`app/services/form_service/user_service.py:253`
  - 类型：防御（guard clause）
  - 描述：`_ensure_last_admin` 防止禁用/降级最后一个管理员导致系统锁死。
  - 建议：迁移为 write service 的强约束，并用单测锁定 `message_key`。

- 位置：`app/services/form_service/password_service.py:58`
  - 类型：防御
  - 描述：`resource is None` 直接失败（未登录），避免在无用户上下文下修改密码。
  - 建议：迁移为 auth write service 的显式前置校验（与 route 权限一致）。

- 位置：`app/services/form_service/scheduler_job_service.py:254`
  - 类型：数据字段兼容（字段别名）
  - 描述：Cron 字段通过 `_pick(..., \"cron_weekday\", \"cron_day_of_week\", \"day_of_week\", \"weekday\")` 支持多命名来源。
  - 建议：明确 canonical 字段并在前端收敛；保留别名仅作为短期兼容，设定移除期限。

- 位置：`app/services/form_service/scheduler_job_service.py:322`
  - 类型：兼容/回退
  - 描述：`pick_value or part` 用表达式分段兜底缺失字段（混合输入时回退到表达式）。
  - 建议：在表单协议中定义优先级（字段 vs 表达式），并补齐测试覆盖。

- 位置：`app/services/form_service/classification_rule_service.py:218`
  - 类型：数据结构兼容（回退旧值）
  - 描述：`data.get(\"rule_expression\") or (resource.rule_expression if resource else \"{}\")`，缺失时回退已有表达式/空对象。
  - 建议：将“默认表达式来源”策略化；长期要求客户端显式提交表达式。

- 位置：`app/services/form_service/classification_rule_service.py:242`
  - 类型：规范化（canonicalization）
  - 描述：`json.dumps(..., sort_keys=True)` 以排序后的 JSON 字符串做表达式规范化与去重。
  - 建议：保留 canonicalization 逻辑，并在 repository 层对“表达式去重”建立稳定约束。

- 位置：`app/views/mixins/resource_forms.py:134`
  - 类型：适配/兼容
  - 描述：`_resolve_resource_id` 支持多种 URL 参数名（instance_id/credential_id/...），并允许 str→int 转换。
  - 建议：长期应在路由层统一参数命名；保留适配仅作为兼容层。

- 位置：`app/views/mixins/resource_forms.py:155`
  - 类型：兼容/防御
  - 描述：`req.get_json(silent=True) or {}`，JSON 解析失败回退空 dict，避免抛异常影响表单渲染。
  - 建议：保留“silent 解析 + 显式校验错误”，并将校验错误统一映射为可展示信息。

- 位置：`app/utils/data_validator.py:405`
  - 类型：兼容/适配
  - 描述：`sanitize_form_data` 支持 MultiDict `getlist`（checkbox 多值）并将单值列表压缩为 scalar。
  - 建议：迁移表单适配层时必须继续支持 MultiDict；长期可为每个字段声明“是否多值”并做强类型收敛。

- 位置：`app/utils/data_validator.py:492`
  - 类型：回退（failsafe）
  - 描述：动态数据库类型读取失败时回退静态白名单（并记录 warning）。
  - 建议：保留 failsafe；若后续强依赖动态配置，应在启动期显式校验并明确失败策略。

