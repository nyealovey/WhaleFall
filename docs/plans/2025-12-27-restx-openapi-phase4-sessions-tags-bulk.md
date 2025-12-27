# 004 Flask-RESTX/OpenAPI Phase 4C (History Sessions/Tags Bulk) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将同步会话(24)、标签批量操作(26) 的既有 `*/api/*` JSON API 迁移到 `/api/v1/**`，并补齐最小 HTTP 契约测试与 OpenAPI 可见性校验。

**Architecture:** 在 `app/api/v1/namespaces/*` 增加对应 Resource，新入口仅做参数解析/鉴权与统一封套输出；业务逻辑复用既有 services/repositories；写操作端点统一加 `require_csrf`。

**Tech Stack:** Flask, Flask-RESTX, pytest, uv

---

## API v1 路径映射

### Module 24: 同步会话模块
- 旧：`GET /history/sessions/api/sessions` → 新：`GET /api/v1/history/sessions`
- 旧：`GET /history/sessions/api/sessions/<session_id>` → 新：`GET /api/v1/history/sessions/<session_id>`
- 旧：`POST /history/sessions/api/sessions/<session_id>/cancel` → 新：`POST /api/v1/history/sessions/<session_id>/cancel`
- 旧：`GET /history/sessions/api/sessions/<session_id>/error-logs` → 新：`GET /api/v1/history/sessions/<session_id>/error-logs`

### Module 26: 标签批量操作模块
- 旧：`POST /tags/bulk/api/assign` → 新：`POST /api/v1/tags/bulk/assign`
- 旧：`POST /tags/bulk/api/instance-tags` → 新：`POST /api/v1/tags/bulk/instance-tags`
- 旧：`GET /tags/bulk/api/instances` → 新：`GET /api/v1/tags/bulk/instances`
- 旧：`POST /tags/bulk/api/remove` → 新：`POST /api/v1/tags/bulk/remove`
- 旧：`POST /tags/bulk/api/remove-all` → 新：`POST /api/v1/tags/bulk/remove-all`
- 旧：`GET /tags/bulk/api/tags` → 新：`GET /api/v1/tags/bulk/tags`

---

## Tasks (TDD)

### Task 1: Add contract tests (RED)

**Files:**
- Create: `tests/unit/routes/test_api_v1_history_sessions_contract.py`
- Create: `tests/unit/routes/test_api_v1_tags_bulk_contract.py`

**Run:**
- `uv run pytest -m unit tests/unit/routes/test_api_v1_history_sessions_contract.py -v`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_tags_bulk_contract.py -v`

**Expected:** FAIL (404 / missing routes)

---

### Task 2: Implement API v1 endpoints (GREEN)

**Files:**
- Create: `app/api/v1/namespaces/history_sessions.py`
- Create: `app/api/v1/namespaces/tags_bulk.py`
- Modify: `app/api/v1/__init__.py`（add namespaces: `/history/sessions`, `/tags/bulk`）

**Notes:**
- 同步会话：全部为只读/操作接口，权限统一 `api_permission_required("view")`；cancel 为写操作需 `require_csrf`。
- 标签批量：list endpoints 用 `view`；写 endpoints 用 `create`；所有 POST 写接口加 `require_csrf`。
- OpenAPI：避免 `fields.Nested(<dict>)`，必要时用 `fields.Raw` 简化。

**Run:**
- `uv run pytest -m unit tests/unit/routes/test_api_v1_history_sessions_contract.py -v`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_tags_bulk_contract.py -v`

**Expected:** PASS

---

### Task 3: Update progress doc

**Files:**
- Modify: `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`

---

### Task 4: Verify

Run:
- `uv run pytest -m unit`
- `uv run python scripts/dev/openapi/export_openapi.py --check`
- `uv run python scripts/dev/docs/generate_api_routes_inventory.py --check-progress`

