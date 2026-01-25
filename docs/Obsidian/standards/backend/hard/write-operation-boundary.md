---
title: 写操作事务边界(Write Operation Boundary)
aliases:
  - write-operation-boundary
tags:
  - standards
  - standards/backend
status: active
enforcement: hard
created: 2025-12-25
updated: 2026-01-13
owner: WhaleFall Team
scope: 写操作的事务提交/回滚边界与门禁
related:
  - "[[standards/backend/action-endpoint-failure-semantics]]"
---

# 写操作事务边界(Write Operation Boundary)

本项目约定：

- MUST: **事务提交/回滚只发生在“事务边界入口（提交点）”**。
- MUST NOT: 其余可复用业务层不得直接 `commit()` / `rollback()`。

> [!important] 术语（避免“边界入口”语义混用）
> - **事务边界入口（提交点 / Commit point）**：代码中实际调用 `db.session.commit()` / `db.session.rollback()` 的位置。
> - **事务语义决策点（决策点 / Decision point）**：决定一次写操作“应提交还是应回滚”的业务代码位置。
>   - Web：通过“正常返回 vs 抛异常”驱动 `safe_route_call` 的 `commit/rollback`。
>   - Tasks/Scripts：由入口函数决定何时 `commit/rollback`（可分阶段提交）。
> - 默认约定：**Service 承载事务语义决策**；Routes/API 只做薄封装；Repository 只 `add/delete/flush`，不 `commit/rollback`。

## 1. 目的

- 统一写操作的**提交点**(commit/rollback 发生位置), 防止 service/repository 误 commit 导致事务语义漂移.
- 明确写操作的**决策点**(通过控制流决定提交/回滚), 降低标准口径分裂.

## 2. 适用范围

- HTTP 写接口: `app/api/**` + `safe_route_call` 的请求级事务.
- 后台任务: `app/tasks/**` 与 worker 入口.
- 运维/一次性脚本: `scripts/**`.

## 3. 规则（允许/禁止，强约束）

### 3.1 MUST: 允许 `db.session.commit()` 的位置（事务边界入口/提交点）

- `app/infra/route_safety.py`: `safe_route_call` 统一在视图成功后提交, 异常时回滚
- `app/tasks/**`：任务入口可按需提交/回滚（长任务可分段 commit）
- `app/infra/logging/queue_worker.py`: worker 入口提交
- `scripts/**`：运维/一次性脚本入口提交

### 3.2 MUST NOT: 禁止 `db.session.commit()` 的位置

- `app/services/**`：可复用 service/repository 不允许 commit（必须用 `flush()`）
- `app/routes/**`：routes 不允许直写 `db.session.*`（由 `safe_route_call` + service 组合完成）

## 4. 约定的调用链

### HTTP 写入口（提交点：`safe_route_call`）

`route/api -> safe_route_call(commit/rollback) -> WriteService(decision) -> Repository(add/delete/flush)`

- route/api 只做：参数解析、权限校验、调用 service、统一响应（不 `commit/rollback`）
- service：业务编排、校验、决定是否抛异常（决策点）
- repository：写入（`add/delete/flush`）与查询组装（不 `commit/rollback`）
- `safe_route_call`：统一 `commit/rollback`（提交点）

### tasks/worker/scripts

`task/worker/script -> Service/Coordinator -> Repository(add/delete/flush)`

- 任务/脚本入口负责 `commit/rollback`（提交点；可按阶段提交）
- service/repository 不得提交事务（只允许 `flush`；决策由入口负责）

## 5. 局部原子性（savepoint）

当 service 需要“失败不落库但不中断外层流程”（例如：返回失败结果而不是抛异常）时：

- 使用 `with db.session.begin_nested(): ... db.session.flush()` 创建 **savepoint**
- MUST NOT: 禁止在 services 内使用 `db.session.rollback()` 回滚整个请求事务

## 6. 正反例

### 6.1 正例: Web 写入口（提交点在 `safe_route_call`）

- route/api：用 `safe_route_call` 包住 service 调用，不在 route/service 内手动 `commit/rollback`。
- service：通过“正常返回 vs 抛异常”表达事务语义（决策点），需要局部回滚时用 `begin_nested()`。
- repository：只做 `add/delete/flush`，不做 `commit/rollback`。

### 6.2 反例: service 层直接 commit/rollback

- 在 `app/services/**` 内调用 `db.session.commit()` 破坏可复用性与事务一致性.
- 在 `app/services/**` 内调用 `db.session.rollback()` 回滚整个请求事务(应由入口决定).

## 7. 门禁/检查方式

- routes 写操作门禁：`scripts/ci/db-session-route-write-guard.sh`
- services commit 漂移门禁：`scripts/ci/db-session-commit-services-drift-guard.sh`
- 全局写边界门禁（组合）：`scripts/ci/db-session-write-boundary-guard.sh`

## 8. 变更历史

- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
- 2026-01-13: 明确“提交点/决策点”术语, 避免“事务边界入口”在多文档中语义混用.
