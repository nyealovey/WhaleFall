---
title: Modal CRUD 表单规范
aliases:
  - modal-crud-forms-standards
  - forms-views-layer-standards
tags:
  - standards
  - standards/backend
  - standards/ui
status: active
enforcement: design
created: 2026-01-09
updated: 2026-01-23
owner: WhaleFall Team
scope: "`app/templates/**/modals/**`, `app/static/js/modules/views/**/modals/**`, `app/static/js/modules/services/**`, `app/api/v1/namespaces/**`, `app/routes/**`"
related:
  - "[[standards/backend/gate/layer/routes-layer]]"
  - "[[standards/backend/gate/layer/services-layer]]"
---

# Modal CRUD 表单规范

> [!note] 说明
> 本仓库已移除 `ResourceFormView` 与 `app/forms/**` 体系, 统一采用 "页面 + 模态 + JS + /api/v1" 的 CRUD 交互.

## 目的

- 统一表单交互形态: 所有 create/edit 表单使用模态框, 避免独立表单页导致 UX 与代码风格分裂.
- 固化依赖方向: 页面路由只负责渲染, 写操作只走 `/api/v1/**`, 业务编排在 Service 中完成.
- 降低重复: 复用 `httpU`(CSRF/headers), `FormValidator`/`ValidationRules`, 以及 Grid 页面通用插件.

## 适用范围

- 页面与模态:
  - `app/routes/**`(页面路由, GET-only)
  - `app/templates/**/modals/**`(模态表单模板)
- 前端交互:
  - `app/static/js/modules/views/**/modals/**`(模态控制器)
  - `app/static/js/modules/services/**`(API service)
- 后端接口:
  - `app/api/v1/namespaces/**`(RESTX 资源, 统一响应封套)

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: 页面路由(`app/routes/**`)只负责渲染页面, MUST NOT 承载写入逻辑(例如 POST 保存表单).
- MUST: create/edit/delete 等写操作统一通过 `/api/v1/**` 完成.
- MUST: API 层负责输入校验与权限校验, 并调用 Service 完成业务动作.
- MUST NOT: 前端直接调用非 `/api/v1/**` 的写接口.
- SHOULD: 前端表单只做交互与字段级校验, 复杂业务校验必须在 Service/API 完成.

### 2) 目录结构(推荐)

```text
app/routes/
└── {domain}.py                # 页面路由, 渲染 list/index/detail

app/templates/
└── {domain}/
    ├── index.html|list.html   # 页面
    └── modals/
        └── {entity}-modals.html

app/static/js/modules/
├── services/
│   └── {entity}_service.js
└── views/
    └── {domain}/
        ├── index.js|list.js
        └── modals/
            └── {entity}-modals.js

app/api/v1/namespaces/
└── {entity}.py                # /api/v1/{entity} CRUD
```

### 3) 依赖规则

- 模态 JS 允许依赖:
  - MUST: `httpU`(统一 headers + CSRF)
  - SHOULD: `FormValidator`/`ValidationRules`
  - SHOULD: `toast`, `UI.confirmDanger`, `GridPage`/`GridPlugins`(若在列表页)

- 模态 JS 禁止依赖:
  - MUST NOT: 直接访问全局未声明的业务对象(除 `window.*` 明确存在的基础工具)
  - MUST NOT: 直接拼接 CSRF token(使用 `httpU` 即可)

- 页面路由允许依赖:
  - SHOULD: `safe_route_call`
  - SHOULD: 仅做 query 参数解析与 `render_template`

- 页面路由禁止依赖:
  - MUST NOT: 依赖任何 "表单视图基类"(例如 `ResourceFormView`)
  - MUST NOT: 承载 create/edit 的 POST 保存逻辑

### 4) CSRF 与安全

- MUST: `/api/v1/**` 写接口必须 `@require_csrf`.
- MUST: 前端调用写接口必须使用 `httpU`(它会从 `<meta name="csrf-token">` 注入 `X-CSRFToken`).
- MUST: 写接口必须保留 `@api_permission_required`, 不得因前端限制而移除后端权限控制.

### 5) 命名规范

| 类型 | 命名规则 | 示例 |
|---|---|---|
| 模态模板 | `{entity}-modals.html` | `tag-modals.html` |
| 模态控制器 | `{entity}-modals.js` | `tag-modals.js` |
| API service | `{entity}_service.js` | `user_service.js` |
| API namespace | `{entity}.py` | `users.py` |

## 正反例

### 正例: 模态提交到 /api/v1

判定点:

- 模态表单在 `templates/**/modals/**`
- JS controller 收集表单, 调用 `httpU.post/put/delete`
- 成功后 toast + 刷新列表(或局部刷新)

### 反例: 表单内查库

```python
# 反例: 在页面路由/模板层直接写 DB 逻辑
def bad_route():
    return Model.query.count()
```

## 门禁/检查方式

- 静态门禁（防止 `app/forms/**` 体系回归）：`./scripts/ci/forms-layer-guard.sh`（目录不存在时自动跳过）
- 评审检查:
  - 是否存在独立 create/edit 表单页?
  - 写操作是否全部走 `/api/v1/**` 且具备 CSRF/权限保护?
- 自查命令(示例):

```bash
rg -n "ResourceFormView|app/forms/|views/form_handlers" app
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/guide/documentation|文档结构与编写规范]] 补齐标准章节.
- 2026-01-23: 移除 `ResourceFormView` 体系, 更新为 Modal CRUD 标准.
