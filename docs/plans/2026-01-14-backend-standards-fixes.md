# Backend Standards Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按 `docs/reports/2026-01-14-backend-standards-audit-report.md` 修复 `app/**` 内的 MUST 级违规点（回退可观测性 + Service/Repository 边界），并补充最小验证。

**Architecture:** 优先做最小侵入修改：在现有日志调用点补齐 `fallback=true` / `fallback_reason`；将 `db.session.add/delete/flush` 从 Service 迁移到对应 Repository 的稳定方法中；保持事务提交边界不变（仍由 `safe_route_call` / task 入口负责 commit/rollback）。

**Tech Stack:** Flask, SQLAlchemy, structlog, Ruff, Pyright

### Task 1: 回退/降级日志可观测性（P0）

**Files:**
- Modify: `app/services/sync_session_service.py`
- Modify: `app/services/accounts_sync/permission_manager.py`
- Modify: `app/tasks/capacity_collection_tasks.py`
- Modify: `app/infra/database_batch_manager.py`
- Modify: `app/views/mixins/resource_forms.py`
- Modify: `app/services/connection_adapters/adapters/oracle_adapter.py`

**Step 1: 写入最小字段**
- 在所有“异常→兜底值/continue/partial failure”日志中补齐 `fallback=True` 与 `fallback_reason="<stable_code>"`。
- 对 silent fallback 补一条低噪音结构化日志（推荐使用 `app/infra/route_safety.py::log_fallback`）。

**Step 2: 静态验证**
- Run: `uv run ruff check app`
- Run: `uv run pyright app`

### Task 2: Service 层数据写入收敛到 Repository（P1）

**Files:**
- Modify: `app/services/auth/change_password_service.py`
- Modify: `app/repositories/users_repository.py`（如需）
- Modify: `app/services/sync_session_service.py`
- Modify: `app/repositories/sync_sessions_repository.py`
- Modify: `app/services/database_sync/inventory_manager.py`
- Modify: `app/repositories/instance_databases_repository.py`
- Modify: `app/services/instances/batch_service.py`
- Modify: `app/repositories/instances_batch_repository.py`

**Step 1: 迁移 add/delete/flush**
- 将 Service 内的 `db.session.add/delete/flush` 替换为 Repository 方法（新增方法时保持命名清晰、避免 commit/rollback）。
- 保持 `db.session.begin_nested()` 等事务语义仍在 Service（或入口）侧，Repository 仅负责 add/delete/flush。

**Step 2: 静态验证**
- Run: `uv run ruff check app`
- Run: `uv run pyright app`

### Task 3: 需要确认的点（向用户咨询）

**Question:**
- `app/services/accounts_sync/inventory_manager.py` 目前使用 `AccountsSyncRepository`（读模型）但在 Service 内直接 `db.session.add/flush`。
  - 选项 A：扩展 `app/repositories/accounts_sync_repository.py` 增加写入方法（add/flush），让 `AccountInventoryManager` 继续复用同一个 repository。
  - 选项 B：新建一个 write-oriented repository（例如 `app/repositories/instance_accounts_write_repository.py` 或 `app/repositories/accounts_inventory_repository.py`），读写分离更清晰。

