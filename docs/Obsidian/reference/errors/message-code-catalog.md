---
title: message_code/message_key catalog
aliases:
  - message-code-catalog
  - message-key-catalog
tags:
  - reference
  - reference/errors
  - api/envelope
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: API v1 错误封套 message_code(message_key) 一览, 含对外语义与常见触发点
related:
  - "[[standards/backend/gate/layer/api-layer]]"
  - "[[standards/backend/standard/error-message-schema-unification]]"
  - "[[operations/observability-ops]]"
---

# message_code/message_key catalog

> [!info] 结论
> 当前实现中, error envelope 的 `message_code` 等于 `message_key`.

## 1. 背景与落点

- 标准封套格式见: [[standards/backend/gate/layer/api-layer#响应封套(JSON Envelope)|API 响应封套]].
- 统一口径见: [[standards/backend/standard/error-message-schema-unification]].

代码落点:

- 组装错误元信息: `app/utils/logging/error_adapter.py` -> `derive_error_metadata(...)`
- 输出封套: `app/utils/response_utils.py` -> `unified_error_response(...)`
- 将 `message_key` 映射为 `message_code`: `app/utils/structlog_config.py`

## 2. 使用方式(排障与 review)

当你拿到 `message_code`:

1. 在代码里定位触发点:
   - `rg -n 'message_key=\"MESSAGE_CODE\"' app`
2. 结合请求路径与模块字段定位入口:
   - `context.url`, `context.method`, `context.request_id`, `context.user_id`
3. 判断是"业务失败"还是"异常":
   - action endpoints 语义见: [[standards/backend/standard/action-endpoint-failure-semantics]]
4. 按需进入更细的 SOP:
   - [[getting-started/debugging]]

## 3. Catalog

> [!note] 说明
> - "典型 HTTP" 为常见状态码, 不是强约束; 以实际抛出点为准.
> - "触发点" 给出常见入口, 具体以 `rg` 结果与调用链为准.

### 3.1 通用类(generic)

| message_code | 对外语义 | 典型 HTTP | 常见触发点(示例) |
| --- | --- | --- | --- |
| `INVALID_REQUEST` | 请求不合法或无法处理 | 400 | 非 AppError 的 4xx HTTPException, 或 `BaseResource.error_message(..., message_key="INVALID_REQUEST")` |
| `VALIDATION_ERROR` | 入参校验失败 | 400 | `ValidationError`, schema 校验(`app/schemas/**`) |
| `RESOURCE_NOT_FOUND` | 资源不存在 | 404 | `NotFoundError` |
| `CONSTRAINT_VIOLATION` | 冲突/约束违反 | 409 | `ConflictError` 默认值(若未指定更细粒度 message_key) |
| `PERMISSION_DENIED` | 无权限(泛化) | 403 | `AuthorizationError` 默认值, 或文本推导("forbidden/denied") |
| `PERMISSION_REQUIRED` | 缺少指定动作权限 | 403 | `api_permission_required(...)` / `permission_required(...)` |
| `AUTHENTICATION_REQUIRED` | 需要登录 | 401 | `api_login_required` / `login_required` |
| `TASK_EXECUTION_FAILED` | 任务执行失败(泛化) | 500 | `ExternalServiceError` 默认值或任务包装 |
| `DATABASE_QUERY_ERROR` | 数据库查询/事务失败 | 500 | `DatabaseError` 默认值 |
| `DATABASE_TIMEOUT` | 数据库超时/连接类失败(推导) | 504 | 异常文本包含 "timeout/connection" 且未被显式包装 |
| `INTERNAL_ERROR` | 未分类系统错误 | 500 | 未捕获异常, 或 5xx HTTPException |

### 3.2 Auth, CSRF, rate limit

| message_code | 对外语义 | 典型 HTTP | 常见触发点(示例) |
| --- | --- | --- | --- |
| `CSRF_MISSING` | 缺少 CSRF token | 403 | `require_csrf`(`app/utils/decorators.py`) |
| `CSRF_INVALID` | CSRF token 无效 | 403 | `require_csrf`(`app/utils/decorators.py`) |
| `ADMIN_PERMISSION_REQUIRED` | 需要管理员权限 | 403 | Web `admin_required`, API `api_admin_required`(目前少用) |
| `INVALID_CREDENTIALS` | 用户名/密码错误或 JWT identity 无效 | 401 | `LoginService`, `AuthMeReadService` |
| `ACCOUNT_DISABLED` | 账户被禁用 | 403 | `LoginService` |
| `RATE_LIMIT_EXCEEDED` | 触发限流 | 429 | `login_rate_limit`, `password_reset_rate_limit` |
| `INVALID_OLD_PASSWORD` | 旧密码错误 | 401 | `ChangePasswordService` |
| `PASSWORD_INVALID` | 新密码不满足要求 | 400 | `ChangePasswordService`, `app/schemas/auth.py` |
| `PASSWORD_MISMATCH` | 两次密码不一致 | 400 | `app/schemas/auth.py` |
| `PASSWORD_DUPLICATED` | 新密码与旧密码相同 | 400 | `app/schemas/auth.py` |

### 3.3 Users, write guards, naming conflicts

| message_code | 对外语义 | 典型 HTTP | 常见触发点(示例) |
| --- | --- | --- | --- |
| `USERNAME_EXISTS` | 用户名已存在 | 409 | `UserWriteService._ensure_username_unique` |
| `LAST_ADMIN_REQUIRED` | 系统至少需要 1 位活跃管理员 | 400 | `UserWriteService._ensure_last_admin` |
| `NAME_EXISTS` | 名称重复 | 400 | 分类/规则写入(`AccountClassificationsWriteService`) |
| `EXPRESSION_DUPLICATED` | 规则表达式重复 | 400 | `AccountClassificationsWriteService` |
| `DSL_V4_REQUIRED` | 仅支持 DSL v4 | 400 | 分类规则表达式校验 |
| `INVALID_DSL_EXPRESSION` | DSL 表达式非法 | 400 | 分类规则表达式校验 |
| `FORBIDDEN` | 业务侧禁止的操作(非权限) | 400/403 | scheduler job 触发器: 仅允许内置任务 |

### 3.4 Tags, classifications, sync/capacity

| message_code | 对外语义 | 典型 HTTP | 常见触发点(示例) |
| --- | --- | --- | --- |
| `TAG_IN_USE` | tag 仍被引用, 禁止删除 | 409 | `app/api/v1/namespaces/tags.py` |
| `CLASSIFICATION_IN_USE` | classification 被使用, 禁止删除 | 409 | `app/api/v1/namespaces/accounts_classifications.py` |
| `SYSTEM_CLASSIFICATION` | 系统 classification 不可删除 | 400 | `app/api/v1/namespaces/accounts_classifications.py` |
| `REQUEST_DATA_EMPTY` | 请求体为空或不是 object | 400 | tags bulk actions 等写接口 |
| `SNAPSHOT_MISSING` | 权限快照缺失(v4) | 409 | `app/services/accounts_permissions/snapshot_view.py` |
| `PERMISSION_FACTS_MISSING` | 权限事实缺失 | 409 | `app/services/account_classification/orchestrator.py` |
| `SYNC_DATA_ERROR` | 同步数据异常/缺失 | 409 | accounts sync, capacity sync, database sync 等编排 |
| `DATABASE_CONNECTION_ERROR` | 外部实例连接失败 | 409 | instance connection test, capacity sync action |

## 4. 变更历史

- 2026-01-10: 新增 message_code/message_key catalog, 作为排障与 review 的稳定对齐表.
