---
title: Sync Sessions - API Contract
aliases:
  - sessions-api-contract
tags:
  - api/contract
  - sessions
  - sync
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/sessions.py
---

# Sync Sessions - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/sessions.py`（挂载：`/api/v1/sync-sessions`）
>

## Scope

- ✅ Sessions：list / detail / error-logs
- ✅ Session Actions：cancel

## 快速导航

- [[#统一封套与分页]]
- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Sessions]]

## 统一封套与分页

> [!info]
> JSON 封套口径见：[[standards/backend/api-response-envelope|API 响应封套]]。

### Pagination（page/limit）

- `GET /api/v1/sync-sessions` 使用 `page` + `limit`（默认 20，最大 100）。

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限粒度（`api_permission_required`）：
  - 读：`view`
  - 管理：`admin`（cancel action）
- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`（包含 action endpoints）。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

| Method | Path                                                | Purpose | Permission | CSRF | Notes                                                        |
| ------ | --------------------------------------------------- | ------- | ---------- | ---- | ------------------------------------------------------------ |
| GET    | `/api/v1/sync-sessions`                             | 同步会话列表  | `view`     | -    | query：`sync_type/sync_category/status/sort/order/page/limit` |
| GET    | `/api/v1/sync-sessions/{session_id}`                | 同步会话详情  | `view`     | -    | -                                                            |
| GET    | `/api/v1/sync-sessions/{session_id}/error-logs`     | 会话错误日志  | `view`     | -    | -                                                            |
| POST   | `/api/v1/sync-sessions/{session_id}/actions/cancel` | 取消会话    | `admin`    | ✅    | action：会话不存在或已结束会返回 404                                      |

## Sessions

### `GET /api/v1/sync-sessions`

query（常用）：

- `sync_type`: string（可选）
- `sync_category`: string（可选）
- `status`: string（可选）
- `sort`: string（默认 `started_at`）
- `order`: `asc/desc`（默认 `desc`；其它值回退 `desc`）
- `page/limit`（`limit` 最大 100）
