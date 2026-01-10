---
title: API v1 调用 cookbook(curl)
aliases:
  - api-v1-cookbook
  - api-v1-curl-cookbook
tags:
  - reference
  - reference/examples
  - api/v1
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: 用可复制的 curl 演示 API v1 的 session cookie + CSRF + JWT 调用方式, 以及分页/筛选/错误封套
related:
  - "[[API/api-v1-api-contract]]"
  - "[[API/auth-api-contract]]"
  - "[[API/accounts-api-contract]]"
  - "[[API/tags-api-contract]]"
  - "[[reference/security/permissions-catalog]]"
  - "[[reference/errors/message-code-catalog]]"
  - "[[standards/backend/layer/api-layer-standards]]"
---

# API v1 调用 cookbook(curl)

> [!info] 适用场景
> - 你需要快速验证 API v1 行为, 或复现某个 `message_code`
> - 你在写/改 API contract, 想用最小命令对齐实现

## 0. 前置条件

- 本地已跑起服务(示例端口 5001): `docs/getting-started/local-dev.md`
- 你已经有一组可用账号(通常是 `admin`)

约定:

- `BASE_URL`: `http://127.0.0.1:5001`
- cookie jar: `./.tmp.whalefall.cookies`

```bash
BASE_URL="${BASE_URL:-http://127.0.0.1:5001}"
COOKIE_JAR="${COOKIE_JAR:-./.tmp.whalefall.cookies}"
```

## 1. 获取 CSRF token + 建立 cookie

> [!note]
> `CSRF token` 必须配合 cookie session 使用. 所以要同时保存 cookie(`-c`)并复用 cookie(`-b`).

```bash
CSRF_TOKEN="$(
  curl -sS -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
    "$BASE_URL/api/v1/auth/csrf-token" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["csrf_token"])'
)"
echo "CSRF_TOKEN=$CSRF_TOKEN"
```

## 2. 登录(session cookie)并获取 JWT

```bash
USERNAME="admin"
PASSWORD="<replace_me>"

LOGIN_RES="$(
  curl -sS -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: $CSRF_TOKEN" \
    -X POST "$BASE_URL/api/v1/auth/login" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}"
)"
echo "$LOGIN_RES" | python -m json.tool
```

提取 token:

```bash
ACCESS_TOKEN="$(echo "$LOGIN_RES" | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["access_token"])')"
REFRESH_TOKEN="$(echo "$LOGIN_RES" | python -c 'import json,sys; print(json.load(sys.stdin)["data"]["refresh_token"])')"
```

## 3. 走 session cookie 的 API 调用示例

> [!note]
> 大多数 `/api/v1/**` 接口使用 `flask-login` 的 session cookie 做鉴权(`api_login_required`).

### 3.1 列表 + 分页

```bash
curl -sS -b "$COOKIE_JAR" \
  "$BASE_URL/api/v1/accounts/ledgers?page=1&limit=20" \
| python -m json.tool
```

### 3.2 筛选 + 排序

参数口径以 contract 为准: `docs/Obsidian/API/accounts-api-contract.md`.

```bash
curl -sS -b "$COOKIE_JAR" \
  "$BASE_URL/api/v1/accounts/ledgers?page=1&limit=20&search=alice&sort=username&order=asc" \
| python -m json.tool
```

重复 key 的数组参数示例(tags):

```bash
curl -sS -b "$COOKIE_JAR" \
  "$BASE_URL/api/v1/accounts/ledgers?page=1&limit=20&tags=prod&tags=staging" \
| python -m json.tool
```

## 4. 写接口示例(CSRF + cookie)

> [!warning]
> 所有 `POST/PUT/PATCH/DELETE` 默认都需要 `X-CSRFToken`(除非代码明确豁免).
> 统一口径见: `docs/Obsidian/API/auth-api-contract.md`.

### 4.1 创建一个 tag

参数口径以 contract 为准: `docs/Obsidian/API/tags-api-contract.md`.

```bash
TAG_CODE="demo_$(date +%s)"

curl -sS -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -X POST "$BASE_URL/api/v1/tags" \
  -d "$(printf '{"name":"%s","display_name":"%s","category":"demo","is_active":true}' "$TAG_CODE" "$TAG_CODE")" \
| python -m json.tool
```

### 4.2 故意触发一个错误封套(CSRF_MISSING)

```bash
curl -sS -b "$COOKIE_JAR" \
  -H "Content-Type: application/json" \
  -X POST "$BASE_URL/api/v1/tags" \
  -d '{"name":"csrf_missing_demo","display_name":"csrf_missing_demo","category":"demo"}' \
| python -m json.tool
```

你应看到类似字段:

- `error_id`
- `message_code`(例如 `CSRF_MISSING`)
- `category`, `severity`
- `recoverable`, `suggestions`
- `context.request_id`, `context.user_id`

错误码含义表见: [[reference/errors/message-code-catalog]].

## 5. 走 JWT 的 API 调用示例

> [!note]
> 当前 JWT 主要用于 `auth` 域的 `me/refresh`.

### 5.1 `GET /api/v1/auth/me`

```bash
curl -sS \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$BASE_URL/api/v1/auth/me" \
| python -m json.tool
```

### 5.2 `POST /api/v1/auth/refresh`(refresh token + CSRF)

```bash
curl -sS -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -H "Authorization: Bearer $REFRESH_TOKEN" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -X POST "$BASE_URL/api/v1/auth/refresh" \
| python -m json.tool
```

## 6. 常见坑

- 只带 `X-CSRFToken`, 不带 cookie jar: 会触发 `CSRF_INVALID` 或被视为未登录.
- 只带 cookie, 不带 `X-CSRFToken`: 写接口会触发 `CSRF_MISSING`.
- 看到 `PERMISSION_REQUIRED`: 先核对 API contract 的 `Permission` 列, 再核对当前用户角色与权限映射.
  - 参考: [[reference/security/permissions-catalog]]
