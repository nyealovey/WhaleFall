---
title: Tags - API Contract
aliases:
  - tags-api-contract
tags:
  - api/contract
  - tags
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/tags.py
---

# Tags - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/tags.py`（挂载：`/api/v1/tags`）
>

## Scope

- ✅ Tags：list / CRUD
- ✅ Tag Options：options / categories
- ✅ Batch：batch-delete
- ✅ Bulk：instances / tags / assign / remove / remove-all / instance-tags

## 快速导航

- [[#统一封套与分页]]
- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Tags]]
- [[#Batch & Bulk]]

## 统一封套与分页

> [!info]
> JSON 封套口径见：[[standards/backend/api-response-envelope|API 响应封套]]。

### Pagination（page/limit）

- `GET /api/v1/tags` 使用 `page` + `limit`：
  - `page`: 最小为 1；非法值回退默认值。
  - `limit`: 最小为 1、最大为 200；非法值回退默认值（默认 20）。

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限粒度（`api_permission_required`）：
  - 读：`view`
  - 创建：`create`
  - 更新：`update`
  - 删除：`delete`
- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`（包含 action endpoints）。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

| Method | Path                                   | Purpose     | Permission | CSRF | Notes                                     |
| ------ | -------------------------------------- | ----------- | ---------- | ---- | ----------------------------------------- |
| GET    | `/api/v1/tags`                         | 标签列表        | `view`     | -    | query：`search/category/status/page/limit` |
| POST   | `/api/v1/tags`                         | 创建标签        | `create`   | ✅    | 支持 JSON 或 form；建议 JSON                    |
| GET    | `/api/v1/tags/options`                 | 标签选项        | `view`     | -    | query：`category?`                         |
| GET    | `/api/v1/tags/categories`              | 标签分类列表      | `view`     | -    | -                                         |
| GET    | `/api/v1/tags/{tag_id}`                | 标签详情        | `view`     | -    | -                                         |
| PUT    | `/api/v1/tags/{tag_id}`                | 更新标签        | `update`   | ✅    | 支持 JSON 或 form；建议 JSON                    |
| DELETE | `/api/v1/tags/{tag_id}`                | 删除标签        | `delete`   | ✅    | 若仍被实例使用，返回 409：`TAG_IN_USE`               |
| POST   | `/api/v1/tags/batch-delete`            | 批量删除标签      | `delete`   | ✅    | body：`tag_ids[]`；可能返回 207 Multi-Status    |
| GET    | `/api/v1/tags/bulk/instances`          | 批量操作：可选实例列表 | `view`     | -    | -                                         |
| GET    | `/api/v1/tags/bulk/tags`               | 批量操作：可选标签列表 | `view`     | -    | -                                         |
| POST   | `/api/v1/tags/bulk/actions/assign`     | 批量分配标签      | `create`   | ✅    | body：`instance_ids[]/tag_ids[]`           |
| POST   | `/api/v1/tags/bulk/actions/remove`     | 批量移除标签      | `create`   | ✅    | body：`instance_ids[]/tag_ids[]`           |
| POST   | `/api/v1/tags/bulk/actions/remove-all` | 批量移除所有标签    | `create`   | ✅    | body：`instance_ids[]`                     |
| POST   | `/api/v1/tags/bulk/instance-tags`      | 批量获取实例标签集合  | `view`     | ✅    | body：`instance_ids[]`                     |

## Tags

### `GET /api/v1/tags`

query（常用）：

- `search`: string（可选）
- `category`: string（可选）
- `status`: string（可选；`all`/空 视为不过滤）
- `page/limit`

### `POST /api/v1/tags`

请求体（JSON）：

- `name: string`（必填，标签代码）
- `display_name: string`（必填）
- `category: string`（必填）
- `color: string`（可选）
- `is_active: boolean`（可选）

## Batch & Bulk

### `POST /api/v1/tags/batch-delete`

请求体（JSON）：

- `tag_ids: int[]`（必填）

> [!note]
> 执行结果可能是部分成功：当 `outcome.has_failure == true` 时，HTTP status 为 207（Multi-Status）。

### `POST /api/v1/tags/bulk/actions/assign`

- 批量建立 `Instance <-> Tag` 关系；返回 `assigned_count`。

### `POST /api/v1/tags/bulk/actions/remove-all`

- 从给定 `instance_ids` 中移除所有标签关系；返回 `removed_count`。
