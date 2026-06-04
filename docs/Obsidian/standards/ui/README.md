---
title: UI 标准索引
aliases:
  - ui-standards
tags:
  - standards
  - standards/ui
  - standards/index
status: active
enforcement: guide
created: 2025-12-23
updated: 2026-06-04
owner: WhaleFall Team
scope: UI standards 入口与索引
related:
  - "[[standards/README]]"
  - "../../../../../DESIGN.md"
---

# UI 标准

本目录定义前端/UI 的结构、交互、安全、可访问性与门禁标准。视觉系统不在本目录重复维护。

## 视觉 SSOT

- 根目录 `DESIGN.md` 是视觉系统单一真源，负责界面气质、密度、配色、动效与组件视觉口径。
- 本目录只保留结构契约、可访问性、安全、数据 hook、分层、门禁与实现载体规则。
- 新增 UI 规则不得复制 `DESIGN.md` 的视觉描述；发现旧视觉描述应删除或改为链接。

## 关键入口(少量)

- [[standards/ui/design/performance|前端性能标准(SSR + Progressive Enhancement)]]
- [[standards/ui/design/jinja-template-composition|Jinja 模板组织与复用标准]]
- [[standards/ui/guide/layer/README|前端分层(layer)标准索引]]
- [[standards/ui/design/javascript-module|前端模块化(modules)规范]]
- [[standards/ui/design/vendor-library-usage|第三方库(vendor)使用标准]]
- [[standards/ui/gate/design-token-governance|设计 Token 治理(CSS Variables)]]
- [[standards/ui/gate/layout-sizing|Layout Sizing Gate]]
- [[standards/ui/gate/button-hierarchy|按钮层级与状态]]
- [[standards/ui/gate/template-event-binding|模板事件绑定规范]]
- [[standards/ui/gate/grid|Grid 列表页标准]]
- [[standards/ui/gate/danger-operation-confirmation|高风险操作二次确认]]
- [[standards/ui/design/metric-card|MetricCard 指标卡标准]]
- [[standards/ui/guide/accessibility-baseline|可访问性(A11y)基线标准]]

## 参考(非强制入口)

- [[standards/ui/design/vercel-react-best-practices-mapping|Vercel React Best Practices 到 Flask + Jinja 的映射]]
- [[standards/ui/design/resource-loading-inventory|资源加载盘点(全站资源 vs 按页资源)]]

## 全量浏览(不维护手工清单)

```query
path:"standards/ui"
```
