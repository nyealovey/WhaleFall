# Account Permissions Phase 7 (Drop Legacy Columns) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 删除 `account_permission` 表中 legacy 权限列，并移除所有依赖这些列的写入/回退逻辑，仅保留 v4 `permission_snapshot` + `permission_facts`。

**Architecture:** 同步写入路径改为“只写 snapshot + facts + type_specific”；读路径改为“只读 snapshot/view（缺失即报错）”，分类评估只使用 `permission_facts`（缺失则用 snapshot 现算）。

**Tech Stack:** Flask + SQLAlchemy + Alembic, pytest, (optional) Docker Postgres.

---

### Task 1: Drop legacy permission columns (DB + model)

**Files:**
- Create: `migrations/versions/20251230190000_drop_account_permission_legacy_permission_columns.py`
- Modify: `app/models/account_permission.py`

**Step 1: Add migration (upgrade/downgrade)**

Create new Alembic migration that drops legacy columns:

```py
LEGACY_COLUMNS = [
  "global_privileges",
  "database_privileges",
  "predefined_roles",
  "role_attributes",
  "database_privileges_pg",
  "tablespace_privileges",
  "server_roles",
  "server_permissions",
  "database_roles",
  "database_permissions",
  "oracle_roles",
  "system_privileges",
  "tablespace_privileges_oracle",
]

def upgrade():
  for col in LEGACY_COLUMNS:
    op.drop_column("account_permission", col)
```

Downgrade should re-add这些列（JSON/JSONB，nullable=True），以便必要时可回滚。

**Step 2: Update model**

In `app/models/account_permission.py`:
- 删除上述列的 `db.Column(...)` 定义
- 删除 `to_dict()` 中这些字段的输出
- 删除/重写 `get_permissions_by_db_type()`（不再从列读取；如保留则应基于 `permission_snapshot["categories"]` + `type_specific` 构造）

**Step 3: Run unit model contract tests**

Run: `uv run pytest -m unit tests/unit/models/test_account_permission.py -q`

Expected: PASS

---

### Task 2: Remove PERMISSION_FIELDS and legacy column writes (sync + facts)

**Files:**
- Modify: `app/services/accounts_sync/permission_manager.py`
- Modify: `app/services/accounts_permissions/facts_builder.py`
- Delete: `scripts/verify_snapshot_consistency.py`

**Step 1: Refactor `_apply_permissions` to stop touching legacy columns**

Replace legacy-column loop with:
- 始终写入 `record.permission_snapshot = _build_permission_snapshot(...)`
- 始终写入 `record.permission_facts = build_permission_facts(..., snapshot=record.permission_snapshot)`
- 仅在 `permissions` 中包含 `type_specific` 时更新 `record.type_specific`（保留现有结构/兼容页面）

**Step 2: Delete `PERMISSION_FIELDS` constant**

Remove `PERMISSION_FIELDS` entirely and any code paths that:
- `setattr(record, field, ...)` for legacy columns
- “缺失则置 None”的清空逻辑

**Step 3: Make facts builder snapshot-only**

In `build_permission_facts(...)`:
- 移除 “legacy fallback” `_build_categories_from_legacy`
- 当 snapshot 缺失/非 v4 时，`categories = {}` 并打 `errors += ["SNAPSHOT_MISSING"]`
- 所有 roles/privileges/capabilities 计算仅基于 snapshot categories（保持现有输出结构）

**Step 4: Remove legacy consistency script**

Delete `scripts/verify_snapshot_consistency.py` (it depends on legacy columns).

**Step 5: Run unit tests for manager/facts**

Run: `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py tests/unit/services/test_permission_facts_builder.py -q`

Expected: PASS

---

### Task 3: Remove legacy read fallbacks (services/orchestrator) and verify

**Files:**
- Modify: `app/services/ledgers/accounts_ledger_permissions_service.py`
- Modify: `app/services/instances/instance_accounts_service.py`
- Modify: `app/services/account_classification/orchestrator.py`
- Delete: `app/services/accounts_permissions/flags.py` (and call sites)
- Modify: `app/settings.py` (remove ACCOUNT_PERMISSION_SNAPSHOT_READ/WRITE)
- Modify: `tests/unit/services/test_permission_snapshot_read_path.py`
- Modify: `tests/unit/services/test_account_permission_manager.py` (remove disabled snapshot test paths)

**Step 1: Force snapshot read path**

In ledger/instance permission detail services:
- always call `build_permission_snapshot_view(account)`
- if snapshot missing -> raise `AppError(message_key="SNAPSHOT_MISSING", status_code=409, ...)`
- derive UI payload from snapshot categories (existing adapter is fine) and never read legacy columns.

**Step 2: Orchestrator facts without legacy columns**

In `_get_permission_facts`:
- prefer persisted `permission_facts`
- else build from snapshot view (no legacy column fallback)

**Step 3: Remove snapshot read/write flags**

Delete flag helpers and remove env parsing in `app/settings.py` for:
- `ACCOUNT_PERMISSION_SNAPSHOT_WRITE`
- `ACCOUNT_PERMISSION_SNAPSHOT_READ`

Update tests accordingly (no env toggles).

**Step 4: Full unit run**

Run: `uv run pytest -m unit -q`

Expected: PASS

