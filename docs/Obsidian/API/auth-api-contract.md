---
title: Auth - API Contract
aliases:
  - auth-api-contract
tags:
  - api/contract
  - auth
  - csrf
  - jwt
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/auth.py
---

# Auth - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/auth.py`（挂载：`/api/v1/auth`）
>

## Scope

- ✅ CSRF Token：获取 token
- ✅ Session Login/Logout：登录/登出（cookie session）
- ✅ Password：修改密码
- ✅ JWT：refresh / me

## 快速导航

- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Login 流程（推荐）]]

## 鉴权、权限、CSRF

### 鉴权方式

- Session（cookie）：`POST /api/v1/auth/login` 会建立/刷新 session；`POST /api/v1/auth/logout`、`POST /api/v1/auth/change-password` 依赖该 session。
- JWT：`GET /api/v1/auth/me` 与 `POST /api/v1/auth/refresh` 使用 `Authorization: Bearer <token>`（由 `jwt_required` 装饰器控制）。

### CSRF（仅 Header）

- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`（包含动作型校验接口）。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

> [!note]
> `GET /api/v1/auth/csrf-token` 会返回 `data.csrf_token`，用于后续写操作（例如登录/登出/修改密码）。

## Endpoints 总览

| Method | Path | Purpose | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/auth/csrf-token` | 获取 CSRF token | - | - | 返回 `data.csrf_token` |
| POST | `/api/v1/auth/login` | 登录（建立 session + 返回 JWT） | - | ✅ | 需要 CSRF；body：`username/password`；受 rate limit 保护 |
| POST | `/api/v1/auth/logout` | 登出（清理 session） | - | ✅ | 需要登录（session）+ CSRF |
| POST | `/api/v1/auth/change-password` | 修改密码 | - | ✅ | 需要登录（session）+ CSRF；受 rate limit 保护 |
| POST | `/api/v1/auth/refresh` | 刷新 access token | - | ✅ | 需要 refresh JWT + CSRF |
| GET | `/api/v1/auth/me` | 获取当前用户信息 | - | - | 需要 access JWT |

## Login 流程（推荐）

> [!example]
> 1) `GET /api/v1/auth/csrf-token` 获取 `csrf_token`（并建立/刷新 cookie）  
> 2) `POST /api/v1/auth/login` 携带 `X-CSRFToken` + cookie，完成登录  
> 3) 后续调用：
> - 走 session 的接口：继续复用 cookie（写操作仍需 `X-CSRFToken`）
> - 走 JWT 的接口：使用 `Authorization: Bearer <access_token>`  

