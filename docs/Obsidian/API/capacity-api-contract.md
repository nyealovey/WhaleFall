---
title: Capacity - API Contract
aliases:
  - capacity-api-contract
tags:
  - api/contract
  - capacity
  - aggregations
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/capacity.py
---

# Capacity - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/capacity.py`（挂载：`/api/v1/capacity`）
>

## Scope

- ✅ Aggregations：current（action）
- ✅ Database Aggregations：list / summary
- ✅ Instance Aggregations：list / summary

## 快速导航

- [[#统一封套与分页]]
- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Database Aggregations]]
- [[#Instance Aggregations]]

## 统一封套与分页

> [!info]
> JSON 封套口径见：[[standards/backend/api-response-envelope|API 响应封套]]。

### Pagination（page/limit）

- `GET /api/v1/capacity/databases`、`GET /api/v1/capacity/instances` 使用 `page` + `limit`：
  - `page`: 最小为 1；非法值回退默认值。
  - `limit`: 最小为 1、最大为 200；非法值回退默认值（默认 20）。
- `get_all=true` 时会尝试返回全量（由 service 实现决定），仍建议在 UI 上优先分页。

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限粒度：
  - 读接口：`view`
  - 聚合触发(action)：`admin`
- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`（包含 action endpoints）。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

| Method | Path                                    | Purpose         | Permission | CSRF | Notes                                                                                                    |
| ------ | --------------------------------------- | --------------- | ---------- | ---- | -------------------------------------------------------------------------------------------------------- |
| POST   | `/api/v1/capacity/aggregations/current` | 触发当前周期聚合（仅聚合今日） | `admin`    | ✅    | body：`period_type?`（当前仅 daily）/`scope?`（instance/database/all）                                           |
| GET    | `/api/v1/capacity/databases`            | 数据库容量聚合列表       | `view`     | -    | query：`instance_id/db_type/database_name/database_id/period_type/start_date/end_date/get_all/page/limit` |
| GET    | `/api/v1/capacity/databases/summary`    | 数据库容量聚合汇总       | `view`     | -    | query 同上（不含分页）                                                                                           |
| GET    | `/api/v1/capacity/instances`            | 实例容量聚合列表        | `view`     | -    | query：`instance_id/db_type/period_type/start_date/end_date/time_range/get_all/page/limit`                |
| GET    | `/api/v1/capacity/instances/summary`    | 实例容量聚合汇总        | `view`     | -    | query 同上（不含分页）                                                                                           |

## Database Aggregations

### `GET /api/v1/capacity/databases`

query（常用）：

- `instance_id: int`（可选）
- `db_type: string`（可选）
- `database_name: string`（可选）
- `database_id: int`（可选）
- `period_type: string`（可选）
- `start_date/end_date: YYYY-MM-DD`（可选）
- `get_all: true/false`（默认 `false`）
- `page/limit`

## Instance Aggregations

### `GET /api/v1/capacity/instances`

query（常用）：

- `instance_id: int`（可选）
- `db_type: string`（可选）
- `period_type: string`（可选）
- `start_date/end_date: YYYY-MM-DD`（可选）
- `time_range: int`（可选；当 `start_date/end_date` 都未提供时生效，表示最近 N 天）
- `get_all: true/false`（默认 `false`）
- `page/limit`
