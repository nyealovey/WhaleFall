# services/tags + routes/tags + templates/tags

## Status

- 2026-01-23: 已完成 - 已移除旧表单体系(ResourceFormView)残留, 标签管理仅保留 "页面 + 模态 + /api/v1" 路径.

## Core Purpose

- 提供标签管理页面（列表/筛选/统计）与批量分配入口（routes + templates）。
- 提供标签相关的读写服务（detail/list/options/write/bulk actions），供 API 与页面逻辑复用。

## Notes

- 该模块当前以 API + 模态为准, 若后续需要新增字段或交互, 优先在 `/api/v1/tags` 与 `templates/tags/modals` 中演进, 避免重新引入独立表单页.
