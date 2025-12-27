# 004 Flask-RESTX/OpenAPI Phase 4A (Cache/Logs) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将缓存管理(20)、日志中心 API(21) 的既有 `*/api/*` JSON API 迁移到 `/api/v1/**`，并补齐最小 HTTP 契约测试与 OpenAPI 可见性校验。

**Architecture:** 在 `app/api/v1/namespaces/*` 增加对应 Resource，新入口仅做参数解析/鉴权与统一封套输出；业务逻辑复用既有 `app/services/**` 与 `app/repositories/**`；写操作端点统一加 `require_csrf`。

**Tech Stack:** Flask, Flask-RESTX, pytest, uv

---

## API v1 路径映射

### Module 20: 缓存管理模块
- 旧：`GET /cache/api/stats` → 新：`GET /api/v1/cache/stats`
- 旧：`POST /cache/api/clear/user` → 新：`POST /api/v1/cache/clear/user`
- 旧：`POST /cache/api/clear/instance` → 新：`POST /api/v1/cache/clear/instance`
- 旧：`POST /cache/api/clear/all` → 新：`POST /api/v1/cache/clear/all`
- 旧：`POST /cache/api/classification/clear` → 新：`POST /api/v1/cache/classification/clear`
- 旧：`POST /cache/api/classification/clear/<db_type>` → 新：`POST /api/v1/cache/classification/clear/<db_type>`
- 旧：`GET /cache/api/classification/stats` → 新：`GET /api/v1/cache/classification/stats`

### Module 21: 日志模块
- 旧：`GET /history/logs/api/list` → 新：`GET /api/v1/history/logs/list`
- 旧：`GET /history/logs/api/detail/<int:log_id>` → 新：`GET /api/v1/history/logs/detail/<int:log_id>`
- 旧：`GET /history/logs/api/modules` → 新：`GET /api/v1/history/logs/modules`
- 旧：`GET /history/logs/api/search` → 新：`GET /api/v1/history/logs/search`
- 旧：`GET /history/logs/api/statistics` → 新：`GET /api/v1/history/logs/statistics`

---

## Tasks (TDD)

### Task 1: Add contract tests (RED)

**Files:**
- Create: `tests/unit/routes/test_api_v1_cache_contract.py`
- Create: `tests/unit/routes/test_api_v1_history_logs_contract.py`

**Run:**
- `uv run pytest -m unit tests/unit/routes/test_api_v1_cache_contract.py -v`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_history_logs_contract.py -v`

**Expected:** FAIL (404 / missing routes)

---

### Task 2: Implement API v1 endpoints (GREEN)

**Files:**
- Create: `app/api/v1/namespaces/cache.py`
- Create: `app/api/v1/namespaces/history_logs.py`
- Modify: `app/api/v1/__init__.py`（add namespaces: `/cache`, `/history/logs`）

**Notes:**
- 鉴权：全部接口至少 `api_login_required`；日志接口按旧实现为 admin-only，可用 `api_permission_required("admin")`。
- 写操作：`POST` 统一 `require_csrf`。
- OpenAPI：避免 `fields.Nested(<dict>)`，先用 `ns.model(...)` 再 `fields.Nested(Model)`。

**Run:**
- `uv run pytest -m unit tests/unit/routes/test_api_v1_cache_contract.py -v`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_history_logs_contract.py -v`

**Expected:** PASS

---

### Task 3: Update progress doc

**Files:**
- Modify: `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`

**Changes:**
- Module 20/21 对应行标记 `DONE`，并在“备注”写新入口（保留 Endpoint 列为旧路径）。

---

### Task 4: Verify

Run:
- `uv run pytest -m unit`
- `uv run python scripts/dev/openapi/export_openapi.py --check`
- `uv run python scripts/dev/docs/generate_api_routes_inventory.py --check-progress`

