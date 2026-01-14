---
title: Grid 列表页标准
aliases:
  - grid-standards
  - grid-list-page-skeleton-guidelines
  - grid-wrapper-performance-logging-guidelines
  - pagination-sorting-parameter-guidelines
tags:
  - standards
  - standards/ui
status: active
created: 2026-01-14
updated: 2026-01-14
owner: WhaleFall Team
scope: 所有基于 Grid.js 的列表页, 以及 `GridWrapper`/`Views.GridPage`/plugins 生态
related:
  - "[[standards/ui/layer/README]]"
  - "[[standards/backend/layer/api-layer-standards]]"
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[reference/development/gridjs-migration-checklist]]"
---

# Grid 列表页标准

## 目的

- 让 Grid 列表页的 wiring(筛选/URL/导出/动作委托/错误处理)收敛为单一真源, 页面脚本只保留 "配置 + domain renderers".
- 统一分页/排序参数, 确保 URL 可分享且刷新行为稳定.
- 固化刷新路径与日志开关, 避免依赖 Grid.js 内部实现导致回归.

## 适用范围

- 前端: 所有 Grid.js 列表页(含多 grid 页面), 以及 `GridWrapper` 调用方.
- 后端: 本文仅描述 UI 侧依赖契约摘要; 后端 SSOT 见 [[standards/backend/layer/api-layer-standards]] 与 [[standards/backend/error-message-schema-unification]].

## 规则(MUST/SHOULD/MAY)

### 1) 单一入口与 wiring(MUST)

- MUST: 列表页使用 `window.Views.GridPage.mount(config)` 作为唯一入口.
- MUST NOT: 页面脚本直接 `new GridWrapper(...)`(允许位置: `app/static/js/modules/views/grid-page.js`).
- MUST NOT: 页面脚本直接 `new gridjs.Grid(...)`.
- SHOULD: wiring 通过 plugins 收敛:
  - FilterCard: `Views.GridPlugins.filterCard(...)`
  - URL sync: `Views.GridPlugins.urlSync(...)`
  - Action delegation: `Views.GridPlugins.actionDelegation(...)`
  - Export: `Views.GridPlugins.exportButton(...)`
- MUST NOT: 页面脚本自行拼接分页/排序 query params(交由 `GridWrapper` + `TableQueryParams`).
- MUST NOT: 页面内绑定内联 `onclick="..."`(统一使用 `actionDelegation`/`data-action`).

### 2) 单一真源 helpers(MUST)

- MUST: 使用 `UI.escapeHtml/UI.resolveErrorMessage/UI.renderChipStack`(`app/static/js/modules/ui/ui-helpers.js`).
- MUST: 使用 `GridRowMeta.get(row)` 读取 row meta(`app/static/js/common/grid-row-meta.js`).
- MUST NOT: 在 `app/static/js/modules/views/**` 内新增重复实现:
  - `function escapeHtml(` / `function resolveErrorMessage(` / `function renderChipStack(`

### 3) filters contract(MUST/SHOULD)

- MUST: 配置 `filters.allowedKeys`(allowlist), 禁止直接透传 `location.search`/`FormData` 原始对象.
- SHOULD: 通过 `filters.normalize(values, ctx)` 做 domain 清洗(去空, trim, 类型规范化等).

### 4) 分页与排序参数(MUST/SHOULD)

- MUST: 分页参数统一使用 `page`(1-based)与 `limit`.
- SHOULD: `limit` 建议范围 `1~200`(具体上限以接口实现为准, 后端需要做裁剪保护).
- SHOULD: 如实现排序, 使用 `sort`/`order`(`asc`/`desc`).
- MUST NOT: 前端请求与可分享 URL 禁止使用 `page_size`.

### 5) 刷新路径与日志(MUST)

- MUST: 刷新使用 `grid.updateConfig(...)` + `grid.forceRender()`.
- MUST NOT: 直接操纵 Grid.js 内部 `pipeline/store` 或调用内部方法(例如 `pipeline.process()`).
- MUST NOT: 在 `GridWrapper` 内常驻 `console.log`.
- MUST: 调试日志仅允许通过开关输出, 且使用 `console.debug`:
  - 开关: `window.DEBUG_GRID_WRAPPER = true`
  - 统一入口: `GridWrapper` 内部 `debugLog(...)`

### 6) 高频输入防抖(SHOULD)

- SHOULD: FilterCard 场景优先使用 `UI.createFilterCard({ autoSubmitDebounce: 200~400 })`.
- SHOULD: 非 FilterCard 场景在调用 `GridWrapper.setFilters(...)` 前自行做 debounce, 避免连发刷新.

### 7) 多 grid 页面(MUST/SHOULD)

- MUST: 每个 grid 使用独立的 `GridPage.mount(...)` controller.
- MUST: 每个 grid 使用独立的 `filterForm`(或显式 `null`), 避免事件互相污染.
- SHOULD: 每个 grid 的筛选表单字段必须具备 `name`, 并使用 `data-auto-submit`(FilterCard 自动提交/防抖).

### 8) 模板依赖(extra_js)

列表页模板至少需要引入:

- `vendor/gridjs/gridjs.umd.js`
- `js/common/grid-wrapper.js`
- `js/modules/ui/ui-helpers.js`
- `js/common/grid-row-meta.js`
- `js/modules/views/grid-page.js`
- `js/modules/views/grid-plugins/filter-card.js`

按页面能力按需引入:

- URL 同步: `js/modules/views/grid-plugins/url-sync.js`
- 动作委托: `js/modules/views/grid-plugins/action-delegation.js`
- 导出按钮: `js/modules/views/grid-plugins/export-button.js`

## UI 侧依赖的后端契约摘要(非 SSOT)

> [!info] SSOT
> 后端 query params/封套/错误字段以以下标准为准:
> - [[standards/backend/layer/api-layer-standards#响应封套(JSON Envelope)|API Layer: 响应封套(JSON Envelope)]]
> - [[standards/backend/layer/api-layer-standards#7) Query 参数命名(canonical: snake_case)|API Layer: Query 参数命名]]
> - [[standards/backend/error-message-schema-unification|错误消息字段统一]]
>
> UI 侧依赖字段摘要:
> - 列表数据: `data.items` + `data.total`.
> - 失败信息: `message`, `recoverable`, `suggestions`(如存在).

## 门禁/检查方式

- 分页参数门禁: `./scripts/ci/pagination-param-guard.sh`
- GridWrapper 日志门禁: `./scripts/ci/grid-wrapper-log-guard.sh`
- 结果结构漂移门禁(如涉及错误字段): `./scripts/ci/error-message-drift-guard.sh`
- 自查命令(示例):
  - `rg -n \"new\\s+GridWrapper\\(|new\\s+gridjs\\.Grid\\(\" app/static/js/modules`
  - `rg -n \"function\\s+(escapeHtml|resolveErrorMessage|renderChipStack)\\(\" app/static/js/modules/views`

## Checklist(迁移交付自检)

- [[reference/development/gridjs-migration-checklist|Grid.js 列表页迁移 checklist]]

## 变更历史

- 2026-01-14: 合并 `grid-list-page-skeleton-guidelines.md`/`grid-wrapper-performance-logging-guidelines.md`/`pagination-sorting-parameter-guidelines.md` 为单一 Grid 标准(SSOT).
