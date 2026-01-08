---
title: Databases - API Contract
aliases:
  - databases-api-contract
tags:
  - api/contract
  - databases
  - ledgers
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/databases.py
---

# Databases - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/databases.py`（挂载：`/api/v1/databases`）
>

## Scope

- ✅ Databases Options（实例下数据库选项）
- ✅ Database Ledgers（数据库台账 + 导出）
- ✅ Database Sizes（历史/最新容量聚合）
- ✅ Database Table Sizes（表容量快照 + refresh action）

## 快速导航

- [[#统一封套与分页]]
- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Database Ledgers]]
- [[#Database Sizes]]
- [[#Database Table Sizes]]

## 统一封套与分页

> [!info]
> JSON 封套口径见：[[standards/backend/api-response-envelope|API 响应封套]]。

### Pagination（page/limit）

- 列表分页统一使用 `page` + `limit`（例如 `GET /api/v1/databases/ledgers`）。
- `page`: 最小为 1；非法值回退默认值。
- `limit`: 最小为 1；上限以各 endpoint 为准（例如 ledgers 最大 200、options 最大 1000、tables/sizes 最大 2000）；非法值回退默认值。

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限以代码侧 `api_permission_required(...)` 为准（例如 `view/update/admin`）。
- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`（包含 action endpoints）。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

| Method | Path                                                           | Purpose            | Permission                                        | CSRF | Notes                                                                                                 |
| ------ | -------------------------------------------------------------- | ------------------ | ------------------------------------------------- | ---- | ----------------------------------------------------------------------------------------------------- |
| GET    | `/api/v1/databases/options`                                    | 获取实例下数据库选项         | `view`                                            | -    | query：`instance_id`（必填）；`page/limit`                                                                  |
| GET    | `/api/v1/databases/ledgers`                                    | 数据库台账列表            | `view`                                            | -    | query：`search/db_type/instance_id/tags/page/limit`；响应字段为 `data.limit`                                 |
| GET    | `/api/v1/databases/ledgers/exports`                            | 导出数据库台账（CSV）       | `view`                                            | -    | 成功返回 CSV（非 JSON）；失败仍为 JSON Envelope                                                                   |
| GET    | `/api/v1/databases/sizes`                                      | 实例数据库大小（历史/最新）     | `view`                                            | -    | query：`instance_id`（必填）；`start_date/end_date/database_name/latest_only/include_inactive/page/limit`   |
| GET    | `/api/v1/databases/{database_id}/tables/sizes`                 | 表容量快照              | `view`                                            | -    | query：`schema_name/table_name/page/limit`；`limit` 最大 2000                                              |
| POST   | `/api/v1/databases/{database_id}/tables/sizes/actions/refresh` | 刷新表容量快照（采集 + 返回快照） | `update`                                          | ✅    | query 同上；可能返回 409：`DATABASE_CONNECTION_ERROR`/`SYNC_DATA_ERROR`                                       |

## Database Ledgers

### `GET /api/v1/databases/ledgers`

query（常用）：

- `search`: string（可选，trim）
- `db_type`: string（默认 `all`）
- `instance_id`: int（可选）
- `tags`: string[]（重复 key：`?tags=prod&tags=staging`）
- `page/limit`

> [!note]
> 返回结构为 `data.items/total/page/limit`。

### `GET /api/v1/databases/ledgers/exports`

- query 同 `GET /api/v1/databases/ledgers`
- 成功：返回 `text/csv; charset=utf-8`，并包含 `Content-Disposition: attachment; filename=...`
- `tags` 兼容两种写法：
  - 重复 key：`?tags=prod&tags=staging`
  - 逗号分隔：`?tags=prod,staging`

## Database Sizes

### `GET /api/v1/databases/sizes`

> [!warning]
> `instance_id` 为必填参数。

query：

- `instance_id`: int（必填）
- `start_date/end_date`: `YYYY-MM-DD`（可选）
- `database_name`: string（可选）
- `latest_only`: `true/false`（默认 `false`）
- `include_inactive`: `true/false`（默认 `false`）
- `page/limit`（默认 `1/100`）

## Database Table Sizes

### `GET /api/v1/databases/{database_id}/tables/sizes`

query：

- `schema_name`: string（可选）
- `table_name`: string（可选）
- `page`: int（默认 1）
- `limit`: int（默认 200，最大 2000）

### `POST /api/v1/databases/{database_id}/tables/sizes/actions/refresh`

> [!note]
> 该接口属于 action：会主动连接实例、采集并刷新快照；成功后返回最新快照（同 `GET /tables/sizes`，额外附带 `saved_count/deleted_count/elapsed_ms`）。
