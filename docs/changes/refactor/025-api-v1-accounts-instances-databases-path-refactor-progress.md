# 025 api v1 accounts instances databases path refactor progress

> 状态: Draft
> 负责人: team
> 创建: 2026-01-07
> 更新: 2026-01-07
> 范围: `/api/v1` 下 `accounts`/`instances`/`databases` 路径收敛, 全局 no-alias 直接 breaking
> 关联方案: `025-api-v1-accounts-instances-databases-path-refactor-plan.md`
> 关联:
> - `../../reports/2026-01-07-api-v1-accounts-instances-databases-path-audit.md`
> - `../../standards/changes-standards.md`
> - `../../standards/documentation-standards.md`

---

## 当前状态(摘要)

- 已完成现状审计与 Proposed 映射: `docs/reports/2026-01-07-api-v1-accounts-instances-databases-path-audit.md`.
- 已冻结策略: 全局 no-alias, 直接 breaking.
- 已完成: 后端路由改名, 前端调用点迁移, contract canvas + OpenAPI + unit tests 同步, 并通过门禁校验.

## Checklist

### Phase 0: 冻结清单与影响面

- [x] 输出 audit 文档: `docs/reports/2026-01-07-api-v1-accounts-instances-databases-path-audit.md`
- [x] 建立 plan/progress: `docs/changes/refactor/025-api-v1-accounts-instances-databases-path-refactor-{plan,progress}.md`
- [x] 固定仓库内调用点清单(确保无遗漏): `rg -n "/api/v1/(accounts|instances|databases)" app/static/js app/templates tests/unit/routes`

### Phase 1: Accounts sync 动作归属收敛到 instances

- [x] `POST /api/v1/accounts/actions/sync-all` -> `POST /api/v1/instances/actions/sync-accounts`
- [x] `POST /api/v1/accounts/actions/sync` -> `POST /api/v1/instances/{instance_id}/actions/sync-accounts`
- [x] 更新调用点:
  - [x] `app/static/js/modules/services/instance_management_service.js`
  - [x] `app/templates/instances/detail.html`
- [x] 更新 contract canvas:
  - [x] `docs/Obsidian/canvas/accounts/accounts-api-contract.canvas`
  - [x] `docs/Obsidian/canvas/instances/instances-api-contract.canvas`
- [x] 更新 contract tests:
  - [x] `tests/unit/routes/test_api_v1_accounts_sync_contract.py`

### Phase 2: Instances connections 路径一致性与 action 命名明确化

- [x] `POST /api/v1/instances/actions/test` -> `POST /api/v1/instances/actions/test-connection`
- [x] `POST /api/v1/instances/actions/validate-params` -> `POST /api/v1/instances/actions/validate-connection-params`
- [x] `POST /api/v1/instances/actions/batch-test` -> `POST /api/v1/instances/actions/batch-test-connections`
- [x] `GET /api/v1/instances/status/{instance_id}` -> `GET /api/v1/instances/{instance_id}/connection-status`
- [x] 更新调用点:
  - [x] `app/static/js/modules/services/connection_service.js`
- [x] 更新 contract canvas:
  - [x] `docs/Obsidian/canvas/instances/instances-api-contract.canvas`
- [x] 更新 contract tests:
  - [x] `tests/unit/routes/test_api_v1_connections_contract.py`

### Phase 3: Databases capacity-trend 层级语义修正

- [x] `GET /api/v1/databases/ledgers/{database_id}/capacity-trend` -> `GET /api/v1/databases/{database_id}/capacity-trend`
- [x] 更新调用点:
  - [x] `app/static/js/modules/services/database_ledger_service.js`
- [x] 更新 contract canvas:
  - [x] `docs/Obsidian/canvas/databases/databases-api-contract.canvas`
- [x] 更新 contract tests:
  - [x] `tests/unit/routes/test_api_v1_databases_ledgers_contract.py`

### Phase 4: 动词路径收敛(可选, 建议一次性做完)

- [x] Instances:
  - [x] `GET /api/v1/instances/export` -> `GET /api/v1/instances/exports`
  - [x] `GET /api/v1/instances/import-template` -> `GET /api/v1/instances/imports/template`
  - [x] `POST /api/v1/instances/batch-create` -> `POST /api/v1/instances/actions/batch-create`
  - [x] `POST /api/v1/instances/batch-delete` -> `POST /api/v1/instances/actions/batch-delete`
- [x] Accounts:
  - [x] `GET /api/v1/accounts/ledgers/export` -> `GET /api/v1/accounts/ledgers/exports`
- [x] Databases:
  - [x] `GET /api/v1/databases/ledgers/export` -> `GET /api/v1/databases/ledgers/exports`
- [x] 更新调用点:
  - [x] `app/templates/instances/list.html`
  - [x] `app/templates/instances/modals/batch-create-modal.html`
  - [x] `app/templates/accounts/ledgers.html`
  - [x] `app/static/js/modules/views/accounts/ledgers.js`
  - [x] `app/templates/databases/ledgers.html`
  - [x] `app/static/js/modules/services/instance_management_service.js`
- [x] 更新 contract canvas:
  - [x] `docs/Obsidian/canvas/accounts/accounts-api-contract.canvas`
  - [x] `docs/Obsidian/canvas/instances/instances-api-contract.canvas`
  - [x] `docs/Obsidian/canvas/databases/databases-api-contract.canvas`

### Phase 5: 门禁与验证(每次合并 PR 都应复核)

- [x] OpenAPI schema 校验: `uv run python scripts/dev/openapi/export_openapi.py --check`
- [x] Contract 覆盖率: `uv run python scripts/dev/openapi/export_api_contract_canvas.py --check`
- [x] 单元测试: `uv run pytest -m unit`
- [x] Ruff: `uv run ruff check app`
- [x] 类型检查: `make typecheck`

## 变更记录

- 2026-01-07: 输出 audit 文档并建立 025 plan/progress, 确认 no-alias 直接 breaking.
- 2026-01-07: 完成 Phase 0-5 路径重构与门禁校验, 并同步 contract canvas + unit tests.
