# 004 Flask-RESTX/OpenAPI Phase 3 (Instances Aggregations/Batch/Stats/Health) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将实例聚合(15)、实例批量操作(17)、实例统计(18)、健康检查补齐(19)的既有 `*/api/*` JSON API 迁移到 `/api/v1/**`，并补齐最小 HTTP 契约测试与 OpenAPI 可见性校验。

**Architecture:** 在 `app/api/v1/namespaces/*` 增加对应 Resource，新入口仅做参数解析/鉴权与统一封套输出；业务逻辑复用 `app/services/**` 与 `app/repositories/**`。写操作端点统一加 `require_csrf`。

**Tech Stack:** Flask, Flask-RESTX, pytest, uv

---

## API v1 路径映射

### Module 15: 实例聚合
- 旧：`GET /capacity/api/instances` → 新：`GET /api/v1/capacity/instances`
- 旧：`GET /capacity/api/instances/summary` → 新：`GET /api/v1/capacity/instances/summary`

### Module 17: 实例批量操作
- 旧：`POST /instances/batch/api/create` → 新：`POST /api/v1/instances/batch-create`（multipart CSV）
- 旧：`POST /instances/batch/api/delete` → 新：`POST /api/v1/instances/batch-delete`（JSON body）

### Module 18: 实例统计
- 旧：`GET /instances/api/statistics` → 新：`GET /api/v1/instances/statistics`

### Module 19: 健康检查补齐
- 旧：`GET /health/api/cache` → 新：`GET /api/v1/health/cache`（需登录）
- 旧：`GET /health/api/detailed` → 新：`GET /api/v1/health/detailed`

---

## Tasks (TDD)

### Task 1: Add contract tests (RED)

**Files:**
- Create: `tests/unit/routes/test_api_v1_capacity_instances_contract.py`
- Create: `tests/unit/routes/test_api_v1_instances_batch_contract.py`
- Create: `tests/unit/routes/test_api_v1_instances_statistics_contract.py`
- Create: `tests/unit/routes/test_api_v1_health_extended_contract.py`

**Run:** `uv run pytest -m unit <new-test-files> -v`
**Expected:** FAIL (404 / missing routes)

### Task 2: Implement API v1 endpoints (GREEN)

**Files:**
- Modify: `app/api/v1/namespaces/capacity.py`
- Modify: `app/api/v1/namespaces/instances.py`
- Modify: `app/api/v1/namespaces/health.py`

**Run:** `uv run pytest -m unit <new-test-files> -v`
**Expected:** PASS

### Task 3: Update progress doc

**Files:**
- Modify: `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`

### Task 4: Verify

Run:
- `uv run pytest -m unit`
- `uv run python scripts/dev/openapi/export_openapi.py --check`
- `uv run python scripts/dev/docs/generate_api_routes_inventory.py --check-progress`

