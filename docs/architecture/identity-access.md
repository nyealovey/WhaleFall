# 认证与授权(Identity & Access)

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-06
> 更新: 2026-01-08
> 范围: API v1 auth/users, session, JWT, CSRF, RBAC
> 关联: ./cross-cutting-capabilities.md; ../standards/backend/api-response-envelope.md; ../standards/backend/error-message-schema-unification.md

## 1. 目标

- 让研发在 5 分钟内回答: API v1 怎么登录, 怎么带认证, 哪些接口需要 CSRF, 权限怎么判定.

## 2. 机制概览

### 2.1 Session vs JWT

- Session(cookie): 大多数 API v1 endpoints 通过 `flask_login.current_user` 判定是否登录, 入口在 `app/api/v1/resources/decorators.py`.
- JWT(Bearer): 目前仅 `GET /api/v1/auth/me` 与 `POST /api/v1/auth/refresh` 使用 `flask_jwt_extended.jwt_required`.

说明: `POST /api/v1/auth/login` 会 `login_user(...)` 写入 session, 同时返回 access/refresh token. API v1 现阶段以 session 校验为主, JWT 端点用于 token 场景.

### 2.2 CSRF

- 写接口通常要求 `@require_csrf` (见 `app/utils/decorators.py`).
- token 来源:
  - Header: `X-CSRFToken`
  - Form: `csrf_token=...`
- 获取 token: `GET /api/v1/auth/csrf-token`.

### 2.3 权限(RBAC)

- API v1 入口装饰器(见 `app/api/v1/resources/decorators.py`):
  - `api_login_required`
  - `api_permission_required(permission)`
  - `api_admin_required`
- 角色到权限映射集中在 `app/utils/decorators.py::has_permission`.

注意: `has_permission` 当前包含占位规则. 现状是 `role == "admin"` 放行所有权限, 非 admin 仅放行少量权限(例如 `view`).

## 3. API 契约: `/api/v1/auth`

| Method | Path | Auth | CSRF | Notes |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/auth/csrf-token` | no | no | 获取 CSRF token. |
| POST | `/api/v1/auth/login` | no | yes | rate limit, 成功后写入 session 并返回 JWT tokens. |
| POST | `/api/v1/auth/logout` | session | yes | 退出当前 session. |
| POST | `/api/v1/auth/change-password` | session | yes | rate limit. |
| POST | `/api/v1/auth/refresh` | JWT refresh | yes | `Authorization: Bearer <refresh_token>`. |
| GET | `/api/v1/auth/me` | JWT access | no | `Authorization: Bearer <access_token>`. |

## 4. API 契约: `/api/v1/users`

| Method | Path | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/users` | `view` | no | list + filters + sort. |
| POST | `/api/v1/users` | `create` | yes | create user, payload contains password. |
| GET | `/api/v1/users/{user_id}` | `view` | no | user detail. |
| PUT | `/api/v1/users/{user_id}` | `update` | yes | update user, password optional. |
| DELETE | `/api/v1/users/{user_id}` | `delete` | yes | delete user. |
| GET | `/api/v1/users/stats` | `view` | no | users stats. |

## 5. 典型调用流程(浏览器/前端)

1. `GET /api/v1/auth/csrf-token` 获取 token.
2. `POST /api/v1/auth/login` 登录, 并在后续请求中携带 session cookie.
3. 读接口: 仅需已登录(session) + 对应 permission.
4. 写接口: 在已登录(session)基础上, 额外携带 `X-CSRFToken`.

## 6. 约束与注意事项

- `api_login_required` / `api_permission_required` 基于 `flask_login.current_user`, 与 JWT 无关.
- 目前 JWT 只用于 `/api/v1/auth/me` 与 `/api/v1/auth/refresh`. 若要让 API v1 全面支持 JWT, 需要引入 JWT -> user identity 的适配层(本阶段未实现).
