---
title: Credentials - API Contract
aliases:
  - credentials-api-contract
tags:
  - api/contract
  - credentials
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/credentials.py
---

# Credentials - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/credentials.py`（挂载：`/api/v1/credentials`）
>

## Scope

- ✅ Credentials：list / CRUD

## 快速导航

- [[#统一封套与分页]]
- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Credentials]]

## 统一封套与分页

> [!info]
> JSON 封套口径见：[[standards/backend/api-response-envelope|API 响应封套]]。

### Pagination（page/limit）

- `GET /api/v1/credentials` 使用 `page` + `limit`：
  - `page`: 最小为 1；非法值回退默认值。
  - `limit`: 最小为 1、最大为 200；非法值回退默认值（默认 20）。

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限粒度（`api_permission_required`）：`view/create/update/delete`。
- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

| Method | Path | Purpose | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/credentials` | 凭据列表 | `view` | - | query：`search/credential_type/db_type/status/tags/sort/order/page/limit`；`credential_type/db_type=all` 视为不过滤 |
| POST | `/api/v1/credentials` | 创建凭据 | `create` | ✅ | body：`name/credential_type/db_type?/username/password/description?/is_active?` |
| GET | `/api/v1/credentials/{credential_id}` | 凭据详情 | `view` | - | - |
| PUT | `/api/v1/credentials/{credential_id}` | 更新凭据 | `update` | ✅ | body：`password` 可选；其余字段必填（以 payload model 为准） |
| DELETE | `/api/v1/credentials/{credential_id}` | 删除凭据 | `delete` | ✅ | - |

## Credentials

### `GET /api/v1/credentials`

query（常用）：

- `search`: string（可选）
- `credential_type`: string（可选；`all`/空 视为不过滤）
- `db_type`: string（可选；`all`/空 视为不过滤）
- `status`: `active/inactive`（可选；其它值视为不过滤）
- `tags`: string[]（重复 key：`?tags=prod&tags=mysql`）
- `sort`: string（默认 `created_at`）
- `order`: `asc/desc`（默认 `desc`）
- `page/limit`

