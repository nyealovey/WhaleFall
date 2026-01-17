# services/tags + routes/tags + templates/tags

## Core Purpose

- 提供标签管理页面（列表/筛选/统计）与批量分配入口（routes + templates）。
- 提供标签相关的读写服务（detail/list/options/write/bulk actions），供 API 与页面逻辑复用。

## Unnecessary Complexity Found

- 资源表单体系（看起来已被“前端模态 + API”替代，但仍残留）：
  - `app/views/tag_forms.py:1`：`TagFormView` 未被任何路由注册引用。
  - `app/views/form_handlers/tag_form_handler.py:1`：仅被 `TagFormView` 引用。
  - `app/forms/definitions/tag.py:5`：定义 `TAG_FORM_DEFINITION`，但模板 `tags/form.html` 在仓库中不存在。
  - `app/forms/definitions/__init__.py:10`：仍包含 `TAG_FORM_DEFINITION` 的 lazy import 映射与导出。
  - 这组代码会误导后续维护者（“标签表单仍存在/可用”），且属于死代码。

## Code to Remove

- `app/views/tag_forms.py:1`：删除未接入路由的 Tag 表单视图（可删 LOC 估算：~57）。
- `app/views/form_handlers/tag_form_handler.py:1`：删除仅服务于 Tag 表单视图的 handler（可删 LOC 估算：~63）。
- `app/forms/definitions/tag.py:1`：删除指向缺失模板的 Tag 表单定义（可删 LOC 估算：~41）。
- `app/forms/definitions/__init__.py:10`：移除 `TAG_FORM_DEFINITION` 的 lazy mapping / export / TYPE_CHECKING import（可删 LOC 估算：~3-6）。

## Simplification Recommendations

1. 移除未接入路由的“表单 View/Handler/Definition”
   - Current: 仓库中同时存在“前端模态 + API”与“ResourceFormView 表单体系”的残留代码。
   - Proposed: 删除未被路由使用且模板缺失的表单代码，保留当前实际在用的 routes/templates/API 路径。
   - Impact: 降低误导与维护成本，减少无效文件与导入链。

## YAGNI Violations

- `app/views/tag_forms.py:19` + `app/forms/definitions/tag.py:5`: 在当前 UI 已通过模态实现的情况下，继续保留“独立表单页面”的体系属于 YAGNI。

## Final Assessment

- 可删 LOC 估算：~164
- Complexity: Medium -> Low
- Recommended action: Proceed（删除死代码，不改对外接口）。

