# 004 Flask-RESTX/OpenAPI Phase 5 (Users/Files/Admin) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将用户管理(27)、文件导入导出(28)、主路由 app-info(29) 的既有 `*/api/*` 端点迁移到 `/api/v1/**`，并补齐最小 HTTP 契约测试与 OpenAPI 可见性。

**Architecture:** 在 `app/api/v1/namespaces/*` 增加对应 Resource；新入口仅做参数解析/鉴权与错误封套，业务逻辑复用既有 `app/services/**` 与 `app/repositories/**`；写操作统一加 `require_csrf`；管理员专用接口使用 `api_admin_required` 确保 API v1 不发生 redirect/flash。

**Tech Stack:** Flask, Flask-RESTX, pytest, uv

---

## API v1 路径映射

### Module 27: 用户管理模块
- 旧：`GET /users/api/users` → 新：`GET /api/v1/users`
- 旧：`POST /users/api/users` → 新：`POST /api/v1/users`
- 旧：`GET /users/api/users/<int:user_id>` → 新：`GET /api/v1/users/<int:user_id>`
- 旧：`PUT /users/api/users/<int:user_id>` → 新：`PUT /api/v1/users/<int:user_id>`
- 旧：`DELETE /users/api/users/<int:user_id>` → 新：`DELETE /api/v1/users/<int:user_id>`
- 旧：`GET /users/api/users/stats` → 新：`GET /api/v1/users/stats`

### Module 28: 文件导入导出模块
- 旧：`GET /files/api/account-export` → 新：`GET /api/v1/files/account-export`
- 旧：`GET /files/api/instance-export` → 新：`GET /api/v1/files/instance-export`
- 旧：`GET /files/api/database-ledger-export` → 新：`GET /api/v1/files/database-ledger-export`
- 旧：`GET /files/api/log-export` → 新：`GET /api/v1/files/log-export`
- 旧：`GET /files/api/template-download` → 新：`GET /api/v1/files/template-download`

### Module 29: 主路由模块
- 旧：`GET /admin/api/app-info` → 新：`GET /api/v1/admin/app-info`

---

## Tasks (TDD)

### Task 1: Add contract tests (RED)

**Files:**
- Create: `tests/unit/routes/test_api_v1_users_contract.py`
- Create: `tests/unit/routes/test_api_v1_files_contract.py`
- Create: `tests/unit/routes/test_api_v1_admin_contract.py`

**Run:**
- `uv run pytest -m unit tests/unit/routes/test_api_v1_users_contract.py -v`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_files_contract.py -v`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_admin_contract.py -v`

**Expected:** FAIL (404 / missing routes)

---

### Task 2: Implement API v1 endpoints (GREEN)

**Files:**
- Create: `app/api/v1/namespaces/users.py`
- Create: `app/api/v1/namespaces/files.py`
- Create: `app/api/v1/namespaces/admin.py`
- Modify: `app/api/v1/resources/decorators.py`（新增 `api_admin_required`）
- Modify: `app/api/v1/__init__.py`（add namespaces: `/users`, `/files`, `/admin`）

**Notes:**
- Users 写操作：`POST/PUT/DELETE` 统一加 `require_csrf`。
- Files 为下载类接口：成功响应为文件；错误响应仍必须为 JSON（由 `WhaleFallApi.handle_error` 兜底）。
- Logs export：仅 admin 可访问。

**Run:**
- `uv run pytest -m unit tests/unit/routes/test_api_v1_users_contract.py -v`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_files_contract.py -v`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_admin_contract.py -v`

**Expected:** PASS

---

### Task 3: Update progress doc

**Files:**
- Modify: `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`

**Changes:**
- Module 27/28/29 对应行标记 `DONE`，并在“备注”写新入口（Endpoint 列保持旧路径）。
- Phase 3 Checklist：覆盖清单项标记为完成。

---

### Task 4: Verify

Run:
- `uv run pytest -m unit`
- `uv run python scripts/dev/openapi/export_openapi.py --check`
- `uv run python scripts/dev/docs/generate_api_routes_inventory.py --check-progress`

