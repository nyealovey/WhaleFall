---
title: Views 视图层编写规范
aliases:
  - ui-views-layer-standards
tags:
  - standards
  - standards/ui
  - standards/ui/layer
status: active
enforcement: design
created: 2026-01-09
updated: 2026-01-25
owner: WhaleFall Team
scope: "`app/static/js/modules/views/**` 下所有页面与组件视图(不含 Page Entry)"
related:
  - "[[standards/ui/guide/layer/README]]"
  - "[[standards/ui/design/javascript-module]]"
  - "[[standards/ui/gate/grid]]"
  - "[[standards/ui/gate/component-dom-id-scope]]"
  - "[[standards/ui/gate/danger-operation-confirmation]]"
  - "[[standards/ui/guide/async-task-feedback]]"
---

# Views 视图层编写规范

> [!note] 说明
> Views 层只负责 DOM 与交互. 它调用 store/actions 或 services, 订阅 store 事件并渲染. Views 不应承载业务规则, 也不应直接拼接 API path 或自行实现通用 wiring.
>
> 本文为 `enforcement: design`: 描述默认分层与推荐边界. `MUST` 主要保留给安全底线(例如 XSS)或已存在门禁覆盖的条款, 其余尽量用 SHOULD 表达(避免过度设计).

## 目的

- 将页面脚本从"巨型控制器"拆为可复用 view components, 降低耦合与重复代码.
- 固化 DOM 访问, 事件绑定, XSS 转义, destroy 清理等约束, 防止页面进入半初始化与内存泄漏.
- 对齐 `Views.GridPage` 作为列表页 wiring 单一真源, 让 list pages 可迁移可回滚.

## 适用范围

- `app/static/js/modules/views/**` 下的页面脚本与组件脚本.
- 包含 `views/components/**` 与 `views/grid-page.js` 生态(plugins 等).
- Page Entry(页面启动脚本)属于 [[standards/ui/design/layer/page-entry-layer|Page Entry 标准]], 推荐逐步迁移到 `app/static/js/modules/pages/**`.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- SHOULD: Views 只负责:
  - DOM 查询/渲染/更新.
  - 绑定用户交互事件, 将动作转成 store actions 或 service 调用.
  - 订阅 store 事件并更新 UI.
- SHOULD NOT: 直接实现业务规则(聚合, 冲突判定, 权限规则等). 业务编排优先下沉到 store/actions.
- SHOULD NOT: 直接拼接 API path 或调用 `httpU`(迁移期例外建议说明理由与回收计划).

### 2) 依赖注入与全局读取

- SHOULD: view 通过参数接收 store/service/容器等依赖(能注入就注入).
- SHOULD: `window.*` 的访问规则以 [[standards/ui/guide/layer/README#全局依赖(window.*) 访问规则(SSOT)|全局依赖(window.*) 访问规则(SSOT)]] 为单一真源.
- SHOULD: Views 避免读取 allowlist 外全局, 且尽量不直接读取 `window.httpU`(优先经由 service).
- SHOULD: 组件型 view 导出 `createXView({ store, container, ... })`, 返回 `{ mount, update, destroy }`.

### 3) 事件绑定与释放

- SHOULD: 所有事件绑定在 `destroy()` 中解除(避免重复 mount 导致多次绑定).
- SHOULD: 事件通过 JS 绑定（`data-action` + delegation，或 `DOMHelpers`/原生 addEventListener）；模板内联事件处理器（`onclick="..."`）遵循 [[standards/ui/gate/template-event-binding]](该文档为 `enforcement: gate`, 以门禁为准).
- SHOULD: 列表页行内动作使用 `Views.GridPlugins.actionDelegation`, 避免重复写 click handler.

### 4) XSS 与 HTML 输出

- MUST: 用户可控内容输出必须转义:
  - 普通文本: 使用 `UI.escapeHtml`.
  - Grid cell HTML: 先转义再传给 `gridjs.html(...)`.
- MUST NOT: 将未转义的用户输入拼接到 `innerHTML`.
- SHOULD: 优先使用 `<template>` 或 DOM API 构造节点, 减少字符串模板带来的注入风险.

### 5) Grid list pages 必须使用 GridPage skeleton

- SHOULD: Grid 列表页遵循 [[standards/ui/gate/grid|Grid 列表页标准]](该文档为 `enforcement: gate`, 以门禁为准).

### 6) 高风险操作与异步反馈

- SHOULD: 高风险操作(删除/批量变更)遵循 [[standards/ui/gate/danger-operation-confirmation]].
- SHOULD: 异步任务反馈遵循 [[standards/ui/guide/async-task-feedback]](loading, disable, toast, recover).

## 正反例

### 正例: Grid list page 只写配置, wiring 交给 GridPage + plugins

- 判定点:
  - 视图层只写 DOM/交互与配置, 不重复实现 wiring.
  - 列表页通过 `Views.GridPage.mount(...)` + plugins 完成筛选/URL/action 委托等组合.
  - API path 与 query 规则下沉到 service/GridPage 生态, view 层不手写通用 helper.
- 长示例见: [[reference/examples/ui-layer-examples#Views 示例|UI Views 示例(长示例)]]

### 反例: 页面脚本重复实现通用 helper 或直接 new GridWrapper

```javascript
// 反例: 不得新增通用 escapeHtml/resolveErrorMessage 等实现.
function escapeHtml(value) {
  return String(value).replace(/</g, "&lt;");
}

// 反例: 列表页不得直接 new GridWrapper.
const grid = new window.GridWrapper(document.querySelector("#grid"), {});
```

## 门禁/检查方式

- 评审检查:
  - view 是否只做 DOM 与交互, 业务动作是否通过 store/actions 或 services?
  - 是否有 `destroy()` 并解除订阅/解绑事件?
  - 是否存在未转义的 HTML 输出?
- 自查命令(示例):

```bash
rg -n "new\\s+GridWrapper\\(|new\\s+gridjs\\.Grid\\(" app/static/js/modules/views
rg -n "function\\s+(escapeHtml|resolveErrorMessage|renderChipStack)\\(" app/static/js/modules/views
rg -n "innerHTML\\s*=\\s*.*\\+" app/static/js/modules/views
```

## 变更历史

- 2026-01-09: 新增前端 Views 分层标准, 明确 DOM/交互职责边界, 并固化 GridPage skeleton 与 XSS 转义约束.
- 2026-01-14: 对齐 `window.*` allowlist SSOT, 并明确 Page Entry 与 Views 的物理目录边界与迁移方向.
