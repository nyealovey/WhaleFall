---
title: 写操作事务边界(Write Operation Boundary)
aliases:
  - write-operation-boundary
tags:
  - standards
  - standards/backend
status: active
created: 2025-12-25
updated: 2026-01-08
owner: WhaleFall Team
scope: 写操作的事务提交/回滚边界与门禁
related:
  - "[[standards/backend/action-endpoint-failure-semantics]]"
---

# 写操作事务边界(Write Operation Boundary)

本项目约定：**事务提交/回滚只发生在“事务边界入口”**，其余可复用业务层不得直接 `commit()`。

## 1. 目的

- 统一写操作的事务边界入口, 防止 service/repository 误 commit 导致事务语义漂移.
- 保证可复用业务层可组合, 让 route/task/script 作为唯一的提交/回滚决策点.

## 2. 适用范围

- HTTP 写接口: `app/api/**` + `safe_route_call` 的请求级事务.
- 后台任务: `app/tasks/**` 与 worker 入口.
- 运维/一次性脚本: `scripts/**`.

## 3. 规则（允许/禁止，强约束）

### 3.1 允许 `db.session.commit()` 的位置（事务边界入口）

- `app/infra/route_safety.py`: `safe_route_call` 统一在视图成功后提交, 异常时回滚
- `app/tasks/**`：任务入口可按需提交/回滚（长任务可分段 commit）
- `app/infra/logging/queue_worker.py`: worker 入口提交
- `scripts/**`：运维/一次性脚本入口提交

### 3.2 禁止 `db.session.commit()` 的位置

- `app/services/**`：可复用 service/repository 不允许 commit（必须用 `flush()`）
- `app/routes/**`：routes 不允许直写 `db.session.*`（由 `safe_route_call` + service 组合完成）

## 4. 约定的调用链

### HTTP 写入口

`route (safe_route_call) -> WriteService -> Repository(add/delete/flush)`

- route 只做：参数解析、权限校验、调用 service、统一响应
- service/repository 只做：写入（`add/delete/flush`）、校验、领域编排
- `safe_route_call` 负责：`commit/rollback`

### tasks/worker/scripts

`task/worker/script -> Service/Coordinator -> Repository(add/delete/flush)`

- 任务/脚本入口负责 `commit/rollback`（可按阶段提交）
- service 层不得提交事务

## 5. 局部原子性（savepoint）

当 service 需要“失败不落库但不中断外层流程”（例如：返回失败结果而不是抛异常）时：

- 使用 `with db.session.begin_nested(): ... db.session.flush()` 创建 **savepoint**
- 禁止在 services 内使用 `db.session.rollback()` 回滚整个请求事务

## 6. 正反例

### 6.1 正例: route/task 决策 commit/rollback

- route: 用 `safe_route_call` 包住 service 调用, 不在 route/service 内手动 commit.
- service/repository: 只做 `add/delete/flush`, 需要局部回滚时用 `begin_nested()`.

### 6.2 反例: service 层直接 commit/rollback

- 在 `app/services/**` 内调用 `db.session.commit()` 破坏可复用性与事务一致性.
- 在 `app/services/**` 内调用 `db.session.rollback()` 回滚整个请求事务(应由入口决定).

## 7. 门禁/检查方式

- routes 写操作门禁：`scripts/ci/db-session-route-write-guard.sh`
- services commit 漂移门禁：`scripts/ci/db-session-commit-services-drift-guard.sh`
- 全局写边界门禁（组合）：`scripts/ci/db-session-write-boundary-guard.sh`

## 8. 变更历史

- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
