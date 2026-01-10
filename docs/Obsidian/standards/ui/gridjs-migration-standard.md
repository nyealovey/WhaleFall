---
title: Grid.js 列表页迁移标准
aliases:
  - gridjs-migration-standard
tags:
  - standards
  - standards/ui
status: active
created: 2025-12-25
updated: 2026-01-09
owner: WhaleFall Team
scope: 所有使用 Grid.js 的列表页(含筛选/分页/排序/批量操作)
related:
  - "[[standards/ui/grid-list-page-skeleton-guidelines]]"
  - "[[standards/ui/pagination-sorting-parameter-guidelines]]"
  - "[[standards/ui/grid-wrapper-performance-logging-guidelines]]"
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[reference/development/gridjs-migration-checklist]]"
---

# Grid.js 列表页迁移标准

## 目的

- 列表页交互一致：分页/排序/筛选参数口径统一，URL 可分享，刷新不漂移。
- 后端契约稳定：列表 API 返回结构统一，避免前端写兼容分支。
- 性能可控：高频筛选/搜索有防抖，生产环境无无意义调试日志。

## 适用范围

- 前端：所有列表页（Grid.js）与 `GridWrapper` 封装。
- 后端：所有列表 API（分页/排序/筛选/批量操作依赖的查询接口）。

## 规则（MUST/SHOULD/MAY）

### 1) 前端（必须遵守）

- MUST：使用 `app/static/js/common/grid-wrapper.js` 的 `GridWrapper` 作为统一封装。
- MUST NOT：页面内直接 new `gridjs.Grid` 自行拼分页/排序参数。
- SHOULD：优先使用 Grid list page skeleton（`window.Views.GridPage.mount(...)`）收敛 wiring（筛选/URL/导出/动作委托）。详见：[[standards/ui/grid-list-page-skeleton-guidelines|Grid list page skeleton 指南]]。

#### 分页与排序参数

- MUST：分页使用 `page`（从 1 开始）与 `limit`。

详见：[[standards/ui/pagination-sorting-parameter-guidelines|分页与排序参数规范]]。

#### 刷新与日志

- MUST：刷新使用 `grid.updateConfig(...)` + `grid.forceRender()`。
- MUST NOT：直接操纵 Grid.js 内部 `pipeline/store`。
- MUST：生产环境默认不输出 GridWrapper 调试日志；仅在 `window.DEBUG_GRID_WRAPPER=true` 时允许 `console.debug`。

详见：[[standards/ui/grid-wrapper-performance-logging-guidelines|GridWrapper 性能与日志]]。

### 2) 后端契约（列表 API）

#### 输入参数

- MUST：支持 `page/limit`。
- SHOULD：排序支持 `sort/order`（`asc|desc`），不需要排序的接口可以不实现。
- MAY：其余筛选字段按页面需要追加（由 GridWrapper 透传为 query params）。

#### 返回结构（推荐）

- MUST：返回 `items` 与 `total`，且 `total` 为满足当前筛选条件的总数。
- SHOULD：统一走成功封套（例如 `jsonify_unified_success(data=...)`），并把列表数据放在 `data.items/data.total`。

示例：

```json
{
  "success": true,
  "data": {
    "items": [],
    "total": 0
  }
}
```

#### 错误结构

- MUST：避免 `error/message` 字段漂移；统一规范见：[[standards/backend/error-message-schema-unification|错误消息字段统一]]。

## 正反例

### 正例：迁移完成后只保留统一参数

- URL/请求统一使用 `page/limit`。

### 反例：页面自行拼分页字段

- 某些页面继续发送 `page_size`，导致分页大小参数被忽略或行为异常。

## 门禁/检查方式

- 分页参数门禁：`./scripts/ci/pagination-param-guard.sh`
- GridWrapper 日志门禁：`./scripts/ci/grid-wrapper-log-guard.sh`
- 结果结构漂移门禁（如涉及错误字段）：`./scripts/ci/error-message-drift-guard.sh`

## Checklist(迁移自检)

迁移自检清单已拆分为 reference, 避免 standards 混入执行清单:

- [[reference/development/gridjs-migration-checklist|Grid.js 列表页迁移 checklist]]

## 变更历史

- 2025-12-25：新增标准文档，统一 GridWrapper 落点、参数口径与门禁入口。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter, 并统一内部链接为 wikilinks.
