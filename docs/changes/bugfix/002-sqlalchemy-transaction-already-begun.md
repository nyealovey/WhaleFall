# 修复文档：`InvalidRequestError: A transaction is already begun on this Session`

## 1. 背景与现象

在创建/恢复等写接口中出现如下报错（服务端 traceback 关键段）：

- `sqlalchemy.exc.InvalidRequestError: A transaction is already begun on this Session.`
- 触发点：`with db.session.begin():`
- 表现：接口被 `safe_route_call` 捕获后统一转为 `SystemError`，前端只看到类似“创建实例失败”的通用文案。

相关代码位置：

- 创建实例：`app/routes/instances/manage.py:454`
- 恢复实例：`app/routes/instances/manage.py:564`
- 统一异常包装：`app/utils/route_safety.py:116-141`

当前依赖版本（仓库锁定）：

- `sqlalchemy==2.0.43`
- `flask-sqlalchemy==3.1.1`

## 2. 根因分析

### 2.1 SQLAlchemy 2.0 的默认行为：Session 会自动开启事务（autobegin）

在 SQLAlchemy 2.0 中，`Session` 默认启用“autobegin”：

- 只要发生一次数据库访问（哪怕是只读查询），该 `Session` 就会进入“已开始事务”的状态。
- 一旦事务已开始，再调用 `Session.begin()`（即 `with db.session.begin():`）会直接抛出：`InvalidRequestError: A transaction is already begun on this Session.`

### 2.2 本项目的典型触发链：登录态下路由执行前就已经发生了 DB 查询

多数路由带有 `@login_required`，而 Flask-Login 在请求链路中会加载用户对象，导致**在进入视图函数之前**就发生数据库访问，从而让 `db.session` 提前进入“事务已开始”的状态。

证据（用户加载器使用 ORM 查询）：

- `app/__init__.py:load_user()` 内部调用：`user_model.query.get(int(user_id))`

因此，即便视图函数内部完全不做查询，只要你在后续写逻辑里调用了 `with db.session.begin():`，也会因为“事务已开始”而报错。

### 2.3 额外放大器：部分路由/闭包先查询再 `begin()`

除了 “user_loader 预先查询” 之外，代码中还存在 “先查询/访问关系，再 `with db.session.begin()`” 的模式，进一步提高触发概率，例如：

- `Instance.query.get_or_404(...)` 后再 `with db.session.begin():`
- `Tag.query.get_or_404(...)` 后调用 `_delete_tag_record()`（其内部 `with db.session.begin():`）

这类模式在 SQLAlchemy 2.0 下基本属于“必炸模板”。

## 3. 影响范围（如何快速定位）

定位入口：全仓扫描 `with db.session.begin():`

```bash
rg -n "with\\s+db\\.session\\.begin\\(\\)" app
```

对每个命中点，重点检查两类情况：

1. 同一函数/闭包中是否存在 “查询在前、begin 在后”；
2. 即使本函数内没有查询，也要评估：该函数是否处于登录态路由链路（可能已被 `load_user()` 预先触发了查询）。

## 4. 修复目标

1. 所有写接口不再因 “transaction already begun” 直接失败。
2. 写操作保持原有的原子性/可回滚能力。
3. 事务边界清晰：成功提交、失败回滚；并避免让 Session 留在不可用状态（尤其是捕获异常后继续复用 Session 的场景）。

## 5. 修复方案

### 方案 A（推荐）：把“提交/回滚”统一收敛到 `safe_route_call`

思路：既然项目规范要求路由使用 `safe_route_call`，就把事务生命周期也放到这里，避免各路由散落的事务模板。

推荐行为：

- 业务闭包执行成功：`db.session.commit()`
- 捕获到任何异常（含 `handled_exceptions` 与“意外异常”）：`db.session.rollback()` 后再抛出（保持现有异常行为不变）

优点：

- 不依赖 `Session.begin()`，不会被 “autobegin” 阻断。
- 提交/回滚行为一致，减少“写成功但没提交”“异常后 session 脏了”的隐患。
- 便于逐步清理现存的 `with db.session.begin()` 模板。

注意点：

- 如果某些路由本身会返回流式响应/长连接，应评估 commit 时机（通常不建议在流式响应期间持有事务）。
- 若业务闭包内部已显式 `commit()/rollback()`，外层再 commit/rollback 需要确认幂等性（通常 commit 两次不会造成数据错误，但可能引发额外 SQL/状态变化，需通过回归测试确认）。

### 方案 B（次选）：移除 `with db.session.begin()`，改用“显式 commit + 异常 rollback”

适用于范围较小的快速修复（例如只修复 `create_instance`/`restore_instance` 两个接口）：

- 用 `db.session.add(...)` + `db.session.commit()` 替代 `with db.session.begin():`
- 异常路径确保调用 `db.session.rollback()`（可在 `safe_route_call` 内统一处理，或在局部捕获 `SQLAlchemyError`）

优点：改动直观，行为清晰，不依赖 begin 模式。

缺点：如果 rollback 没统一收敛，容易遗漏导致“后续请求复用 session 时异常连锁”。

### 方案 C（不推荐作为默认）：使用 `begin_nested()` / `begin(nested=True)` 兜底

动机：在“已存在外层事务”的情况下用 SAVEPOINT 包裹写操作，避免 `begin()` 抛错。

主要问题：

- 嵌套事务提交只会释放 SAVEPOINT，不会提交外层事务；若外层没有明确 `commit()`，写入最终可能在 teardown 时被回滚。
- 对于“以 `with db.session.begin()` 作为提交点”的现有代码，这种替换容易造成“看起来成功但实际没落库”的隐性故障。

因此不建议把 `begin_nested` 作为默认修复方式，除非你同时明确了外层事务的提交策略。

## 6. 推荐落地步骤（面向 PR 的执行清单）

1. 选择方案 A：在 `app/utils/route_safety.py` 中统一处理 `commit/rollback`（成功提交、失败回滚）。
2. 全仓扫描并逐步清理 `with db.session.begin()`：
   - 对写接口：删除 begin 模板，直接 `add/flush`，提交交给 `safe_route_call`。
   - 对纯服务层：若不经 `safe_route_call`，保持显式 commit/rollback 或补充独立事务管理（视调用方而定）。
3. 回归验证：
   - 创建实例：`POST /instances/api/create`
   - 恢复实例：`POST /instances/api/<id>/restore`
   - 其它包含 begin 的功能点（标签删除、用户更新、分类变更等）按需抽样回归。

## 7. 验证清单

1. 复现用例：登录后创建实例不再触发 `InvalidRequestError`。
2. 异常用例：提交非法参数导致 `ValidationError` 时，接口返回符合预期，且后续请求不受影响（Session 未“卡死”）。
3. 并发用例（可选）：同时创建同名实例时，仍应由数据库唯一约束兜底并返回合理错误（建议在后续改造中用 `IntegrityError` 兜底替代“先查再插”的竞争窗口）。

## 8. 回滚方案

若线上出现不可控影响：

- 首先回滚到旧版本代码（保持现有错误但恢复历史行为）。
- 同时建议补充临时告警：捕获 `InvalidRequestError` 的日志聚合，便于确认是否存在其它隐蔽触发点。

## 9. 兼容/回退/兜底逻辑记录（便于 code review 与后续清理）

- 类型：兼容（框架升级适配）
  - 描述：适配 SQLAlchemy 2.0 的 `autobegin` 行为，避免在“事务已开始”状态下再次 `begin()`。
- 类型：防御（resilience）
  - 描述：在统一入口（`safe_route_call`）集中 `rollback`，避免异常后 Session 处于失败状态影响后续请求。
- 类型：回退（fail-safe）
  - 描述：若短期无法全量迁移，优先为关键写接口改为显式 `commit/rollback`，确保核心路径可用。

