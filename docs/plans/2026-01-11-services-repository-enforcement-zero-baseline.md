# Services Repository Enforcement: Zero Baseline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 将 `scripts/ci/services-repository-enforcement-guard.sh` 的命中数降为 `0`，并将 `scripts/ci/baselines/services-repository-enforcement.txt` 收敛为“空基线”(禁止新增/允许白名单为空)。

**Architecture:** 以 `services-layer-standards` / `repository-layer-standards` 为口径：`app/services/**` 禁止直接使用 `Model.query` 与 `db.session.(query|execute)`；所有查询/SQL/Upsert/批量 delete 统一下沉到 `app/repositories/**`，Service 仅负责业务编排、事务边界与日志。

**Tech Stack:** Python(Flask + SQLAlchemy), Bash(`rg` guards), pytest.

---

## Verification Baseline(每个任务都可重复跑)

Run:

```bash
./scripts/ci/services-repository-enforcement-guard.sh
./scripts/ci/db-session-write-boundary-guard.sh
uv run pytest -m unit
```

Expected:

- `services-repository-enforcement-guard` 最终命中 `0`
- 其他 guard 不回归
- unit tests 全绿

---

### Task 1: 清理 services 内 docstring 命中(非代码)

**Files:**
- Modify: `app/services/accounts_sync/accounts_sync_task_service.py`
- Modify: `app/services/capacity/capacity_tasks_read_service.py`
- Modify: `app/services/aggregation/aggregation_tasks_read_service.py`

**Steps:**
- 将 docstring 中的 ``.query`` / `db.session.query` 等字样改为“查库/ORM 查询”等不触发门禁的表达，不改变语义。
- Run: `./scripts/ci/services-repository-enforcement-guard.sh`

---

### Task 2: 小型 services 的 `.query` 下沉到现有 Repository

**Files:**
- Modify: `app/services/auth/login_service.py`
- Modify: `app/services/auth/auth_me_read_service.py`
- Modify: `app/services/users/user_write_service.py`
- Modify: `app/services/credentials/credential_write_service.py`
- Modify: `app/repositories/users_repository.py`
- Modify: `app/repositories/credentials_repository.py`

**Steps:**
- 通过 repository 提供 `get_by_id/get_by_username/exists_*` 等方法，Service 不再直接 `Model.query`。
- Run guards + unit tests.

---

### Task 3: instances/cache/capacity/database_sync 等读取统一走 repository

**Files:**
- Modify: `app/repositories/instances_repository.py`
- Modify: `app/services/cache/cache_actions_service.py`
- Modify: `app/services/capacity/current_aggregation_service.py`
- Modify: `app/services/capacity/instance_capacity_sync_actions_service.py`
- Modify: `app/services/database_sync/database_sync_service.py`

**Steps:**
- 复用/扩展 `InstancesRepository` / `FilterOptionsRepository` 的最小读能力（按 ID 获取、活跃实例列表/计数等）。
- Run guards + unit tests.

---

### Task 4: accounts_sync managers 的 `.query` 下沉

**Files:**
- Modify: `app/repositories/instance_accounts_repository.py`
- Create: `app/repositories/accounts_sync_repository.py`
- Modify: `app/services/accounts_sync/account_query_service.py`
- Modify: `app/services/accounts_sync/accounts_sync_actions_service.py`
- Modify: `app/services/accounts_sync/inventory_manager.py`
- Modify: `app/services/accounts_sync/permission_manager.py`

**Steps:**
- 将权限记录查找、清单表加载、活跃实例计数/获取等 Query 全部移到 repositories。
- Run guards + unit tests.

---

### Task 5: aggregation 相关 services/runners 的 Query 全部下沉

**Files:**
- Create: `app/repositories/aggregation_repository.py`
- Create: `app/repositories/aggregation_runner_repository.py`
- Modify: `app/services/aggregation/aggregation_service.py`
- Modify: `app/services/aggregation/query_service.py`
- Modify: `app/services/aggregation/aggregation_tasks_read_service.py`
- Modify: `app/services/aggregation/database_aggregation_runner.py`
- Modify: `app/services/aggregation/instance_aggregation_runner.py`

**Steps:**
- Repository 负责 `db.session.query` 聚合、`Model.query` 查询与 existing record 读取；Runner 只做计算/落库编排。
- Run guards + unit tests.

---

### Task 6: database_sync persistence/table_size 的 `execute/query` 下沉

**Files:**
- Create: `app/repositories/capacity_persistence_repository.py`
- Create: `app/repositories/database_table_size_stats_repository.py`
- Modify: `app/services/database_sync/persistence.py`
- Modify: `app/services/database_sync/table_size_coordinator.py`

**Steps:**
- 将 upsert/cleanup 的 `db.session.execute` / `Model.query` / delete 下沉到 repositories。
- Run guards + unit tests.

---

### Task 7: instances batch service 的 Query/execute 下沉

**Files:**
- Create: `app/repositories/instances_batch_repository.py`
- Modify: `app/services/instances/batch_service.py`

**Steps:**
- Repository 负责：按 ID 批量加载实例、查询已存在名称、批量删除关联数据与 tag link 删除。
- Service 仅负责参数校验、循环编排与日志。
- Run guards + unit tests.

---

### Task 8: partition management 的 `execute/query` 下沉

**Files:**
- Create: `app/repositories/partition_management_repository.py`
- Modify: `app/services/partition_management_service.py`

**Steps:**
- 所有 `db.session.execute(...)` / `select + execute` 由 repository 承接。
- Run guards + unit tests.

---

### Task 9: accounts statistics page 的 Query 下沉

**Files:**
- Modify: `app/services/statistics/accounts_statistics_page_service.py`

**Steps:**
- 通过 `InstancesRepository`/`SyncSessionsRepository` 获取活跃实例与最近会话。
- Run guards + unit tests.

---

### Task 10: 更新基线与文档

**Files:**
- Modify: `scripts/ci/baselines/services-repository-enforcement.txt`
- Modify: `docs/reports/2026-01-11-backend-layer-boundary-audit.md`
- Modify: `docs/reports/2026-01-11-backend-layer-boundary-audit-progress.md`

**Steps:**
- 确认 `./scripts/ci/services-repository-enforcement-guard.sh` 输出命中 `0` 后执行：
  - `./scripts/ci/services-repository-enforcement-guard.sh --update-baseline`
- 将报告中的 services 命中数更新为最新(预期 0)，并在 progress 文档中标记 Phase 6 进入/完成。

