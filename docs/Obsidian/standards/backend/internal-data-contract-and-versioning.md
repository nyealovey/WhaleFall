---
title: 内部数据契约与版本化(Internal Data Contract)
aliases:
  - internal-data-contract-and-versioning
  - internal-data-contract
  - data-contract-versioning
tags:
  - standards
  - standards/backend
status: active
created: 2026-01-13
updated: 2026-01-13
owner: WhaleFall Team
scope: 内部 JSON payload（snapshot/cache/JSON column）的结构稳定、版本化与兼容退出策略
related:
  - "[[standards/backend/layer/schemas-layer-standards]]"
  - "[[standards/backend/layer/types-layer-standards]]"
  - "[[standards/backend/compatibility-and-deprecation]]"
  - "[[standards/backend/sensitive-data-handling]]"
---

# 内部数据契约与版本化(Internal Data Contract)

## 1. 目的

- 把“内部数据结构（snapshot/cache/JSON 字段）”变成可执行、可验证的契约，避免下游用 `or` 兜底链和形状适配来修补上游不稳定输出。
- 固化“单入口 canonicalization”：只在读/写入口做一次结构迁移与类型规整；业务代码只消费稳定形状。
- 为迁移/兼容提供退出机制：避免兼容分支永久化。

## 2. 适用范围

以下任一场景均属于“内部数据契约”：

- DB JSON 字段：例如 `models` 的 JSON/JSONB 列、审计 payload、快照字段。
- 缓存 payload：例如 Redis/本地 cache 中存储的 dict/list 结构。
- snapshot / 事实表输入：从外部采集后写入本系统，再被其他模块消费的结构化 payload。
- 任何跨模块/跨层传递的“结构化 dict”（不包含纯 DTO/dataclass）。

不包含：

- HTTP body payload（见 [[standards/backend/request-payload-and-schema-validation]]）
- YAML 配置文件（见 [[standards/backend/yaml-config-validation]]）

## 3. 术语

- **canonical 形状**：系统内部唯一可信的结构与类型（例如字段名、list/dict 形状、字符串是否允许空白）。
- **adapter/normalizer（适配入口）**：把任意历史形状 → canonical 形状的一次性转换入口。
- **version**：内部结构版本号，用于显式区分历史形状与迁移策略。

## 4. 规则（MUST/SHOULD）

### 4.1 版本化（强约束）

- MUST: 任何需要长期存储或跨模块消费的内部结构化 payload 必须包含显式 `version`（整数）字段。
- MUST: 写入端必须只写入**最新版本**的 canonical 形状（禁止“写旧版本以兼容下游”）。
- MUST: 读取端必须显式处理：
  - 已支持版本：转换为 canonical 形状
  - 未知版本：fail-fast（抛异常/返回错误），禁止 silent fallback 为 `{}`/`[]`

### 4.2 单入口 canonicalization（强约束）

- MUST: internal payload 的“形状兼容/字段 alias/类型转换/默认值补齐”必须收敛到 adapter/normalizer（单入口）完成一次。
- MUST NOT: 在 Service/Repository/业务逻辑中写结构兼容链，例如：
  - `data.get("new") or data.get("old")`
  - `_ensure_str_list_from_dicts(x) or _ensure_str_list(x)`
  - `payload.get("x") or []`（当 `[]` 可能是合法值时）
- SHOULD: adapter/normalizer 优先使用 pydantic model（或 TypedDict + 显式 normalize 函数），并遵循 [[standards/backend/layer/schemas-layer-standards]] 的兼容/默认值约束。

### 4.3 `or` 兜底使用约束（关键）

- SHOULD: 当合法值可能为 `0/""/[]/{}` 时，禁止用 `or` 兜底默认值；改用 `is None` 或显式“缺失判定”。
- MAY: 仅当语义明确为“空白视为缺省”时，允许在 adapter/schema 内使用 `cleaned or None` 做 canonicalization，但必须通过命名或校验规则明确语义，并补单测。

### 4.4 兼容退出机制（防止永久化）

- MUST: 每个 adapter 支持的历史版本集合必须可枚举（例如只支持 v3/v4，不允许“无限兼容”）。
- SHOULD: 每个历史版本兼容分支必须有退出策略，参考 [[standards/backend/compatibility-and-deprecation]]。

## 5. 门禁/检查方式（建议）

- 单元测试（必须）：为每个 internal contract 的 adapter 覆盖：
  - canonical 输入（最新版本）→ 输出稳定
  - 至少 1 个历史版本输入 → 输出稳定
  - 未知版本 → fail-fast
- 静态自查（示例）：

```bash
# 识别业务层的字段 alias / 形状兜底链（仅作为提示，不能替代人工判定）
rg -n \"get\\(\\\"\\w+\\\"\\)\\s*or\\s*.*get\\(\" app/services app/repositories
```

## 6. 变更历史

- 2026-01-13：新增标准，收敛 internal payload 的版本化与单入口 canonicalization 口径。

