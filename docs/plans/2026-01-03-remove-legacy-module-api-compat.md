# Remove Legacy `/<module>/api/*` Compatibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 迁移完成后清理遗留：将 RestX `marshal/fields` 定义从 `app/routes/**` 收敛到 `app/api/v1/**`，并移除 legacy `/<module>/api/*` 404 contract tests（保留 `/api/v1/**` contract tests）。

**Architecture:** `/api/v1/**` 是唯一对外 JSON API。旧 `app/routes/**` 仅保留页面/HTML 路由；API v1 相关的 RestX 字段定义放入 `app/api/v1/restx_models/**`，由各 `namespaces/*` 引用。旧 `/<module>/api/*` 下线路径不再通过单测门禁固化。

**Tech Stack:** Flask, Flask-RESTX, uv, pytest, ruff, pyright

---

### Task 1: Create `app/api/v1/restx_models` package

**Files:**
- Create: `app/api/v1/restx_models/__init__.py`

**Step 1: Add empty package init**
- Implement: create empty `__init__.py`

**Step 2: Sanity import**
- Run: `uv run python -c "import app.api.v1.restx_models"`
- Expected: exit code 0

---

### Task 2: Move RestX marshal fields to API v1

**Files:**
- Move: `app/routes/common_restx_models.py` -> `app/api/v1/restx_models/common.py`
- Move: `app/routes/credentials_restx_models.py` -> `app/api/v1/restx_models/credentials.py`
- Move: `app/routes/dashboard_restx_models.py` -> `app/api/v1/restx_models/dashboard.py`
- Move: `app/routes/partition_restx_models.py` -> `app/api/v1/restx_models/partition.py`
- Move: `app/routes/scheduler_restx_models.py` -> `app/api/v1/restx_models/scheduler.py`
- Move: `app/routes/accounts/restx_models.py` -> `app/api/v1/restx_models/accounts.py`
- Move: `app/routes/capacity/restx_models.py` -> `app/api/v1/restx_models/capacity.py`
- Move: `app/routes/history/restx_models.py` -> `app/api/v1/restx_models/history.py`
- Move: `app/routes/instances/restx_models.py` -> `app/api/v1/restx_models/instances.py`
- Move: `app/routes/tags/restx_models.py` -> `app/api/v1/restx_models/tags.py`
- Delete (unused): `app/routes/users_restx_models.py`
- Delete (unused): `app/routes/databases/restx_models.py`

**Step 1: Apply file moves/deletions**
- Implement: move content as-is; no behavior changes

**Step 2: Ensure no leftover references**
- Run: `rg -n "app\\.routes\\..*restx_models|app\\.routes\\.users_restx_models|app\\.routes\\.databases\\.restx_models" app tests`
- Expected: no matches

---

### Task 3: Update API v1 namespaces imports

**Files:**
- Modify: `app/api/v1/namespaces/*.py`

**Step 1: Replace imports from `app.routes.*restx_models`**
- Implement: point to `app.api.v1.restx_models.*`

**Step 2: Run a quick import sweep**
- Run: `uv run python -c "from app.api.v1 import create_api_v1_blueprint; print('ok')"`
- Expected: prints `ok`

---

### Task 4: Remove legacy `/<module>/api/*` 404 contract tests

**Files:**
- Delete: `tests/unit/routes/test_legacy_api_gone_contract.py`
- Delete: `tests/unit/routes/test_instances_list_contract.py`
- Delete: `tests/unit/routes/test_users_list_contract.py`
- Delete: `tests/unit/routes/test_tags_list_contract.py`
- Delete: `tests/unit/routes/test_credentials_list_contract.py`
- Delete: `tests/unit/routes/test_accounts_ledgers_contract.py`
- Delete: `tests/unit/routes/test_databases_ledger_contract.py`
- Delete: `tests/unit/routes/test_history_logs_list_contract.py`
- Delete: `tests/unit/routes/test_dashboard_charts_contract.py`
- Delete: `tests/unit/routes/test_common_filter_options_contract.py`
- Delete: `tests/unit/routes/test_capacity_databases_contract.py`
- Delete: `tests/unit/routes/test_capacity_instances_contract.py`

**Step 1: Delete files**
- Implement: remove the tests entirely

**Step 2: Ensure no more legacy module/api usage in route tests**
- Run: `rg -n "\\\"/[^\\\"]+/api/\\\"" tests/unit/routes`
- Expected: no matches

---

### Task 5: Update RestX integration reference doc

**Files:**
- Modify: `docs/reference/api/flask-restx-integration.md`

**Step 1: Update scope & file paths**
- Implement: point examples/list to `app/api/v1/restx_models/**`

**Step 2: Verify doc still reflects current architecture**
- Run: `rg -n "app/routes/.*restx_models" docs/reference/api/flask-restx-integration.md`
- Expected: no matches

---

### Task 6: Verify

**Step 1: Format**
- Run: `make format`

**Step 2: Typecheck**
- Run: `make typecheck`

**Step 3: Unit tests**
- Run: `uv run pytest -m unit`
- Expected: PASS
