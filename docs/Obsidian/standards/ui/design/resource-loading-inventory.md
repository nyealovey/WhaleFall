---
title: 资源加载盘点(全站资源 vs 按页资源)
aliases:
  - ui-resource-loading-inventory
tags:
  - standards
  - standards/ui
  - reference
status: active
enforcement: design
created: 2026-01-24
updated: 2026-01-24
owner: WhaleFall Team
scope: "`app/templates/base.html` 的全站资源盘点与分类方法(用于指导按需加载)"
related:
  - "[[standards/ui/README]]"
  - "[[standards/ui/design/performance]]"
  - "[[standards/ui/design/vendor-library-usage]]"
---

# 资源加载盘点(全站资源 vs 按页资源)

> [!note] 说明
> 本文用于把"现在 base.html 引入了什么"显式化, 便于按需加载与性能审查. 它不是强制标准, 标准以 [[standards/ui/design/performance]] 为准.

## 1) 分类口径

- Core(全站必需): 每个页面都需要, 否则页面无法正常展示/交互.
- Auth-only(登录后必需): 仅登录态页面需要, 未登录页面不应背负成本.
- Page-only(按页): 仅特定页面需要, 必须通过 `extra_css`/`extra_js` 引入.

## 2) 当前 base.html 的资源结构(按功能分组)

### Core CSS(全站)

- Bootstrap CSS
- 字体与主题: fonts, theme
- 全局 Token 与全局样式: variables, global
- 通用组件样式: buttons, forms, table, charts, modals, metric-card, status-pill, progress, filters(common)

### Auth-only CSS(登录态)

- CRUD modal 样式(例如修改密码等)

### Core JS(全站通用能力)

- Bootstrap bundle(交互组件)
- 通用工具封装: NumberFormat, EventBus, LodashUtils, DOMHelpers, httpU, timeUtils, FormValidator, ValidationRules
- UI modules: filter-card, modal, terms, async-action-feedback, button-loading, danger-confirm
- page-loader(按 `page_id` 自动 mount 页面入口)

### Auth-only JS(登录态)

- auth_service/auth_store/change-password-modals

## 3) 自查命令(更新盘点)

```bash
rg -n \"<link |<script \" app/templates/base.html
rg -n \"\\{%\\s*block\\s+extra_(css|js)\\s*%\\}\" -S app/templates
```

## 4) 按需加载改造的最低准入问题

新增或调整资源引入前必须能回答:

- 这是否是 Core 资源? 如果不是, 为什么要放进 `base.html`?
- 如果是 Auth-only, 是否已经放在 `if current_user.is_authenticated` 分支内?
- 如果是 Page-only, 是否已经移动到对应页面的 `extra_css`/`extra_js`?

