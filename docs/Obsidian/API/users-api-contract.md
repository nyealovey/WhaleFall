---
title: Users - API Contract
aliases:
  - users-api-contract
tags:
  - api/contract
  - users
  - admin
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/users.py
---

# Users - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/users.py`（挂载：`/api/v1/users`）
>

## Scope

- ✅ Users：list / CRUD
- ✅ Users Stats

## 快速导航

- [[#统一封套与分页]]
- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]

## 统一封套与分页

> [!info]
> JSON 封套口径见：[[standards/backend/api-response-envelope|API 响应封套]]。

### Pagination（page/limit）

- `GET /api/v1/users` 使用 `page` + `limit`（默认 10，最大 200）。

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限粒度（`api_permission_required`）：`view/create/update/delete`。
- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

| Method | Path | Purpose | Service | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/users` | 用户列表 | `UsersListService.list_users` | `view` | - | query：`search/role/status/sort/order/page/limit`（默认 limit=10） |
| POST | `/api/v1/users` | 创建用户 | `UserWriteService.create` | `create` | ✅ | body：`username/role/password/is_active?` |
| GET | `/api/v1/users/{user_id}` | 用户详情 | `UsersRepository.get_by_id` | `view` | - | - |
| PUT | `/api/v1/users/{user_id}` | 更新用户 | `UserWriteService.update` | `update` | ✅ | body：`username?/role?/password?/is_active?` |
| DELETE | `/api/v1/users/{user_id}` | 删除用户 | `UserWriteService.delete` | `delete` | ✅ | - |
| GET | `/api/v1/users/stats` | 用户统计 | `UsersStatsService.get_stats` | `view` | - | - |
