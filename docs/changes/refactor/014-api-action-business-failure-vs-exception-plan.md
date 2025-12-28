# API action: business outcome failure vs exception (plan)

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-28
> 更新: 2025-12-28
> 范围: Flask-RESTX `app/api/v1/**` action endpoints, 事务边界, 错误封套
> 关联:
> - `docs/standards/backend/api-response-envelope.md`
> - `docs/standards/backend/error-message-schema-unification.md`
> - `docs/standards/backend/action-endpoint-failure-semantics.md`
> - `docs/changes/refactor/002-backend-write-operation-boundary-plan.md`

---

## 1. 动机与范围

### 1.1 动机

当前 `app/api/v1/**` 的 action 类接口存在两类"失败"混用, 导致以下问题:

- 链路不一致: 部分 action 用 `raise AppError` 走全局异常处理, 部分 action 直接返回 `jsonify_unified_error_message(...)`.
- 事务语义不清: `safe_route_call` 以"是否抛异常"决定 commit/rollback. 当把"业务结果失败"当作异常抛出时, 会回滚掉本应保留的"已完成子步骤"写入(典型: capacity inventory 已同步但后续容量采集失败).
- RESTX 返回值陷阱: 在 Flask-RESTX Resource 内返回 `(Response, status)` 会触发 RESTX 对 `Response` 再次 JSON 序列化, 进而报错 `Object of type Response is not JSON serializable`.
- message_code 漂移: 走异常时 `message_code` 取决于异常类型的默认 `message_key`, 容易变成泛化的 `CONSTRAINT_VIOLATION` 等, 无法表达 domain 语义.

结论: 需要把"业务结果失败(business outcome failure)"与"异常(exception)"在路由层明确分开, 并把 capacity sync 等 action 统一到可预期的事务与响应策略上.

### 1.2 范围

本方案覆盖:

- `/api/v1/**/actions/*` 这类 action endpoint 的失败语义与返回策略.
- `safe_route_call` 的事务边界使用约定(何时允许 commit, 何时必须 rollback).
- Flask-RESTX Resource 的返回值规范(避免 `(Response, status)` 形态).

不在本方案范围内:

- task/worker 内部事务策略(仍遵循 task 入口自行 commit 的既有约定).
- 业务侧错误文案的重写与文案规范(仅讨论结构与语义).

---

## 2. 不变约束

- API envelope 字段口径不变: 成功与失败封套结构仍由 `unified_success_response` / `unified_error_response` 产出.
- 既有 CRUD 请求的事务语义不变: 常规写操作仍以 `safe_route_call` 做"请求级事务边界".
- 不引入新的全局中间件或破坏性框架替换.

---

## 3. 分层边界与禁止项

### 3.1 Service 层

- MUST: service 返回 canonical 字段 `message`(见 `docs/standards/backend/error-message-schema-unification.md`).
- SHOULD: service 对"可预期的失败结果"用返回值表达(例如: `{"success": False, "message": "...", "error_code": "..."}"`), 不直接 `raise` 泛化异常.
- MUST NOT: service 返回 Flask `Response`.

### 3.2 Route(Resource) 层

- MUST: Flask-RESTX Resource 只返回以下两类之一:
  - `(JsonDict, status_code)` 或 `(JsonDict, status_code, headers)` 这类可被 RESTX 序列化的结构.
  - `flask.Response` 对象(已设置 `response.status_code`).
- MUST NOT: 返回 `(Response, status_code)` 元组.
- SHOULD: "异常"用 `raise AppError` 进入 `WhaleFallApi.handle_error`.
- SHOULD: "业务结果失败"用"返回错误 Response"表达, 避免触发 rollback.

---

## 4. 定义: 业务结果失败 vs 异常

### 4.1 业务结果失败(business outcome failure)

定义: 请求合法且被成功处理, 业务流程按预期执行到了某个判定点, 但由于外部依赖/数据状态/权限等原因得出"失败结果". 这类失败是 domain 允许发生的结果, 不是代码 bug.

典型特征:

- 不应当触发请求级 rollback(尤其当已完成子步骤写入需要保留).
- 需要对外返回可展示的 `message`, 可选 `error_code`, 可选 `error_id`.
- 需要在日志中可追踪(推荐用 `jsonify_unified_error_message(..., extra=...)` 产出 payload 并记录).

推荐返回策略(默认):

- 返回 error envelope(Response), HTTP 状态码使用 4xx(常见: 400/409/504), 但不通过抛异常触发 rollback.
- 仅在"必须回滚"的场景才把它提升为异常(见 4.2).

### 4.2 异常(exception)

定义: 请求无法被正确处理, 或者出现了非预期的控制流(代码 bug, 系统故障, 不可恢复的异常). 这类失败应当由异常机制统一处理, 并触发 rollback.

典型特征:

- 参数校验失败, 权限失败, 资源不存在.
- 程序错误, 依赖库异常, 未捕获异常.
- 需要 `safe_route_call` rollback, 避免写入半成品.

推荐返回策略:

- `raise ValidationError/NotFoundError/ConflictError/...` 由 `WhaleFallApi.handle_error` 输出 error envelope.

---

## 5. 事务语义: 以 safe_route_call 为边界

`safe_route_call` 的关键行为:

- `func()` 正常返回: `db.session.commit()`.
- 捕获到 handled exceptions 或其他异常: `db.session.rollback()` 并重新抛出.

因此, action endpoint 必须先做语义选择:

- 希望 commit(即使对外失败): 用"业务结果失败"返回 error Response, 不抛异常.
- 希望 rollback: 用异常抛出.

这不是"HTTP status 决定事务", 而是"控制流(抛不抛异常)决定事务".

---

## 6. 对现有 action 的分类与结论

### 6.1 Connection test(`/api/v1/connections/actions/test`)

- 连接失败属于业务结果失败: 请求合法, 外部 DB 不可达是预期结果.
- 需要保留写入: `last_connected` 等字段用于可观测性.
- 结论: 维持"业务结果失败返回 error Response, 不抛异常"路线.

### 6.2 Accounts sync(`/api/v1/accounts/actions/sync`)

- 下游同步失败属于业务结果失败: 请求合法, 下游返回失败是预期结果.
- 结论: 维持"业务结果失败返回 error Response, 不抛异常"路线.

### 6.3 Capacity sync(`/api/v1/instances/<id>/actions/sync-capacity`)

现状问题:

- `synchronize_inventory()` 可能已经写入 instance_databases, 但后续 `collect_capacity()` 失败时通过 `raise ConflictError(...)` 触发 rollback, 会回滚掉 inventory 同步结果.

结论:

- capacity sync 的"连接失败/无容量数据/外部采集失败"应归类为业务结果失败, 用返回 error Response 表达, 以允许 commit 保留 inventory 等子步骤写入.
- "资源不存在/权限不足/请求不合法"仍归类为异常.

---

## 7. 分阶段计划(每阶段验收口径)

### Phase 1: 规范落地(最小改动)

- 为 action endpoint 建立统一的"业务结果失败"返回 helper(建议新增 `BaseResource.error_message(...)` 或 module-level helper), 避免再次出现 `(Response, status)`.
- 把 capacity sync 中"期望发生的失败"从 `raise` 改为"返回 error Response", 并补齐 `message_code`(建议新增 `CAPACITY_SYNC_FAILED` 或复用 `SYNC_DATA_ERROR`).

验收:

- `pytest -m unit tests/unit/routes/test_api_v1_instances_sync_capacity_contract.py`
- 新增 failure contract test 覆盖"inventory 已同步但容量采集失败"时不会 500, 且返回预期 error envelope.

### Phase 2: 扫描与门禁

- 全仓扫描 v1 namespaces, 禁止 `(Response, status)` 返回形态(静态 rg 门禁或 unit test).
- 补齐 action endpoint 的分类表(见 6)与实践示例.

验收:

- `rg -n \"\\(Response, status\\)\" app/api/v1/namespaces` 结果为空.
- `pytest -m unit tests/unit/routes` 通过.

---

## 8. 风险与回滚

### 风险

- 某些 action 在失败时不再 rollback, 可能保留"已完成子步骤"写入, 需要确认这些写入对业务是期望的.
- `message_code` 的调整可能影响前端或埋点的分支判断(如存在).

### 回滚

- capacity sync 可快速回退为原 `raise ConflictError` 行为.
- helper 引入为纯增量, 回滚时只需恢复调用点.

---

## 9. 验证与门禁

- 单测: 为每个被改造的 action 增加至少 1 条 failure contract test.
- 搜索门禁: 增加一个 unit test 或 CI 脚本, 在 `app/api/v1/namespaces/**` 范围内禁止 `return response, status`.
