# 024 layer first api restructure progress

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-07
> 更新: 2026-01-07
> 范围: API v1 路径收敛(health/logs/sync-sessions/scheduler/partitions/tags bulk/cache/instances/accounts/databases/files exports), layer-first 目录落点
> 关联方案: `024-layer-first-api-restructure-plan.md`
> 关联: `docs/Obsidian/standards/doc/changes-standards.md`, `docs/Obsidian/standards/doc/documentation-standards.md`

---

## 当前状态(摘要)

- 已完成 API v1 路径收敛(health/logs/sync-sessions/scheduler/partitions/tags bulk/cache/accounts/databases/files exports)与顶层资源(accounts/databases)迁移.
- 已补齐 databases ledgers 的 `instance_id` query 过滤(含 export).
- 已完成 Phase 4 method 收敛: instances soft delete 改为 `DELETE`, restore 收敛到 `actions/restore`; tags/credentials delete 改为 `DELETE`.
- 已完成 Phase 5 门禁验证(OpenAPI/unit/ruff/typecheck).
- 剩余(可选): Phase 4 的 batch 操作收敛到 `/actions/*`(如需).

## Checklist

### Phase 0: 方案与清单冻结

- [x] 更新架构提案: `docs/Obsidian/architecture/layer-first-api-restructure.md`
- [x] 更新索引入口: `docs/README.md`, `docs/Obsidian/architecture/README.md`
- [x] 建立 plan/progress: `024-layer-first-api-restructure-{plan,progress}.md`
- [x] 同步相关域文档(调用方视角/Flow): `docs/Obsidian/architecture/instances-domain.md`, `docs/Obsidian/architecture/accounts-permissions-domain.md`, `docs/Obsidian/architecture/databases-ledger-domain.md`, `docs/Obsidian/architecture/files-exports.md`, `docs/Obsidian/architecture/observability-ops.md`, `docs/Obsidian/architecture/tags-domain.md`, `docs/Obsidian/architecture/capacity-partitions-domain.md`, `docs/Obsidian/architecture/credentials-connections-domain.md`

### Phase 1: 动词路径收敛到 actions(7.3/7.4/7.6/7.7)

#### 7.3 Sync sessions(同步会话)

- [x] `GET /api/v1/history/sessions` → `GET /api/v1/sync-sessions`
- [x] `GET /api/v1/history/sessions/<session_id>` → `GET /api/v1/sync-sessions/<session_id>`
- [x] `GET /api/v1/history/sessions/<session_id>/error-logs` → `GET /api/v1/sync-sessions/<session_id>/error-logs`
- [x] `POST /api/v1/history/sessions/<session_id>/cancel` → `POST /api/v1/sync-sessions/<session_id>/actions/cancel`
- [x] 调用点迁移:
  - `app/static/js/modules/services/sync_sessions_service.js`
  - `app/static/js/modules/views/history/sessions/sync-sessions.js`
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_history_sessions_contract.py`

#### 7.4 Scheduler(action 收敛)

- [x] `POST /api/v1/scheduler/jobs/<job_id>/pause` → `POST /api/v1/scheduler/jobs/<job_id>/actions/pause`
- [x] `POST /api/v1/scheduler/jobs/<job_id>/resume` → `POST /api/v1/scheduler/jobs/<job_id>/actions/resume`
- [x] `POST /api/v1/scheduler/jobs/<job_id>/run` → `POST /api/v1/scheduler/jobs/<job_id>/actions/run`
- [x] `POST /api/v1/scheduler/jobs/reload` → `POST /api/v1/scheduler/jobs/actions/reload`
- [x] 调用点迁移:
  - `app/static/js/modules/services/scheduler_service.js`
  - `app/static/js/modules/views/admin/scheduler/index.js`
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_scheduler_contract.py`

#### 7.6 Tags bulk(action 收敛)

- [x] `POST /api/v1/tags/bulk/assign` → `POST /api/v1/tags/bulk/actions/assign`
- [x] `POST /api/v1/tags/bulk/remove` → `POST /api/v1/tags/bulk/actions/remove`
- [x] `POST /api/v1/tags/bulk/remove-all` → `POST /api/v1/tags/bulk/actions/remove-all`
- [x] 确认保留不变: `GET /api/v1/tags/bulk/instances`, `GET /api/v1/tags/bulk/tags`, `POST /api/v1/tags/bulk/instance-tags`
- [x] 调用点迁移:
  - `app/static/js/modules/services/tag_management_service.js`
  - `app/static/js/modules/views/tags/index.js`
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_tags_bulk_contract.py`

#### 7.7 Cache(action 收敛)

- [x] `POST /api/v1/cache/clear/user` → `POST /api/v1/cache/actions/clear-user`
- [x] `POST /api/v1/cache/clear/instance` → `POST /api/v1/cache/actions/clear-instance`
- [x] `POST /api/v1/cache/clear/all` → `POST /api/v1/cache/actions/clear-all`
- [x] `POST /api/v1/cache/classification/clear` → `POST /api/v1/cache/actions/clear-classification`
- [x] `POST /api/v1/cache/classification/clear/<db_type>` → `POST /api/v1/cache/actions/clear-classification`(payload 可选 `db_type`)
- [x] 确认保留不变: `GET /api/v1/cache/stats`, `GET /api/v1/cache/classification/stats`
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_cache_contract.py`

### Phase 2: 资源形态收敛(7.1/7.2)

#### 7.1 Health(命名重复)

- [x] `GET /api/v1/health/health` → `GET /api/v1/health`
- [x] 调用点迁移:
  - `app/static/js/modules/services/partition_service.js`
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_health_ping_contract.py`

#### 7.2 Logs(统一日志)

- [x] `GET /api/v1/history/logs/list` → `GET /api/v1/logs`
- [x] `GET /api/v1/history/logs/search` → `GET /api/v1/logs`
- [x] `GET /api/v1/history/logs/detail/<log_id>` → `GET /api/v1/logs/<log_id>`
- [x] `GET /api/v1/history/logs/statistics` → `GET /api/v1/logs/statistics`
- [x] `GET /api/v1/history/logs/modules` → `GET /api/v1/logs/modules`
- [x] 调用点迁移:
  - `app/static/js/modules/services/logs_service.js`
  - `app/static/js/modules/views/history/logs/logs.js`
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_history_logs_contract.py`

### Phase 3: 高 churn 的 base path 调整(7.5/7.8/7.9/7.11)

#### 7.5 Partitions(resource 命名 + action 收敛)

- [x] `GET /api/v1/partition/partitions` → `GET /api/v1/partitions`
- [x] `POST /api/v1/partition/create` → `POST /api/v1/partitions`
- [x] `POST /api/v1/partition/cleanup` → `POST /api/v1/partitions/actions/cleanup`
- [x] `GET /api/v1/partition/info` → `GET /api/v1/partitions/info`
- [x] `GET /api/v1/partition/status` → `GET /api/v1/partitions/status`
- [x] `GET /api/v1/partition/statistics` → `GET /api/v1/partitions/statistics`
- [x] `GET /api/v1/partition/aggregations/core-metrics` → `GET /api/v1/partitions/core-metrics`
- [x] 调用点迁移:
  - `app/static/js/modules/services/partition_service.js`
  - `app/static/js/modules/views/admin/partitions/partition-list.js`
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_partition_contract.py`

#### 7.8 Accounts: 顶层资源(读模型迁移)

- [x] 确认保留不变: `GET /api/v1/accounts/statistics*`
- [x] 确认保留不变: `POST /api/v1/accounts/actions/sync*`
- [x] 确认保留不变: `/api/v1/accounts/classifications/*`
- [x] `GET /api/v1/instances/<instance_id>/accounts` → `GET /api/v1/accounts/ledgers?instance_id=<instance_id>`
- [x] `GET /api/v1/instances/<instance_id>/accounts/<account_id>/permissions` → `GET /api/v1/accounts/ledgers/<account_id>/permissions`
- [x] `GET /api/v1/instances/<instance_id>/accounts/<account_id>/change-history` → `GET /api/v1/accounts/ledgers/<account_id>/change-history`
- [x] 补齐顶层 change-history(如尚未实现): `GET /api/v1/accounts/ledgers/<account_id>/change-history`
- [x] 调用点迁移:
  - `app/templates/accounts/ledgers.html`
  - `app/static/js/modules/views/accounts/ledgers.js`
  - `app/static/js/modules/views/instances/detail.js`
  - `app/static/js/modules/services/instance_management_service.js`
  - `app/static/js/modules/services/permission_service.js`
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_instances_contract.py`

#### 7.9 Databases: 顶层资源(sizes/tables sizes 迁移)

- [x] 确认保留不变: `GET /api/v1/databases/ledgers`
- [x] `GET /api/v1/databases/ledgers` 支持 `instance_id` query 过滤(含 export)
- [x] `GET /api/v1/instances/<instance_id>/databases/sizes` → `GET /api/v1/databases/sizes?instance_id=<instance_id>`
- [x] `GET /api/v1/instances/<instance_id>/databases/<database_name>/tables/sizes` → `GET /api/v1/databases/<database_id>/tables/sizes`
- [x] `POST /api/v1/instances/<instance_id>/databases/<database_name>/tables/sizes/actions/refresh` → `POST /api/v1/databases/<database_id>/tables/sizes/actions/refresh`
- [x] 确认保留不变: `POST /api/v1/instances/<instance_id>/actions/sync-capacity`
- [x] 调用点迁移:
  - `app/static/js/modules/views/instances/detail.js`
  - `app/static/js/modules/services/instance_management_service.js`
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_instances_contract.py`

#### 7.11 Exports/templates(现 files) 下沉

- [x] `GET /api/v1/files/account-export` → `GET /api/v1/accounts/ledgers/export`
- [x] `GET /api/v1/files/instance-export` → `GET /api/v1/instances/export`
- [x] `GET /api/v1/files/database-ledger-export` → `GET /api/v1/databases/ledgers/export`
- [x] `GET /api/v1/files/template-download` → `GET /api/v1/instances/import-template`
- [x] 调用点迁移:
  - `app/templates/databases/ledgers.html`
  - `app/templates/instances/list.html`
  - `app/templates/instances/modals/batch-create-modal.html`
  - `app/templates/accounts/ledgers.html`
  - `app/static/js/modules/views/accounts/ledgers.js`
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_files_contract.py`

### Phase 4: method 收敛(delete/restore)(7.10) + 清理

- [x] `POST /api/v1/instances/<instance_id>/delete` → `DELETE /api/v1/instances/<instance_id>`
- [x] `POST /api/v1/instances/<instance_id>/restore` → `POST /api/v1/instances/<instance_id>/actions/restore`
- [x] `POST /api/v1/tags/<tag_id>/delete` → `DELETE /api/v1/tags/<tag_id>`
- [x] `POST /api/v1/credentials/<credential_id>/delete` → `DELETE /api/v1/credentials/<credential_id>`
- [ ] (可选) batch 操作收敛到 `/actions/*`: instances `batch-create/batch-delete` 等
- [x] 清理: 删除所有已替换的旧 routes/旧调用点(无 alias), 并同步更新 `docs/Obsidian/architecture/layer-first-api-restructure.md#8`(如调用点发生漂移)
- [x] 合同测试同步: `tests/unit/routes/test_api_v1_instances_contract.py`, `tests/unit/routes/test_api_v1_tags_contract.py`, `tests/unit/routes/test_api_v1_credentials_contract.py`

### Phase 5: 门禁与验证(每次合并 PR 都应复核)

- [x] OpenAPI schema 校验: `python scripts/dev/openapi/export_openapi.py --check`
- [x] 单元测试: `uv run pytest -m unit`
- [x] Ruff: `ruff check app`
- [x] 类型检查: `make typecheck`

## 变更记录

- 2026-01-07: 初始化 plan/progress, 完成 `docs/Obsidian/architecture/layer-first-api-restructure.md` 的 layer-first + 顶层资源(accounts/databases)设计更新并同步索引入口.
- 2026-01-07: 补齐 databases ledgers 的 `instance_id` query 过滤(含 export), 完成 Phase 5 门禁校验(OpenAPI/unit/ruff/typecheck).
