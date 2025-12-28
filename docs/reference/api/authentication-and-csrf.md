# 认证与 CSRF 使用说明

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2025-12-28
> 更新: 2025-12-28
> 范围: `/api/v1/**` JSON API, Swagger UI, curl, tests
> 关联: `./api-routes-documentation.md`, `../../standards/backend/api-response-envelope.md`, `app/utils/decorators.py`

## 字段/参数表

| 名称 | 位置 | 用途 | 备注 |
| --- | --- | --- | --- |
| Cookie(Session) | request cookies | API v1 的主要登录态载体 | 多数 `/api/v1/**` 端点使用 `flask_login` 登录态校验 |
| CSRF token | `GET /api/v1/auth/csrf-token` 响应体 `data.csrf_token` | 写操作 CSRF 校验 | token 与 cookie session 绑定, 必须复用同一份 cookie |
| `X-CSRFToken` | request header | 写操作提交 CSRF token | 项目默认读取该 header (见 `app/constants/http_headers.py`) |
| `Authorization: Bearer <token>` | request header | JWT 认证 | 仅少数端点使用 JWT 装饰器, 以路由实现为准 |

## 默认值/约束

- 认证: 当前 API v1 以 cookie session 为主, 需先完成登录流程, 再调用受保护资源.
- CSRF: 对写操作 (通常为 `POST/PUT/DELETE`) 默认启用 CSRF 校验, 调用方必须携带 `X-CSRFToken`.
- token 获取: `GET /api/v1/auth/csrf-token` 会返回 token, 同时建立/刷新当前会话 cookie, 后续请求必须复用该 cookie.
- Swagger UI: 浏览器会自动带上同源 cookie, 但不会自动附加 `X-CSRFToken`, 所以写接口在 Swagger UI 中常见 403.

## 示例

### 1) curl: 获取 CSRF token + 登录 + 写操作

```bash
# 1. 获取 token (同时写入 cookie)
CSRF_TOKEN=$(
  curl -s -c cookies.txt http://127.0.0.1:5001/api/v1/auth/csrf-token \
    | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["csrf_token"])'
)

# 2. 登录 (复用 cookie + 提交 token)
curl -s -b cookies.txt -c cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: ${CSRF_TOKEN}" \
  -d '{"username":"alice","password":"***"}' \
  http://127.0.0.1:5001/api/v1/auth/login

# 3. 调用写接口示例 (以 tags create 为例, 仍需 cookie + token)
curl -s -b cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: ${CSRF_TOKEN}" \
  -d '{"name":"prod","display_name":"生产","category":"env"}' \
  http://127.0.0.1:5001/api/v1/tags
```

### 2) curl: JWT 端点示例

```bash
ACCESS_TOKEN="paste_access_token_here"
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" http://127.0.0.1:5001/api/v1/auth/me
```

### 3) Swagger UI 使用提示

1. 先在浏览器中完成登录 (页面路由 `/auth/login`) 或使用上面的 curl 登录并复用同一浏览器会话.
2. 打开 `/api/v1/docs`.
3. 先调用 `GET /api/v1/auth/csrf-token`, 复制 `data.csrf_token`.
4. 调用写接口时, 使用外部工具 (curl/Postman) 携带 `X-CSRFToken`, 或在前端/网关层补齐 header.

## 版本/兼容性说明

- header 名称以 `X-CSRFToken` 为准, 不建议使用变体 (例如 `X-CSRF-Token`).
- 若未来引入 OpenAPI security scheme 或统一 header 参数, 本文档需同步更新并指向新真源入口.

## 常见错误

- 401 Unauthorized: 未登录或登录态失效, 先完成登录流程并确认 cookie 是否复用.
- 403 Forbidden: 常见原因是 CSRF token 缺失/无效, 或权限不足.
- 429 Too Many Requests: 触发限流 (例如登录/敏感操作).
