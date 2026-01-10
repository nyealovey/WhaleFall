# 025 api v1 accounts instances databases path refactor plan

> 状态: Draft
> 负责人: team
> 创建: 2026-01-07
> 更新: 2026-01-07
> 范围: `/api/v1` 下 `accounts`/`instances`(含连接相关子路由)/`databases` 的路径命名与层级收敛, 全局 no-alias 直接 breaking
> 关联:
> - `../../reports/2026-01-07-api-v1-accounts-instances-databases-path-audit.md`
> - `../../Obsidian/standards/backend/layer/api-layer-standards.md`
> - `../../Obsidian/standards/backend/action-endpoint-failure-semantics.md`
> - `../../Obsidian/standards/doc/api-contract-markdown-standards.md`
> - `./024-layer-first-api-restructure-plan.md`

---

## 动机与范围

动机:

- 现有部分路径在 "资源归属" 与 "层级语义" 上不可推断, 例如:
  - `POST /api/v1/accounts/actions/sync` 实际是对 instance 做同步, 但挂在 accounts 下并要求 body 传 `instance_id`.
  - `GET /api/v1/instances/status/{instance_id}` 把 id 放在末尾, 与 `/{instance_id}` 风格不一致.
- 部分路径仍是动词型段(如 `export`, `batch-create`), 与 API layer standards 的 "URI 表示资源" 原则不一致.

范围:

- 仅处理以下 namespace 的路径与调用点:
  - `app/api/v1/namespaces/accounts.py`
  - `app/api/v1/namespaces/instances.py`
  - `app/api/v1/namespaces/instances_connections.py`
  - `app/api/v1/namespaces/databases.py`
- 同步更新:
  - 前端调用点: `app/static/js/**`, `app/templates/**`
  - 契约单一真源: `docs/Obsidian/API/**-api-contract.md`
  - 相关单元测试(契约测试): `tests/unit/routes/**`

非目标:

- 不改变既有业务语义与权限规则, 仅做路径与入参表达的收敛.
- 不引入 alias/deprecated 过渡入口(全局 no-alias).
- 不在本计划中引入新的导出异步任务体系(保持现有同步下载 Response).

## 不变约束(行为/契约/性能门槛)

- 响应封套不变: `app/api/v1/models/envelope.py`, `BaseResource.success/error_message`.
- action 失败语义不变: 继续遵循 `docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md`.
- CSRF 策略不变: 写接口继续走 `@require_csrf`.
- 全局 no-alias: 路径变更不保留旧入口, 由调用方一次性迁移.

## 兼容/适配/回退策略

- 兼容策略: no-alias, 不提供旧路径兼容.
- 回退策略: git revert 对应 PR, 恢复旧路径与旧调用点.

## 分阶段计划(每阶段验收口径)

### Phase 0: 冻结清单与影响面

- 固定 Current -> Proposed 映射(以 audit 文档为准).
- 固定调用点清单(templates + JS + tests + contract canvas).

验收:

- `rg -n "/api/v1/(accounts|instances|databases)" app/static/js app/templates tests/unit/routes` 可覆盖所有需要迁移的引用点.

### Phase 1: Accounts sync 动作归属收敛到 instances

- `POST /api/v1/accounts/actions/sync-all` -> `POST /api/v1/instances/actions/sync-accounts`
- `POST /api/v1/accounts/actions/sync` -> `POST /api/v1/instances/{instance_id}/actions/sync-accounts`(instance_id 从 path 表达, body 可为空)

验收:

- 相关 contract tests 更新并通过: `tests/unit/routes/test_api_v1_accounts_sync_contract.py`
- `docs/Obsidian/canvas/accounts/accounts-api-contract.canvas` 与 `docs/Obsidian/canvas/instances/instances-api-contract.canvas` 同步更新.

### Phase 2: Instances connections 路径一致性与 action 命名明确化

- `POST /api/v1/instances/actions/test` -> `POST /api/v1/instances/actions/test-connection`
- `POST /api/v1/instances/actions/validate-params` -> `POST /api/v1/instances/actions/validate-connection-params`
- `POST /api/v1/instances/actions/batch-test` -> `POST /api/v1/instances/actions/batch-test-connections`
- `GET /api/v1/instances/status/{instance_id}` -> `GET /api/v1/instances/{instance_id}/connection-status`

验收:

- 相关 contract tests 更新并通过: `tests/unit/routes/test_api_v1_connections_contract.py`
- instances contract canvas 同步更新.

### Phase 3: Databases capacity-trend 移除

- 移除 `GET /api/v1/databases/{database_id}/capacity-trend`（no-alias，不保留旧路径）

验收:

- 相关 contract tests 更新并通过: `tests/unit/routes/test_api_v1_databases_ledgers_contract.py`

### Phase 4: 动词路径收敛(可选, 但建议一次性做完)

- Instances:
  - `GET /api/v1/instances/export` -> `GET /api/v1/instances/exports`
  - `GET /api/v1/instances/import-template` -> `GET /api/v1/instances/imports/template`
  - `POST /api/v1/instances/batch-create` -> `POST /api/v1/instances/actions/batch-create`
  - `POST /api/v1/instances/batch-delete` -> `POST /api/v1/instances/actions/batch-delete`
- Accounts:
  - `GET /api/v1/accounts/ledgers/export` -> `GET /api/v1/accounts/ledgers/exports`
- Databases:
  - `GET /api/v1/databases/ledgers/export` -> `GET /api/v1/databases/ledgers/exports`

验收:

- 前端所有调用点与 templates 更新完成, 页面可用.
- OpenAPI/contract canvas 校验通过(见下).

## 风险与回滚

- 风险: no-alias 会导致前端/脚本在发布窗口内必须同步迁移.
  - 缓解: 每个 Phase 都更新 contract tests + contract canvas, 并在合并前跑 OpenAPI check.
- 回滚: git revert 对应 PR(一次性回滚到旧路径).

## 验证与门禁

- OpenAPI schema: `uv run python scripts/dev/openapi/export_openapi.py --check`
- Contract 覆盖率: `uv run python scripts/dev/openapi/export_api_contract_canvas.py --check`
- 单元测试: `uv run pytest -m unit`
- Ruff: `ruff check app`
- 类型检查: `make typecheck`
