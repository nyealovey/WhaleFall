---
title: 认证与权限(Identity & Access)
aliases:
  - identity-access
tags:
  - architecture
  - security
  - security/identity-access
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: Web UI + API v1 的 authentication/authorization/RBAC, 以及 CSRF/JWT 约束与落点
related:
  - "[[architecture/developer-entrypoint]]"
  - "[[standards/backend/gate/layer/api-layer]]"
  - "[[standards/doc/guide/api-contract-markdown]]"
  - "[[standards/backend/standard/error-message-schema-unification]]"
  - "[[standards/backend/standard/sensitive-data-handling]]"
  - "[[API/auth-api-contract]]"
---

# 认证与权限(Identity & Access)

> [!note] 目标
> 让你在改任何 endpoint/页面前, 先明确: 认证是什么, 权限检查在哪里做, CSRF/JWT 应该怎么接.

## 1. 现状概览

- Web UI(HTML): `flask_login` session cookie + CSRF.
- API v1(JSON): 同样基于 `flask_login` session cookie, 写操作必须带 CSRF.
- JWT: 登录时同时签发 access/refresh token, 当前主要用于 `auth` namespace 的 token 刷新与 `me` 查询, 不是全量替代 session 的鉴权机制.

## 2. 认证(Authentication)

### 2.1 Session cookie(浏览器与 API v1 共享)

- 会话写入: `app/services/auth/login_service.py` 里调用 `login_user(user, remember=True)`.
- Cookie 名称与安全参数: `app/__init__.py` 里的 `configure_security()`.
- 访问控制: 通过 `flask_login.current_user` 判断是否已登录.

### 2.2 JWT(用于 token 刷新与可选的无状态调用)

- 签发: `app/services/auth/login_service.py` 里 `create_access_token`/`create_refresh_token`.
- 受保护资源: `app/api/v1/namespaces/auth.py` 中 `@jwt_required()`/`@jwt_required(refresh=True)` 的 endpoints.
- 注意: 仅携带 `Authorization: Bearer <token>` 并不会让 `current_user` 自动变为已登录(当前实现未做 jwt -> user 的 request loader 绑定).

## 3. CSRF

### 3.1 何时需要 CSRF

- MUST: 所有写操作(POST/PUT/PATCH/DELETE)都必须过 CSRF 校验, 包括 `/actions/*`.
- MAY: GET/HEAD/OPTIONS/TRACE 免 CSRF(见 `SAFE_CSRF_METHODS`).

### 3.2 Token 传递方式

- Header: `X-CSRFToken`(见 `app/core/constants/http_headers.py`).
- 兜底: 表单字段 `csrf_token`(仅 HTML form).
- MUST NOT: 通过 JSON body 传 csrf token(见 [[standards/doc/guide/api-contract-markdown]]).

### 3.3 校验落点

- 统一装饰器: `app/utils/decorators.py:require_csrf`.
- API v1: 在对应 method 上加 `@require_csrf`(常见于 `app/api/v1/namespaces/*.py`).
- Web routes: 对写视图函数加 `require_csrf`, 并保证装饰器顺序正确(见 [[#6.2 装饰器顺序]]).

## 4. 授权(Authorization)与 RBAC

### 4.1 角色与权限模型(当前实现)

- Role: `current_user.role`, 典型值: `admin/user/guest`.
- Admin: 默认拥有全部权限(见 `app/utils/decorators.py:has_permission`).
- 非 admin: 权限集合目前为内置映射(后续如接入 DB/RBAC, 以同名函数为扩展点).

### 4.2 Web routes 的检查入口

- 登录: `app/utils/decorators.py:login_required`.
- 管理员: `app/utils/decorators.py:admin_required`.
- CRUD: `view_required/create_required/update_required/delete_required`(底层走 `permission_required(permission)`).

### 4.3 API v1 的检查入口

- 登录: `app/api/v1/resources/decorators.py:api_login_required`(禁止 redirect/flash, 直接抛 `AuthenticationError`).
- 权限: `app/api/v1/resources/decorators.py:api_permission_required(permission)`.
- Admin: `app/api/v1/resources/decorators.py:api_admin_required`.

> [!warning] UI gating 不是权限
> `app/templates/**` 中的 `if current_user.role == "admin"` 只能作为 UI 控制(隐藏按钮等).
> 服务端仍必须在 route/API 层做真实的权限校验.

## 5. 权限检查落点(推荐)

| 层 | 位置 | 允许做什么 | 禁止做什么 |
| --- | --- | --- | --- |
| Web route | `app/routes/**` + `app/utils/decorators.py` | login/permission/csrf + 参数解析 + 调用 service | 在模板条件里当作唯一防线 |
| API v1 | `app/api/v1/namespaces/**` + `app/api/v1/resources/decorators.py` | login/permission/csrf + schema/封套 + 调用 service | 用 web 的 decorator 导致 redirect |
| Service | `app/services/**` | 业务编排, 失败语义, 事务内 savepoint | 直接决定 "用户有没有权限" 作为唯一校验 |

## 6. 常见坑

### 6.1 JWT 和 current_user 混用

- 现状: 多数 API v1 endpoints 依赖 `current_user`(session).
- 结果: 只带 JWT 访问这些 endpoints 会被当成未登录.

### 6.2 装饰器顺序

- Web routes: 推荐 `@login_required` 在外层, `@<permission>_required` 其次, `@require_csrf` 最内层(最接近业务函数).
- API v1: `api_login_required`/`api_permission_required` 可通过 `method_decorators` 或显式装饰器, `@require_csrf` 贴在具体写方法上.

### 6.3 把权限判断写进模板或前端

- 模板/前端只做体验, 不做安全.
- 所有写操作必须在服务端校验权限 + CSRF.

### 6.4 action endpoint 的失败语义影响事务

- 当你想 "失败也要保留部分写入" 时, 不要抛异常.
- 细节见 [[standards/backend/standard/action-endpoint-failure-semantics]] 与 [[standards/backend/standard/write-operation-boundary]].

## 7. 新增 endpoint 的最小 checklist

- contract: 更新 `docs/Obsidian/API/**-api-contract.md` 的 "Endpoints 总览" 表格(见 [[standards/doc/guide/api-contract-markdown]]).
- auth: 明确是 session 还是 jwt, 并选用对应 decorator.
- permission: 给出 `api_permission_required(...)` 或 web 的 `*_required`, 同步更新 contract 的 Permission 列.
- csrf: 写操作加 `@require_csrf`, token 走 `X-CSRFToken`.
- errors: 对外口径走统一错误封套(见 [[standards/backend/standard/error-message-schema-unification]]).

