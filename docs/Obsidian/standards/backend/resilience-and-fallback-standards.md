---
title: 回退/降级/容错策略标准(Resilience & Fallback)
aliases:
  - resilience-and-fallback-standards
  - fallback-standards
  - graceful-degradation
tags:
  - standards
  - standards/backend
status: active
created: 2026-01-13
updated: 2026-01-13
owner: WhaleFall Team
scope: 运行期容错、降级、failover 与临时 workaround 的引入约束（避免 silent fallback 与语义漂移）
related:
  - "[[standards/backend/action-endpoint-failure-semantics]]"
  - "[[standards/backend/write-operation-boundary]]"
  - "[[standards/backend/compatibility-and-deprecation]]"
  - "[[standards/backend/structured-logging-context-fields]]"
---

# 回退/降级/容错策略标准(Resilience & Fallback)

## 1. 目的

- 允许必要的韧性设计，但把“容错代码”限制在可审计、可观测、可移除的范围内，避免系统长期靠 silent fallback 运行。
- 避免“为了继续跑下去”而引入隐式语义改变（尤其是写操作的事务语义、错误封套口径）。

## 2. 适用范围

- 缓存/队列/外部依赖失败时的降级、failover、重试、兜底值。
- 批处理/长任务的“单项失败不影响整体”策略。
- 临时 workaround（用于绕过已知 bug/外部依赖缺陷）。

## 3. 术语

- **fail-fast**：立即失败并暴露错误（抛异常/返回错误）。
- **graceful degradation（降级）**：功能降级但保持系统可用（例如只读、使用内存兜底）。
- **failover**：切换到替代实现（例如 cache backend 不可用时切换内存模式）。
- **workaround**：为临时绕过缺陷引入的分支（必须可移除）。

## 4. 规则（MUST/SHOULD）

### 4.1 可观测性（强约束）

- MUST: 任何降级/failover/workaround 都必须显式记录结构化日志，至少包含：
  - `fallback=true`
  - `fallback_reason`（简短原因）
  - 关键维度（例如 `action`/`task`/`instance_id` 等，见 [[standards/backend/structured-logging-context-fields]]）
- MUST NOT: silent fallback（例如 `except Exception: return default` 且不记录任何告警/日志）。

### 4.2 对写操作的约束（避免语义漂移）

- MUST: 写路径的事务提交点必须遵循 [[standards/backend/write-operation-boundary]]，容错逻辑不得在可复用层引入 `commit/rollback`。
- MUST: 当“失败是否回滚”会影响数据一致性时，必须遵循 [[standards/backend/action-endpoint-failure-semantics]] 的约定：
  - 需要原子性：抛异常触发 rollback
  - 允许保留已完成子步骤：以业务结果失败返回错误封套（不抛异常）
- SHOULD: “单项失败不影响整体”优先使用 savepoint（`begin_nested()`）而不是在 service 内 `db.session.rollback()`。

### 4.3 默认值与 `or` 兜底

- SHOULD: 对可能合法为 `0/""/[]/{}` 的字段，禁止用 `or` 兜底默认值（会覆盖合法值）；改用 `is None` 或显式缺失判定。
- MAY: 仅当语义明确为“空白视为缺省”时，允许 `cleaned or None` 作为 canonicalization（且必须在 schema/adapter 单入口）。

### 4.4 退出机制（防止永久化）

- MUST: workaround/fallback 必须满足 [[standards/backend/compatibility-and-deprecation]] 的退出机制要求（可判定的删除条件）。
- SHOULD: 降级路径应有“触发阈值/告警建议”（例如连续 N 次失败才降级、降级后每 M 分钟尝试恢复），避免长期处于降级态无人发现。

## 5. 门禁/检查方式（建议）

- SHOULD: 为关键降级路径补单元测试，覆盖：
  - 主路径成功
  - 依赖失败触发降级且日志可观测（不要求断言日志内容的全量字段，但应断言“降级发生”）

## 6. 变更历史

- 2026-01-13：新增标准，统一降级/回退/容错的可观测性与退出机制约束。

