---
title: Action endpoint failure semantics(business failure vs exception)
aliases:
  - action-endpoint-failure-semantics
tags:
  - standards
  - standards/backend
status: active
created: 2025-12-28
updated: 2026-01-08
owner: WhaleFall Team
scope: "`app/api/v1/**` Flask-RESTX endpoints, 尤其是 `/actions/*`, 以及 `safe_route_call` 事务边界"
related:
  - "[[standards/backend/api-response-envelope]]"
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[standards/backend/write-operation-boundary]]"
---

# Action endpoint failure semantics (business failure vs exception)

---

## 1. 目的

- 统一 action 类接口的失败语义, 明确什么是"业务结果失败"(business outcome failure)与"异常"(exception).
- 统一事务预期: 在 `safe_route_call` 下, 通过"抛异常 vs 返回响应"决定 commit/rollback, 避免误回滚已完成的子步骤写入.
- 避免 Flask-RESTX 返回值陷阱: 禁止 `(Response, status)` 形态导致 `Response is not JSON serializable`.

---

## 2. 适用范围

- `app/api/v1/**` 下的 Flask-RESTX Resource, 特别是 `/actions/*` 这类 side-effect endpoint.
- 使用 `BaseResource.safe_call(...)` / `safe_route_call(...)` 作为请求级事务边界的接口.

不包含:

- `app/tasks/**`, `scripts/**` 等非 HTTP 入口的事务策略(它们在入口自行 commit/rollback).

---

## 3. 定义

### 3.1 业务结果失败 (business outcome failure)

定义: 请求合法, 代码按预期路径完成了处理, 但业务结果为失败. 例如: 外部数据库不可达, 下游同步失败, 容量采集为空等.

关键特征:

- 这是 domain 允许发生的"失败结果", 不是代码 bug.
- 通常不应触发请求级 rollback, 尤其当"已完成子步骤写入"需要保留用于可观测性或增量推进.

### 3.2 异常 (exception)

定义: 请求无法被正确处理, 或出现非预期控制流. 例如: 参数校验失败, 权限不足, 资源不存在, 未捕获异常, 系统故障.

关键特征:

- 应触发请求级 rollback, 避免写入半成品.
- 由统一异常处理输出错误封套.

---

## 4. 规则 (MUST/SHOULD/MAY)

### 4.1 返回值形态 (Flask-RESTX)

- MUST: Resource 只允许返回:
  - `(JsonDict, status_code)` 或 `(JsonDict, status_code, headers)` 等可序列化结构.
  - `flask.Response` 对象(且必须已设置 `response.status_code`).
- MUST NOT: 返回 `(Response, status_code)` 元组.

推荐做法:

- SHOULD: 使用 `BaseResource.error_message(...)` 返回错误封套 `Response`, 避免重复写 `response.status_code = status`.

### 4.2 事务语义与 safe_route_call

`safe_route_call` 的提交规则:

- func 正常返回 -> `db.session.commit()`
- func 抛异常 -> `db.session.rollback()` 并继续抛出

因此:

- MUST: 当你希望"失败也要保留已完成的子步骤写入"时, 该失败必须走"业务结果失败", 即返回 error `Response`, 不抛异常.
- MUST: 当你希望回滚(原子性)时, 该失败必须走"异常", 即抛出 `AppError` 或其他异常, 让 `safe_route_call` rollback.

### 4.3 错误封套与 message_code

- MUST: 对外错误封套必须遵循 [[standards/backend/api-response-envelope|API 响应封套]].
- MUST: `message_code` 必须能表达 domain 语义, 不得依赖 `ConflictError` 的默认 `CONSTRAINT_VIOLATION` 作为对外稳定标识.
- SHOULD: action 类接口的"业务结果失败"优先使用 `BaseResource.error_message(..., message_key=...)` 指定 `message_code`.

### 4.4 业务结果失败的 HTTP 状态码 (方案 A)

- MUST: "业务结果失败"对外返回 error envelope, HTTP 状态码使用 4xx/5xx 中的语义值(常用: 400/409/504).
- SHOULD: 当失败来自外部依赖且可重试时, 优先选择 409/504, 并通过 `recoverable`/`suggestions` 引导用户重试.

### 4.5 savepoint (可选)

当需要"保留部分写入, 但回滚某个子步骤"时:

- MAY: 在 service/coordinator 内使用 `with db.session.begin_nested(): ...` 创建 savepoint, 让局部失败不影响外层事务(见 [[standards/backend/write-operation-boundary|写操作事务边界]]).
- MUST NOT: 在 services 内直接 `db.session.rollback()` 回滚整个请求事务.

---

## 5. 示例

### 5.1 业务结果失败: capacity sync 连接失败

```python
if not coordinator.connect():
    return self.error_message(
        f"无法连接到实例 {instance.name}",
        status=HttpStatus.CONFLICT,
        message_key="DATABASE_CONNECTION_ERROR",
        extra={"instance_id": instance.id},
    )
```

语义: 对外失败(409), 但不抛异常, 允许 `safe_route_call` commit 其他已完成写入.

### 5.2 异常: 资源不存在

```python
if instance is None:
    raise NotFoundError("实例不存在")
```

语义: 触发 rollback, 由统一异常处理输出错误封套.

---

## 6. 门禁/检查方式

- 静态扫描:
  - `rg -n \"return\\s+response\\s*,\\s*status\" app/api/v1/namespaces`
  - `rg -n \"\\(Response,\\s*status\" app/api/v1/namespaces`
- 单测:
  - action endpoint 至少包含 1 条 failure contract test, 覆盖 message_code 与事务预期(例如: capacity sync 失败后 inventory 仍保留).

---

## 7. 变更历史

- 2025-12-28: 初版, 明确 action endpoint 的失败语义与事务策略(方案 A).
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
