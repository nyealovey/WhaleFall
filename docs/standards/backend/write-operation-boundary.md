# 写操作事务边界（Write Operation Boundary）

本项目约定：**事务提交/回滚只发生在“事务边界入口”**，其余可复用业务层不得直接 `commit()`。

## 1. 允许/禁止（强约束）

### 允许 `db.session.commit()` 的位置（事务边界入口）

- `app/utils/route_safety.py`：`safe_route_call` 统一在视图成功后提交，异常时回滚
- `app/tasks/**`：任务入口可按需提交/回滚（长任务可分段 commit）
- `app/utils/logging/queue_worker.py`：worker 入口提交
- `scripts/**`：运维/一次性脚本入口提交

### 禁止 `db.session.commit()` 的位置

- `app/services/**`：可复用 service/repository 不允许 commit（必须用 `flush()`）
- `app/routes/**`：routes 不允许直写 `db.session.*`（由 `safe_route_call` + service 组合完成）

## 2. 约定的调用链

### HTTP 写入口

`route (safe_route_call) -> WriteService -> Repository(add/delete/flush)`

- route 只做：参数解析、权限校验、调用 service、统一响应
- service/repository 只做：写入（`add/delete/flush`）、校验、领域编排
- `safe_route_call` 负责：`commit/rollback`

### tasks/worker/scripts

`task/worker/script -> Service/Coordinator -> Repository(add/delete/flush)`

- 任务/脚本入口负责 `commit/rollback`（可按阶段提交）
- service 层不得提交事务

## 3. 局部原子性（savepoint）

当 service 需要“失败不落库但不中断外层流程”（例如：返回失败结果而不是抛异常）时：

- 使用 `with db.session.begin_nested(): ... db.session.flush()` 创建 **savepoint**
- 禁止在 services 内使用 `db.session.rollback()` 回滚整个请求事务

## 4. 门禁脚本

- routes 写操作门禁：`scripts/ci/db-session-route-write-guard.sh`
- services commit 漂移门禁：`scripts/ci/db-session-commit-services-drift-guard.sh`
- 全局写边界门禁（组合）：`scripts/ci/db-session-write-boundary-guard.sh`

