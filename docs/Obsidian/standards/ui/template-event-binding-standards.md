---
title: 模板事件绑定规范
aliases:
  - template-event-binding-standards
tags:
  - standards
  - standards/ui
status: active
created: 2026-01-15
updated: 2026-01-15
owner: WhaleFall FE
scope: "`app/templates/**`"
related:
  - "[[standards/ui/layer/page-entry-layer-standards]]"
  - "[[standards/ui/layer/views-layer-standards]]"
  - "[[standards/ui/grid-standards]]"
---

# 模板事件绑定规范

## 目的

- 统一“事件绑定”的落点：模板只声明语义与 hook（如 `data-action`），交互逻辑由 JS 负责绑定/委托。
- 避免 inline handler 导致的可维护性与安全问题（难审查、难复用、难做统一门禁与迁移）。

## 适用范围

- `app/templates/**`（所有页面与组件模板）。

## 规则(MUST/SHOULD/MAY)

### 1) 禁止模板内联事件处理器

- MUST NOT：在模板中写内联事件处理器（例如 `onclick="..."`、`onchange="..."` 等）。
- MUST：用 `data-action="..."`（或其他 `data-*` hook）表达“意图”，并由 JS 侧通过 `addEventListener` 或 delegation 绑定事件。

### 2) 与分层的关系（落点）

- MUST：页面级事件绑定由 [[standards/ui/layer/page-entry-layer-standards|Page Entry]] 或 [[standards/ui/layer/views-layer-standards|Views]] 负责；模板不得承载 JS 逻辑。
- SHOULD：Grid 列表页行内动作优先使用 `Views.GridPlugins.actionDelegation(...)`（见 [[standards/ui/grid-standards]]）。

## 正反例

### 正例：模板声明 data-action，JS 绑定事件

```html
<button type="button" class="btn btn-outline-secondary" data-action="refresh">
  刷新
</button>
```

```javascript
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  if (button.dataset.action === "refresh") {
    // do refresh
  }
});
```

### 反例：模板内联 onclick

```html
<button onclick="doRefresh()">刷新</button>
```

## 门禁/检查方式

- 门禁脚本：`./scripts/ci/inline-handler-guard.sh`（锁定现状 baseline；允许减少，禁止新增 inline handler）。
  - 更新 baseline：`./scripts/ci/inline-handler-guard.sh --update-baseline`（仅在历史遗留需临时保留时使用，不推荐）。
- 人工评审：模板是否出现 `on*="..."`？
