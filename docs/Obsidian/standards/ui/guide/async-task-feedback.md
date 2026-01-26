---
title: 异步任务反馈规范(Sync/Batch)
aliases:
  - async-task-feedback-guidelines
tags:
  - standards
  - standards/ui
status: active
enforcement: guide
created: 2025-12-29
updated: 2026-01-14
owner: WhaleFall Team
scope: 所有触发异步任务/批量同步/批量操作的前端入口
related:
  - "[[standards/backend/standard/error-message-schema-unification]]"
  - "[[standards/backend/gate/layer/api-layer#响应封套(JSON Envelope)]]"
---

# 异步任务反馈规范(Sync/Batch)

## 目的

- 任何 sync/batch 动作必须给用户可见反馈，禁止静默失败/静默未知。
- 统一“开始/失败/未知”文案与 tone，降低交互漂移。
- 让用户在任何情况下都能找到结果入口（默认：会话中心）。

## 适用范围

下列场景必须遵循本规范：

- 同步类：同步账户、同步容量、重算/重建类操作。
- 批量类：同步所有账户、批量导入/导出、批量删除/批量变更。
- 启动后需要等待的任务：接口返回后任务仍在后台执行，结果需要在“会话中心”查看。

## 规则（MUST/SHOULD/MAY）

### 1) 任何情况下禁止静默

- MUST：无论接口返回结构是否符合预期，必须至少展示一次用户可见反馈（toast/alert/confirm）。
- MUST NOT：仅处理 `success/error` 分支而缺少 `else` 的未知兜底。

### 2) 统一使用 outcome helper（边界层一次规范化）

- MUST：统一使用 `UI.resolveAsyncActionOutcome(response, options)` 解析结果（`app/static/js/modules/ui/async-action-feedback.js`）。
- MUST NOT：在各调用点扩散 `message || error`、`success || Boolean(message)` 等互兜底链(对齐 [[standards/backend/standard/error-message-schema-unification]])。
- SHOULD：unknown 分支必须记录一次可观测事件，推动后端契约收敛（当前默认 `EventBus.emit("async-action:unknown-response")` + `console.warn`）。

### 3) started / failed / unknown 的默认口径

- started（`tone=success`）
  - message：优先使用 `response.message`，否则使用调用点提供的 `startedMessage`。
- failed（`tone=error`）
  - message：优先使用 `response.message`（错误摘要），否则使用 `failedMessage`。
  - MAY：展示 `suggestions`（如存在）作为下一步提示。
- unknown（`tone=warning`）
  - message：固定为“操作未完成，请稍后在会话中心确认”（可由调用点覆盖）。
  - MUST：unknown 必须可观测（见 2）。

### 4) 结果入口（CTA）

- MUST：异步任务必须提供结果入口，默认指向 `/history/sessions`。
- SHOULD：确认弹窗/成功提示中提供“前往会话中心查看结果/进度”的 CTA（参考 `UI.confirmDanger` 的 `resultUrl/resultText` 选项）。
- MAY：后端返回 `data.session_id` 时，前端可在日志/埋点中携带该 ID 用于定位（当前 outcome.meta 支持 `session_id`）。

### 5) 后端契约(入口)

> [!info] SSOT
> 后端响应封套与错误字段以以下标准为准:
> - [[standards/backend/gate/layer/api-layer#响应封套(JSON Envelope)|API Layer: 响应封套(JSON Envelope)]]
> - [[standards/backend/standard/error-message-schema-unification|错误消息字段统一]]
>
> UI 侧依赖的字段摘要:
> - `message`: 用户可见摘要(用于 started/failed 的默认文案).
> - `recoverable`/`suggestions`: 失败时的恢复信息(如存在).
> - `data.session_id`: 异步会话标识(如存在, 用于观测与定位).

## 正反例（推荐用法）

```javascript
const outcome = UI.resolveAsyncActionOutcome(resp, {
  action: "accounts:syncAllAccounts",
  startedMessage: "批量同步任务已启动",
  failedMessage: "批量同步失败",
  unknownMessage: "批量同步未完成，请稍后在会话中心确认",
  resultUrl: "/history/sessions",
  resultText: "前往会话中心查看同步进度",
});

const toast = window.toast;
const warnOrInfo = toast?.warning || toast?.info;
const notify =
  outcome.tone === "success" ? toast?.success :
  outcome.tone === "error" ? toast?.error :
  warnOrInfo;

notify?.call(toast, outcome.message);
```

## 门禁/检查方式

- SHOULD：新增静态扫描门禁（先 warn 后 fail），用于发现缺少 unknown fallback 的 async action 调用点。
- 相关门禁脚本可放置在 `scripts/ci/` 并在 CI 中逐步收紧。

## 变更历史

- 2025-12-29：新增规范文档，固化 async action 的反馈口径、结果入口与后端契约要求。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter, 并统一内部链接为 wikilinks.
- 2026-01-14: 将后端 MUST 契约迁移为 SSOT 链接, UI 标准仅保留前端依赖字段摘要.
