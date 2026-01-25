---
title: Grid.js 列表页迁移 checklist
aliases:
  - gridjs-migration-checklist
tags:
  - reference
  - reference/development
status: active
created: 2026-01-09
updated: 2026-01-14
owner: WhaleFall Team
scope: Grid.js 列表页迁移的执行清单(面向自检/交付)
related:
  - "[[standards/ui/gate/grid]]"
  - "[[standards/backend/gate/layer/api-layer]]"
  - "[[standards/backend/hard/error-message-schema-unification]]"
---

# Grid.js 列表页迁移 checklist

> [!important] 说明
> 本文是 checklist(面向执行与查阅), 不是 standards SSOT.
> 规则与门禁口径以以下 standards SSOT 为准:
> - [[standards/ui/gate/grid|Grid 列表页标准]]
> - [[standards/backend/gate/layer/api-layer|API Layer 标准]] + [[standards/backend/hard/error-message-schema-unification|错误消息字段统一]]

## 迁移自检

### 1) 前端(wiring 与交互)

- [ ] 页面使用 `Views.GridPage.mount(...)` + plugins 收敛 wiring(筛选/URL/动作委托/导出等).
- [ ] 页面脚本未直接 `new gridjs.Grid(...)`, 未绕过 `Views.GridPage`.
- [ ] 页面脚本未直接 `new GridWrapper(...)`(允许位置仅 `app/static/js/modules/views/grid-page.js`).
- [ ] helpers 使用 `UI.escapeHtml/UI.resolveErrorMessage/UI.renderChipStack`, 未新增重复实现.
- [ ] filters 配置具备 `allowedKeys`(allowlist)与 `normalize`, 未透传原始 `location.search/FormData` 对象.
- [ ] 筛选输入具备 debounce(优先 FilterCard; 或等价实现).
- [ ] 分页参数仅使用 `page/limit`, 未出现 `page_size`.

### 2) 后端(契约与字段)

- [ ] 列表接口支持 `page/limit`(如有排序则支持 `sort/order`).
- [ ] 成功响应把列表数据放在 `data.items/data.total`.
- [ ] 失败响应字段遵循统一错误 schema(避免 `error/message` 互兜底链).

### 3) 门禁(建议在提交前跑一遍)

- [ ] `./scripts/ci/pagination-param-guard.sh`
- [ ] `./scripts/ci/grid-wrapper-log-guard.sh`
- [ ] `./scripts/ci/error-message-drift-guard.sh`(如本次改动涉及后端返回结构/错误字段)
