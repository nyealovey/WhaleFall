# Veeam Multi Source Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 支持配置多个 Veeam 数据源，并在一次同步任务中同步所有启用的数据源。

**Architecture:** 保留现有 Veeam provider、匹配、restore point 聚合和“同源同名机器折叠为最新快照”的行为。本次只把数据源绑定、快照写入、查询和页面管理从单源改为多源，并按 `source_binding_id` 隔离不同 Veeam 源的数据。

**Tech Stack:** Flask、Flask-RESTX、SQLAlchemy、Alembic、APScheduler、现有 WhaleFall Veeam service/repository/test 架构。

## Scope

### 本次做

- 支持多个 Veeam source binding。
- 每个 source binding 独立保存连接信息、匹配域名、启停状态和最后同步状态。
- 快照表增加 `source_binding_id`，全量同步只替换当前 source 的快照。
- `sync_veeam_backups` 定时任务保持一个任务入口，内部依次同步所有启用 source。
- 实例备份查询跨所有启用 source 匹配，返回最新命中的备份，并带上来源信息。
- 管理页面从单个绑定表单调整为 source 列表 + 新增/编辑/解绑。

### 本次不做

- 不解决同一个 Veeam 内机器重名的精确区分问题。
- 不引入每个 Veeam 独立 scheduler job。
- 不重写 Veeam provider 的分页、解析、restore point、backupFiles 逻辑。
- 不改变现有备份状态口径、告警规则和实例详情主展示字段。

## Data Model

### Task 1: Add multi-source schema migration

**Files:**
- Create: `migrations/versions/<timestamp>_support_multiple_veeam_sources.py`
- Modify: `app/models/veeam_source_binding.py`
- Modify: `app/models/veeam_machine_backup_snapshot.py`
- Modify: `app/core/types/orm_kwargs.py`
- Test: `tests/unit/repositories/test_veeam_repository_snapshot_write_contract.py`

**Required changes:**

- Add `name` to `veeam_source_bindings`.
- Keep `credential_id` as a normal foreign key, but remove ORM `unique=True` and DB unique constraint `uq_veeam_source_binding_credential_id`.
- Add `source_binding_id` to `veeam_machine_backup_snapshots`.
- Add FK: `veeam_machine_backup_snapshots.source_binding_id -> veeam_source_bindings.id`.
- Replace global unique constraints:
  - old: `normalized_machine_name`
  - old: `normalized_machine_ip`
  - new: `(source_binding_id, normalized_machine_name)`
  - new: `(source_binding_id, normalized_machine_ip)`
- Backfill existing snapshots with the first existing binding id.
- Backfill existing binding `name` from credential name if possible, otherwise use `默认 Veeam`.

**Step 1: Write failing migration/model tests**

Add a repository test that creates two source bindings, writes the same machine name under each source, and asserts both rows survive.

**Step 2: Implement migration and model changes**

Keep the migration additive/backfill/drop-constraint oriented. Do not edit old migration files.

**Step 3: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/repositories/test_veeam_repository_snapshot_write_contract.py -q
```

Expected: PASS.

## Repository Layer

### Task 2: Split global binding access into list/get APIs

**Files:**
- Modify: `app/repositories/veeam_repository.py`
- Test: `tests/unit/repositories/test_veeam_repository_snapshot_write_contract.py`

**Required changes:**

- Keep `get_binding()` temporarily as a compatibility alias returning the first binding, if existing tests or UI still need it during migration.
- Add:
  - `list_bindings()`
  - `list_enabled_bindings()`
  - `get_binding_by_id(binding_id)`
  - `delete_binding_by_id(binding_id)`
  - `clear_machine_backup_snapshots(source_binding_id=None)`
- Change snapshot write methods to require source context:
  - `replace_machine_backup_snapshots(records, source_binding_id, sync_run_id, synced_at)`
  - `upsert_machine_backup_snapshots(records, source_binding_id, sync_run_id, synced_at)`
- In `_write_machine_backup_snapshots`, query existing rows only for the current `source_binding_id`.
- In delete-missing mode, delete only rows for the current source.

**Step 1: Write failing tests**

Add tests for:

- `replace_machine_backup_snapshots` for source A does not delete source B rows.
- `upsert_machine_backup_snapshots` updates only rows under the requested source.

**Step 2: Implement repository changes**

Thread `source_binding_id` into `_SnapshotWriteRecord` application by setting `row.source_binding_id`.

**Step 3: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/repositories/test_veeam_repository_snapshot_write_contract.py -q
```

Expected: PASS.

## Source Management API

### Task 3: Convert source service from single binding to source list

**Files:**
- Modify: `app/services/veeam/source_service.py`
- Modify: `app/schemas/veeam.py`
- Modify: `app/api/v1/namespaces/veeam.py`
- Test: `tests/unit/routes/test_api_v1_veeam_source_contract.py`

**Required changes:**

- Update payload schema to include optional `name`.
- Add service methods:
  - `list_sources_payload()`
  - `create_source(...)`
  - `update_source(source_id, ...)`
  - `delete_source(source_id)`
  - `set_source_enabled(source_id, is_enabled)`
  - `get_binding_or_error(source_id)`
- Preserve old `/api/v1/veeam/source` response shape only if frontend transition needs it; otherwise make it return `sources`.
- Preferred route shape:
  - `GET /api/v1/veeam/sources`
  - `POST /api/v1/veeam/sources`
  - `PUT /api/v1/veeam/sources/<source_id>`
  - `DELETE /api/v1/veeam/sources/<source_id>`
  - `POST /api/v1/veeam/sources/<source_id>/actions/enable`
  - `POST /api/v1/veeam/sources/<source_id>/actions/disable`

**Step 1: Write failing route contract tests**

Cover list/create/update/delete with two sources.

**Step 2: Implement service and route changes**

Keep validation messages in Chinese and preserve existing permission/CSRF style.

**Step 3: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/routes/test_api_v1_veeam_source_contract.py -q
```

Expected: PASS.

## Sync Pipeline

### Task 4: Sync all enabled Veeam sources from one scheduler task

**Files:**
- Modify: `app/services/veeam/sync_actions_service.py`
- Modify: `app/tasks/veeam_backup_sync_tasks.py`
- Test: `tests/unit/services/test_veeam_sync_actions_service_contract.py`
- Test: `tests/unit/tasks/test_veeam_backup_sync_tasks.py`

**Required changes:**

- Keep task key `sync_veeam_backups`.
- Change `prepare_background_sync()` to create one parent TaskRun for all sources.
- `_sync_once()` should load all enabled bindings and sync each source in sequence.
- Extract existing single-binding body into helper:
  - `_sync_source_once(binding, created_by, run_id, task_runs_service)`
- Each source should:
  - create its own provider session
  - use its own `match_domains`
  - write snapshots with its own `source_binding_id`
  - update its own `last_sync_at/status/run_id/error`
- One source failure should not stop later sources.
- If at least one source succeeds and one fails, final summary should mark partial success.
- If all enabled sources fail, final TaskRun should fail.
- If no enabled source exists, raise `ValidationError("请先启用至少一个 Veeam 数据源")`.

**Step 1: Write failing sync tests**

Add tests for:

- two enabled sources both sync and both write snapshots.
- source A failure does not prevent source B from syncing.
- no enabled source returns validation error.
- `replace_machine_backup_snapshots` receives the correct `source_binding_id`.

**Step 2: Refactor minimally**

Do not rewrite provider methods. Move the existing `_sync_once` body into `_sync_source_once` and wrap it in source iteration.

**Step 3: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/services/test_veeam_sync_actions_service_contract.py tests/unit/tasks/test_veeam_backup_sync_tasks.py -q
```

Expected: PASS.

## Backup Query Surface

### Task 5: Return source-aware backup info

**Files:**
- Modify: `app/repositories/veeam_repository.py`
- Modify: `app/services/veeam/instance_backup_read_service.py`
- Test: `tests/unit/routes/test_api_v1_instances_backup_info_contract.py`
- Test: `tests/unit/routes/test_api_v1_instances_contract.py`

**Required changes:**

- `find_best_backup_for_instance_name()` should search all enabled source snapshots.
- `fetch_backup_summary_map()` should search all enabled source snapshots.
- Candidate names should be built from each source's `match_domains`.
- Result payload should include:
  - `source_binding_id`
  - `source_name`
  - `source_server_host`
- If multiple sources match the same instance, keep current behavior of choosing the latest `latest_backup_at`.

**Step 1: Write failing tests**

Add a test where two sources both match the same instance and assert the newer backup wins with source metadata.

**Step 2: Implement repository query**

Avoid N+1 queries for list pages. Load enabled bindings once, build candidate maps per source, query snapshots by source and candidate sets.

**Step 3: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/routes/test_api_v1_instances_backup_info_contract.py tests/unit/routes/test_api_v1_instances_contract.py -q
```

Expected: PASS.

## Single Instance Sync

### Task 6: Keep single-instance sync compatible

**Files:**
- Modify: `app/api/v1/namespaces/veeam.py`
- Modify: `app/services/veeam/sync_actions_service.py`
- Test: `tests/unit/routes/test_api_v1_veeam_source_contract.py`
- Test: `tests/unit/services/test_veeam_sync_actions_service_contract.py`

**Required changes:**

- Preferred API:
  - `POST /api/v1/veeam/sources/<source_id>/instances/<instance_id>/actions/sync`
- Keep old instance sync route if needed, but define it as syncing all enabled sources for that instance or the first enabled source. Prefer explicit `source_id` to avoid ambiguity.
- `sync_instance_now()` should accept `source_binding_id`.
- Single-instance upsert must pass `source_binding_id`.

**Step 1: Write failing tests**

Cover explicit source sync and verify unrelated source snapshots survive.

**Step 2: Implement explicit source sync**

Reuse existing single-instance pipeline, only thread binding/source id into it.

**Step 3: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/routes/test_api_v1_veeam_source_contract.py tests/unit/services/test_veeam_sync_actions_service_contract.py -q
```

Expected: PASS.

## Frontend

### Task 7: Update Veeam source management UI

**Files:**
- Modify: `app/static/js/modules/services/veeam_source_service.js`
- Modify: `app/static/js/modules/views/integrations/veeam/source.js`
- Modify: Veeam system-settings template under `app/templates/**` if present
- Test: frontend contract tests under `tests/unit/test_frontend_*veeam*`

**Required changes:**

- Show a compact source list:
  - name
  - server host/port
  - credential
  - enabled status
  - last sync status/time
  - actions: edit, enable/disable, delete, sync
- Reuse existing form for create/edit.
- Do not add dashboard-style decorative cards; keep the page compact.
- Preserve existing provider-ready defaults.

**Step 1: Update frontend contract tests**

Assert the page/service references the new list endpoints and source actions.

**Step 2: Implement JS/template changes**

Keep existing API envelope handling.

**Step 3: Run frontend checks**

Run:

```bash
./scripts/ci/eslint-report.sh quick
uv run pytest tests/unit/test_frontend_scheduler_veeam_edit_contract.py tests/unit/test_frontend_veeam_source_contract.py -q
```

Expected: PASS.

## TaskRun Summary and Observability

### Task 8: Add source-level sync summary

**Files:**
- Modify: `app/services/task_runs/task_run_summary_builders.py`
- Modify: `app/services/veeam/sync_actions_service.py`
- Test: `tests/unit/services/test_task_run_summary_builders.py`

**Required changes:**

- Keep existing top-level summary fields where possible.
- Add `sources` list:
  - `source_binding_id`
  - `source_name`
  - `status`
  - `snapshots_written_total`
  - `error_message`
- Keep stage keys stable:
  - `fetch_backup_objects`
  - `match_backup_objects`
  - `fetch_restore_points`
  - `fetch_backup_files`
  - `write_snapshots`
- Include source metadata in logs for each source.

**Step 1: Write failing summary tests**

Assert multi-source summary contains per-source status and preserves existing `ext.type`.

**Step 2: Implement summary builder changes**

Keep old fields for compatibility.

**Step 3: Run targeted tests**

Run:

```bash
uv run pytest tests/unit/services/test_task_run_summary_builders.py -q
```

Expected: PASS.

## Final Verification

### Task 9: Run full relevant quality gates

**Files:**
- No code changes expected.

**Step 1: Run unit tests**

Run:

```bash
uv run pytest -m unit
```

Expected: PASS.

**Step 2: Run style/type checks**

Run:

```bash
./scripts/ci/ruff-report.sh style
./scripts/ci/pyright-report.sh
./scripts/ci/eslint-report.sh quick
./scripts/ci/refactor-naming.sh --dry-run
```

Expected: no new failures caused by this change.

**Step 3: Manual smoke checklist**

- Create Veeam source A.
- Create Veeam source B.
- Disable source B and run sync; only source A syncs.
- Enable source B and run sync; both sources sync.
- Delete source A; source A snapshots are removed or hidden according to product decision, source B snapshots remain.
- Instance detail page shows backup info and source name.
- Scheduler still shows built-in task `sync_veeam_backups`.

## Rollback Plan

- Migration downgrade should drop `source_binding_id` and restore old unique constraints only if rows can be collapsed safely.
- Safer operational rollback is application rollback plus DB backup restore before migration.
- Because multi-source may create multiple rows for the same normalized machine across sources, automatic downgrade should refuse if more than one source exists.

## Compatibility Notes

- Existing single-source deployments migrate to one source named `默认 Veeam`.
- Existing scheduler task id remains `sync_veeam_backups`.
- Existing同源重名折叠逻辑保持不变：同一 source 内按 normalized machine name/IP 保留最新快照。
- API clients using old `/veeam/source` should either receive a compatibility payload or be updated with the frontend in the same release.
