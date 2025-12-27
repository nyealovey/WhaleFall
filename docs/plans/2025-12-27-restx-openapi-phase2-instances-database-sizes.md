# 004 Flask-RESTX/OpenAPI Phase 2 (Instances Database Sizes Read) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Instances 域的数据库容量（大小）只读 API 迁移到 RestX API v1（`/api/v1/instances/<id>/databases/sizes`），保持既有 JSON envelope 与错误口径。

**Architecture:** 在 `app/api/v1/namespaces/instances.py` 新增子资源路由，复用 `InstanceDatabaseSizesService`；实例存在性复用 `InstanceDetailReadService().get_active_instance()`；统一通过 `BaseResource.safe_call()` 输出封套；鉴权/权限使用 `api_login_required + api_permission_required("view")`（JSON-only）。

**Tech Stack:** Flask, Flask-RESTX, pytest

---

## API v1 路径映射（Instances Database Sizes Read）

- 旧：GET /instances/api/databases/<int:instance_id>/sizes
  - 新：GET /api/v1/instances/<int:instance_id>/databases/sizes

---

### Task 1: Add API v1 instances database sizes contract test

**Files:**
- Modify: tests/unit/routes/test_api_v1_instances_contract.py

**Step 1: Write the failing test**

- `test_api_v1_instances_database_sizes_contract`

**Step 2: Run tests to verify it fails**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -v`

Expected: FAIL（404 或未实现）

---

### Task 2: Implement API v1 instances database sizes endpoint

**Files:**
- Modify: app/api/v1/namespaces/instances.py

**Step 1: Implement GET /api/v1/instances/<id>/databases/sizes**

- 复用旧接口 Query 参数（snake_case）：
  - `start_date`, `end_date`（YYYY-MM-DD，可选）
  - `database_name`（可选）
  - `latest_only`（默认 false）
  - `include_inactive`（默认 false）
  - `limit`（默认 100）
  - `offset`（默认 0）
- 调用: `InstanceDatabaseSizesService().fetch_sizes(options, latest_only=latest_only)`
- 返回:
  - `latest_only=false`: `data={"total","limit","offset","databases"}`
  - `latest_only=true`: 增加 `active_count/filtered_count/total_size_mb`
  - message="数据库大小数据获取成功"

**Step 2: Run tests**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -v`

Expected: PASS

---

### Task 3: Update progress doc + verification gates

**Files:**
- Modify: docs/changes/refactor/004-flask-restx-openapi-migration-progress.md

**Step 1: Mark endpoint as DONE**

- 将 `GET /instances/api/databases/<int:instance_id>/sizes` 标记为 DONE，并注明新入口（不带 METHOD）。

**Step 2: Run unit tests**

Run: `uv run pytest -m unit`

Expected: 0 failed

**Step 3: Verify OpenAPI export**

Run: `uv run python scripts/dev/openapi/export_openapi.py --check`

Expected: exit 0

**Step 4: Ensure progress doc endpoint set not drifted**

Run: `uv run python scripts/dev/docs/generate_api_routes_inventory.py --check-progress`

Expected: missing=0 extra=0

