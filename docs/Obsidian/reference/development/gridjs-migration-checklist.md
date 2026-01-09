---
title: Grid.js 列表页迁移 checklist
aliases:
  - gridjs-migration-checklist
tags:
  - reference
  - reference/development
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: Grid.js 列表页迁移的执行清单(面向自检/交付)
related:
  - "[[standards/ui/gridjs-migration-standard]]"
  - "[[standards/ui/grid-list-page-skeleton-guidelines]]"
  - "[[standards/ui/pagination-sorting-parameter-guidelines]]"
  - "[[standards/ui/grid-wrapper-performance-logging-guidelines]]"
---

# Grid.js 列表页迁移 checklist

> [!important] 说明
> 本文是 checklist(面向执行与查阅), 不是 standards SSOT.
> 规则与门禁口径以 [[standards/ui/gridjs-migration-standard]] 为准.

## 迁移自检

- [ ] 页面使用 `GridWrapper` 初始化表格.
- [ ] 页面使用 `Views.GridPage` + plugins(filterCard/urlSync/actionDelegation/exportButton 等)收敛 wiring.
- [ ] 后端接口支持 `page/limit`, 并返回 `data.items/data.total`.
- [ ] 若启用排序: 后端支持 `sort/order`.
- [ ] 筛选输入具备 debounce(FilterCard 或等价实现).
- [ ] 无新增 GridWrapper 生产环境 `console.log`.

