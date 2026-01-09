---
title: Grid list page skeleton 指南
aliases:
  - grid-list-page-skeleton-guidelines
tags:
  - standards
  - standards/ui
status: active
created: 2025-12-30
updated: 2026-01-08
owner: WhaleFall Team
scope: 所有 Grid.js 列表页(含多 grid 页面)
related:
  - "[[standards/ui/gridjs-migration-standard]]"
  - "[[standards/ui/pagination-sorting-parameter-guidelines]]"
  - "[[standards/ui/grid-wrapper-performance-logging-guidelines]]"
---

# Grid list page skeleton 指南

## 目的

- 让 Grid list pages 的 wiring（筛选/URL/导出/动作委托/错误处理）收敛为单一真源，页面脚本只保留“配置 + domain renderers”。
- 防止各页面重复实现 `escapeHtml/resolveErrorMessage/renderChipStack/resolveRowMeta` 等 helpers，避免行为漂移。
- 兼容既有 `GridWrapper`/`TableQueryParams` 生态，渐进迁移、可回滚。

## 核心原则（MUST）

### 1) 统一入口：`Views.GridPage`

- MUST：列表页使用 `window.Views.GridPage.mount(config)` 作为唯一入口。
- MUST：页面脚本不得直接 `new GridWrapper(...)`（允许位置：`app/static/js/modules/views/grid-page.js`）。
- MUST：页面不得直接 `new gridjs.Grid(...)`。

### 2) 单一真源 helpers

- MUST：使用 `UI.escapeHtml / UI.resolveErrorMessage / UI.renderChipStack`（`app/static/js/modules/ui/ui-helpers.js`）。
- MUST：使用 `GridRowMeta.get(row)` 读取 row meta（`app/static/js/common/grid-row-meta.js`）。

### 3) filters contract（allowlist + normalize）

- MUST：配置 `filters.allowedKeys`（allowlist），禁止直接透传 `location.search`/`FormData` 原始对象。
- SHOULD：通过 `filters.normalize(values, ctx)` 做 domain 清洗（去空、trim、类型规范化等）。
- MUST：分页字段统一 `page/limit`，禁止使用 `page_size`。

## 模板依赖（extra_js）

列表页模板至少需要引入：

- `vendor/gridjs/gridjs.umd.js`
- `js/common/grid-wrapper.js`
- `js/modules/ui/ui-helpers.js`
- `js/common/grid-row-meta.js`
- `js/modules/views/grid-page.js`
- `js/modules/views/grid-plugins/filter-card.js`

按页面能力按需引入：

- URL 同步：`js/modules/views/grid-plugins/url-sync.js`
- 动作委托：`js/modules/views/grid-plugins/action-delegation.js`
- 导出按钮：`js/modules/views/grid-plugins/export-button.js`

## 页面脚本目标形态（示例）

- 判定点:
  - 页面脚本只保留"配置 + domain renderers", wiring 由 `Views.GridPage` + plugins 收敛.
  - filters 必须有 allowlist(`allowedKeys`)与 normalize, 禁止透传原始对象.
- 长示例见: [[reference/examples/ui-layer-examples#Views 示例|Grid list page 示例(长示例)]]

## 多 grid 页面（MUST）

- MUST：每个 grid 使用独立的 `GridPage.mount(...)` controller。
- MUST：每个 grid 使用独立的 `filterForm`（或显式 `null`），避免事件互相污染。
- SHOULD：每个 grid 的筛选表单字段必须具备 `name`，并使用 `data-auto-submit`（FilterCard 自动提交/防抖）。

## 禁止项（MUST NOT）

- MUST NOT：在 `app/static/js/modules/views/**` 内新增 `function escapeHtml(` / `function resolveErrorMessage(` / `function renderChipStack(`。
- MUST NOT：在页面脚本自行拼接分页/排序 query params（交由 `GridWrapper` + `TableQueryParams`）。
- MUST NOT：页面内绑定内联 `onclick="..."`（统一使用 `actionDelegation` / `data-action`）。

## 关联标准

- [[standards/ui/gridjs-migration-standard|Grid.js 列表页迁移标准]]
- [[standards/ui/pagination-sorting-parameter-guidelines|分页与排序参数规范]]
- [[standards/ui/grid-wrapper-performance-logging-guidelines|GridWrapper 性能与日志]]

## 门禁/检查方式

- 人工检查: 新列表页脚本是否只保留"配置 + domain renderers", wiring 是否通过 `Views.GridPage` + plugins 收敛.
- 自查命令(示例):
  - `rg -n \"function\\s+(escapeHtml|resolveErrorMessage|renderChipStack)\\(\" app/static/js/modules/views`

## 变更历史

- 2025-12-30: 初版, 引入 `Views.GridPage` 作为列表页 wiring 的单一真源.
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
