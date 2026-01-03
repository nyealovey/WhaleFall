# Permission Facts Column Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Persist derived permission facts into `account_permission.permission_facts` (JSONB) for stats queries, and remove `permission_snapshot_version`.

**Architecture:** Keep `permission_snapshot` as raw/audit payload (schema version lives in JSON). Derive a compact, query-friendly `permission_facts` JSON from snapshot when present, otherwise fall back to legacy permission columns during rollout.

**Tech Stack:** Flask, SQLAlchemy, Alembic, PostgreSQL JSONB, pytest

---

### Task 1: Schema & model contract

**Files:**
- Create: `migrations/versions/20251230183000_add_account_permission_facts_column_drop_snapshot_version.py`
- Modify: `app/models/account_permission.py`
- Test: `tests/unit/models/test_account_permission.py`

**Step 1: Write the failing test**

- Update `tests/unit/models/test_account_permission.py` to assert `permission_facts` exists (JSONB, nullable), and to stop asserting `permission_snapshot_version`.

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/models/test_account_permission.py -v`
Expected: FAIL because model/table contract still exposes `permission_snapshot_version` but not `permission_facts`.

**Step 3: Write minimal implementation**

- Migration:
  - add `permission_facts` (jsonb, nullable)
  - drop `permission_snapshot_version`
- Model: remove `permission_snapshot_version`, add `permission_facts` (JSONB variant), update `to_dict()`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest -m unit tests/unit/models/test_account_permission.py -v`
Expected: PASS

---

### Task 2: Facts builder + persistence

**Files:**
- Create: `app/services/accounts_permissions/facts_builder.py`
- Modify: `app/services/accounts_sync/permission_manager.py`
- Test: `tests/unit/services/test_account_permission_manager.py`

**Step 1: Write failing tests**

- Extend manager tests to assert:
  - when sync apply is called, `permission_facts` is written (even if snapshot write is disabled)
  - `permission_facts` includes expected fields (`db_type`, `is_superuser`, `is_locked`, `capabilities`, `roles`, `errors`, `meta`).

**Step 2: Run tests to verify they fail**

Run: `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py -v`
Expected: FAIL because `permission_facts` is not populated.

**Step 3: Implement builder + write path**

- `facts_builder.build_permission_facts(...)`:
  - prefer `permission_snapshot` when it is a dict and `version == 4`
  - otherwise fall back to legacy-per-db permission dict (`AccountPermission.get_permissions_by_db_type()` when available, else the `permissions` arg)
  - compute:
    - `capabilities`: minimal set (`SUPERUSER`, `GRANT_ADMIN`) with `capability_reasons`
    - `roles`: db-specific extraction
    - `privileges`: normalized lists/maps for `global/server/database/tablespace` as available
    - `errors`: propagate snapshot errors if present
    - `meta.source`: `snapshot` or `legacy`
    - `meta.snapshot_version`: 4 when built from snapshot
- `permission_manager._apply_permissions`:
  - stop setting `permission_snapshot_version`
  - always set `record.permission_facts = build_permission_facts(...)` after applying permissions/snapshot

**Step 4: Run tests to verify pass**

Run: `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py -v`
Expected: PASS

---

### Task 3: Update remaining tests & scripts

**Files:**
- Modify: `tests/unit/services/test_permission_snapshot_read_path.py`
- Modify: `tests/unit/services/test_permission_snapshot_view.py`

**Step 1: Adjust stubs**

- Ensure stubs in tests include `permission_facts` attribute when needed (SimpleNamespace).

**Step 2: Run unit tests**

Run: `uv run pytest -m unit -v`
Expected: PASS
