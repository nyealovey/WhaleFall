---
title: 兼容与弃用生命周期(Compatibility & Deprecation)
aliases:
  - compatibility-and-deprecation
  - deprecation-policy
  - compatibility-policy
tags:
  - standards
  - standards/backend
status: active
enforcement: design
created: 2026-01-13
updated: 2026-01-13
owner: WhaleFall Team
scope: 字段 alias/形状迁移/env alias/降级路径等兼容逻辑的引入、可观测性与退出机制
related:
  - "[[standards/backend/gate/layer/schemas-layer]]"
  - "[[standards/backend/gate/request-payload-and-schema-validation]]"
  - "[[standards/backend/gate/internal-data-contract-and-versioning]]"
  - "[[standards/backend/standard/configuration-and-secrets]]"
  - "[[standards/backend/standard/action-endpoint-failure-semantics]]"
  - "[[standards/backend/standard/sensitive-data-handling]]"
---

# 兼容与弃用生命周期(Compatibility & Deprecation)

## 1. 目的

- 把“兼容/回退/弃用”从散落的 `or` 链与临时补丁，收敛为可审计、可测试、可移除的机制。
- 避免兼容逻辑长期沉淀为“永久层”，导致语义漂移与维护成本指数上升。

## 2. 适用范围

以下都属于“兼容/弃用”：

- HTTP payload 字段重命名/字段 alias/形状迁移（旧字段/旧形状仍可被接受）。
- internal payload（snapshot/cache/JSON column）版本迁移与历史版本读取。
- Settings 环境变量重命名（`NEW_ENV` / `OLD_ENV` 的 alias）。
- 降级/回退策略（例如缓存失败降级、外部依赖失败的 business failure vs exception）。

## 3. 术语

- **兼容分支**：为了兼容历史调用方/历史数据而保留的旧逻辑路径。
- **弃用窗口**：兼容分支允许存在的时间或版本区间。
- **退出条件**：删除兼容分支的可判定条件（例如“所有数据已迁移到 v4 且观测 30 天无 v3 命中”）。

## 4. 规则（MUST/SHOULD）

### 4.1 兼容逻辑的落点（强约束）

- MUST: 写路径（HTTP body）字段 alias/类型转换/默认值/兼容策略必须落在 `app/schemas/**`（schema）侧，并由 Service `validate_or_raise(...)` 消费 typed payload（见 [[standards/backend/gate/request-payload-and-schema-validation]]）。
- MUST: internal payload 的版本化与形状迁移必须落在 adapter/normalizer 单入口（见 [[standards/backend/gate/internal-data-contract-and-versioning]]）。
- MUST: env alias 只能发生在 `app/settings.py`（见 [[standards/backend/standard/configuration-and-secrets]]）。
- MUST NOT: 在业务代码中新增 `data.get("new") or data.get("old")`、`payload.get("x") or default` 等 silent fallback 兼容链（除非该兼容逻辑位于 schema/adapter 且带单测）。

### 4.2 可观测性（避免 silent fallback）

- MUST: 兼容分支必须可被观测到（至少满足其一）：
  - 单元测试覆盖（能证明该分支仍被支持且行为稳定）
  - 结构化日志记录“兼容分支命中”（注意脱敏，禁止记录敏感字段）
- SHOULD: 对外接口的弃用应在文档或 UI 侧明确提示，不依赖服务端 silent fallback 长期吞并差异。

### 4.3 退出机制（强约束）

- MUST: 任何兼容分支都必须具备“可删除”的退出条件（时间/版本/数据迁移完成指标），并在实现处或变更文档中写明。
- MUST: 迁移完成后必须删除兼容分支，禁止长期保留“看起来无害”的 legacy fallback。

> [!note]
> 对外 API 的弃用窗口可以更长；internal payload 与 YAML 配置通常应更“严格”（更倾向 fail-fast），以避免默默带入错误配置或脏数据。

### 4.4 与事务语义的关系（避免误回滚/误提交）

- MUST: 当兼容/回退逻辑可能影响“是否回滚”的语义时，必须遵循 [[standards/backend/standard/action-endpoint-failure-semantics]]：
  - 需要原子回滚：走异常（触发 `safe_route_call` rollback）
  - 允许保留已完成子步骤写入：走业务结果失败（返回错误封套，不抛异常）

## 5. 门禁/检查方式

- MUST: 每个兼容分支至少补 1 个单元测试覆盖（正例/反例或旧形状/新形状）。
- SHOULD: 自查命令（示例）：

```bash
# 定位可能的字段 alias / 兜底链（仅提示）
rg -n \"get\\(\\\"\\w+\\\"\\)\\s*or\\s*.*get\\(\" app
```

## 6. 变更历史

- 2026-01-13：新增标准，固化兼容/弃用的落点、可观测性与退出机制。

