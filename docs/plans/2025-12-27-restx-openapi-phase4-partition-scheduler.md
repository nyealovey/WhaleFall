# 004 Flask-RESTX/OpenAPI Phase 4B (Partition/Scheduler) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将分区管理(22)、定时任务管理(23) 的既有 `*/api/*` JSON API 迁移到 `/api/v1/**`，并补齐最小 HTTP 契约测试与 OpenAPI 可见性校验。

**Architecture:** 在 `app/api/v1/namespaces/*` 增加对应 Resource，新入口仅做参数解析/鉴权与统一封套输出；业务逻辑复用 `app/services/**`；写操作端点统一加 `require_csrf`。

**Tech Stack:** Flask, Flask-RESTX, pytest, uv

---

## API v1 路径映射

### Module 22: 分区管理模块
- 旧：`GET /partition/api/info` → 新：`GET /api/v1/partition/info`
- 旧：`GET /partition/api/status` → 新：`GET /api/v1/partition/status`
- 旧：`GET /partition/api/partitions` → 新：`GET /api/v1/partition/partitions`
- 旧：`POST /partition/api/create` → 新：`POST /api/v1/partition/create`
- 旧：`POST /partition/api/cleanup` → 新：`POST /api/v1/partition/cleanup`
- 旧：`GET /partition/api/statistics` → 新：`GET /api/v1/partition/statistics`
- 旧：`GET /partition/api/aggregations/core-metrics` → 新：`GET /api/v1/partition/aggregations/core-metrics`

### Module 23: 定时任务模块
- 旧：`GET /scheduler/api/jobs` → 新：`GET /api/v1/scheduler/jobs`
- 旧：`GET /scheduler/api/jobs/<job_id>` → 新：`GET /api/v1/scheduler/jobs/<job_id>`
- 旧：`PUT /scheduler/api/jobs/<job_id>` → 新：`PUT /api/v1/scheduler/jobs/<job_id>`
- 旧：`POST /scheduler/api/jobs/<job_id>/pause` → 新：`POST /api/v1/scheduler/jobs/<job_id>/pause`
- 旧：`POST /scheduler/api/jobs/<job_id>/resume` → 新：`POST /api/v1/scheduler/jobs/<job_id>/resume`
- 旧：`POST /scheduler/api/jobs/<job_id>/run` → 新：`POST /api/v1/scheduler/jobs/<job_id>/run`
- 旧：`POST /scheduler/api/jobs/reload` → 新：`POST /api/v1/scheduler/jobs/reload`

---

## Tasks (TDD)

### Task 1: Add contract tests (RED)

**Files:**
- Create: `tests/unit/routes/test_api_v1_partition_contract.py`
- Create: `tests/unit/routes/test_api_v1_scheduler_contract.py`

**Run:**
- `uv run pytest -m unit tests/unit/routes/test_api_v1_partition_contract.py -v`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_scheduler_contract.py -v`

**Expected:** FAIL (404 / missing routes)

---

### Task 2: Implement API v1 endpoints (GREEN)

**Files:**
- Create: `app/api/v1/namespaces/partition.py`
- Create: `app/api/v1/namespaces/scheduler.py`
- Modify: `app/api/v1/__init__.py`（add namespaces: `/partition`, `/scheduler`）

**Notes:**
- 分区：读接口 `api_permission_required("view")`；写接口（create/cleanup）用 `api_permission_required("admin")` + `require_csrf`。
- 定时任务：旧实现区分 `scheduler_view_required`/`scheduler_manage_required`，v1 统一用权限字符串：`scheduler.view` / `scheduler.manage`（`has_permission` 已支持这类权限）。
- 定时任务 PUT：复用 `SchedulerJobWriteService`（JSON body），不依赖旧的 `SchedulerJobFormView`。
- OpenAPI：避免 `fields.Nested(<dict>)`。

**Run:**
- `uv run pytest -m unit tests/unit/routes/test_api_v1_partition_contract.py -v`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_scheduler_contract.py -v`

**Expected:** PASS

---

### Task 3: Update progress doc

**Files:**
- Modify: `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`

**Changes:**
- Module 22/23 对应行标记 `DONE`，并在“备注”写新入口（保留 Endpoint 列为旧路径）。

---

### Task 4: Verify

Run:
- `uv run pytest -m unit`
- `uv run python scripts/dev/openapi/export_openapi.py --check`
- `uv run python scripts/dev/docs/generate_api_routes_inventory.py --check-progress`

