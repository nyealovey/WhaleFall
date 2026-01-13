---
title: 错误消息字段统一(error/message)
aliases:
  - error-message-schema-unification
tags:
  - standards
  - standards/backend
status: active
created: 2025-12-18
updated: 2026-01-13
owner: WhaleFall Team
scope: 任务/服务/路由返回结构与 API 响应封套
related:
  - "[[standards/backend/layer/api-layer-standards#响应封套(JSON Envelope)]]"
---

# 错误消息字段统一(`error/message`)

## 目的

- 消除 `error/message` 字段漂移，避免调用方写 `result.get("error") or result.get("message")` 互兜底链。
- 消除 `error_code/message_code` 字段漂移，避免调用方写 `payload.get("message_code") or payload.get("error_code")` 互兜底链。
- 固化“产生方负责结构稳定”的契约，让错误可被结构化检索、统计与治理。

## 适用范围

- 内部结果对象：任务返回值、服务返回值（包含批量/多阶段流程）。
- 对外 API：JSON 响应封套中的错误提示字段。

## 规则（MUST/SHOULD/MAY）

### 1) 产生方契约（Producer-owned contract）

- MUST：产生方必须写入 `message`（人类可读、可展示的摘要文案）。
- SHOULD：失败时可写入 `error`（诊断信息/异常信息摘要），避免把堆栈/巨型 SQL 直接塞进 `message`。
- MAY：批量/多阶段场景可写入 `errors`（错误字符串列表）。
- SHOULD：如有机器可读需求，在内部结果对象新增 `error_code`（受控枚举），禁止用 `message` 承载机器语义。
- MUST：对外 API 错误封套使用 `message_code`（见 [[standards/backend/layer/api-layer-standards#失败响应字段(固定口径)]]），不得透传 `error_code` 作为对外稳定字段。
- MUST NOT：对外 API 的 error envelope **任何位置**（包含 `extra`）都不得出现 `error_code` 字段；如需诊断请使用 `error_id` 或边界层定义的非敏感诊断字段。

### 2) 消费方约束（禁止互兜底）

- MUST NOT：在业务逻辑中新增以下互兜底链：
  - `result.get("error") or result.get("message")`
  - `result.get("message") or result.get("error")`
  - `payload.get("message_code") or payload.get("error_code")`
  - `payload.get("error_code") or payload.get("message_code")`
- MUST：消费方只读取其所在边界的 canonical 字段（内部：`message` + 可选 `error_code`；对外 API：`message` + `message_code`）。

### 3) 兼容与迁移边界

- SHOULD：如必须兼容历史结构，只允许在“边界层”做一次规范化（canonicalization），随后下游只读 canonical 字段。
- MUST：`error_code` → `message_code` 映射只允许在边界层发生一次（例如统一错误处理器/封套生成处），不得在多层重复映射。
- MUST：不得把兼容逻辑扩散到多层（任务 → 服务 → 路由 → 前端），否则后续无法一次性删除。

## 正反例

### Canonical 结果封套（推荐最小结构）

成功：

```json
{
  "status": "completed",
  "message": "执行成功",
  "details": {}
}
```

失败：

```json
{
  "status": "failed",
  "message": "执行失败",
  "error": "诊断信息（可选）",
  "errors": ["子任务失败1", "子任务失败2"]
}
```

### 禁止的互兜底链

```python
msg = result.get("error") or result.get("message")
```

## 门禁/检查方式

- 门禁脚本：`./scripts/ci/error-message-drift-guard.sh`
- Baseline：`scripts/ci/baselines/error-message-drift.txt`
- 规则：
  - 允许减少命中（删除漂移代码）
  - 禁止新增命中（新增漂移代码会阻断）

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 重写为“标准契约文档”，剥离阶段性方案叙述，补齐 MUST/SHOULD/MAY 与门禁说明。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
- 2026-01-13: 明确 `error_code` 仅内部字段, 对外统一 `message_code`, 且只允许在边界层做一次 canonicalization.
