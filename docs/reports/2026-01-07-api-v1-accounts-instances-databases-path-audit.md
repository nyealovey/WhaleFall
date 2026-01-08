# API v1 accounts/instances/databases 路径重构建议

> 状态: Draft
> 负责人: team
> 创建: 2026-01-07
> 更新: 2026-01-07
> 范围: `/api/v1` 下 `accounts`, `instances`(含连接测试子路由), `databases` 三个 namespace 的路径命名与层级
> 关联:
> - `docs/Obsidian/standards/backend/api-naming-standards.md`
> - `docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md`
> - `docs/Obsidian/standards/backend/api-contract-canvas-standards.md`
> - `docs/architecture/layer-first-api-restructure.md`
> - `docs/changes/refactor/024-layer-first-api-restructure-plan.md`

## 摘要结论

- `/api/v1/accounts/actions/sync-all` 与 `/api/v1/accounts/actions/sync` 的资源归属不清: 实际是对 instance 做同步, 但挂在 accounts 下, 导致调用方难以从路径推断语义与 scope. 参考 `app/api/v1/namespaces/accounts.py:613`, `app/api/v1/namespaces/accounts.py:656`.
- `/api/v1/instances/<id>/actions/sync-capacity` 符合现行 actions 规范, 但 action 名 `sync-capacity` 语义偏泛, 建议强化为 `sync-database-capacity`(或 `sync-database-sizes`)以降低误解成本. 参考 `app/api/v1/namespaces/instances.py:743`.
- `instances` 下的连接相关接口存在路径形态不一致: `GET /api/v1/instances/status/<instance_id>` 把 id 放在末尾, 与其它 `/<instance_id>/...` 模式不一致, 且 `/actions/test` 等 action 名不够自描述. 参考 `app/api/v1/namespaces/instances_connections.py:314`, `app/api/v1/namespaces/instances_connections.py:449`.
- `databases` 的容量走势接口被挂在 `ledgers` 子资源下: `GET /api/v1/databases/ledgers/<database_id>/capacity-trend` 破坏了层级语义, 建议迁移到 `GET /api/v1/databases/<database_id>/capacity-trend`. 参考 `app/api/v1/namespaces/databases.py:403`.
- 多个下载/批量操作仍使用动词型路径(如 `/export`, `/batch-create`), 建议统一收敛为名词子资源或 `/actions/*` 形式, 以对齐 `api-naming-standards.md` 的 "URI 表示资源" 原则.

## 范围与方法

### 范围

- API 范围: 仅覆盖 `app/api/v1/namespaces/accounts.py`, `app/api/v1/namespaces/instances.py`, `app/api/v1/namespaces/instances_connections.py`, `app/api/v1/namespaces/databases.py` 对外暴露的路径.
- 调用方范围: 仅梳理仓库内前端调用点(templates + `app/static/js/**`), 不包含外部系统调用.

### 方法

- 对照 `docs/Obsidian/standards/backend/api-naming-standards.md` 的规则 3.2/3.4/3.5, 针对 "资源命名, 层级, actions, 动词路径" 做静态审计.
- 通过 `rg` 定位前端调用点, 标记迁移影响面, 作为后续实施 checklist.
- 额外记录当前存在的兼容/兜底分支(重点关注 `or`/fallback), 以便在路径重构时同步评估清理窗口.

## 发现清单(按优先级)

### P0: 资源归属与层级语义问题

- 位置: `app/api/v1/namespaces/accounts.py:613`
  - 类型: 设计/归属
  - 描述: `POST /api/v1/accounts/actions/sync-all` 从语义上是 "对实例集合触发同步", 但路径归属到 accounts, 且返回 `session_id` 更像 job/session 资源创建.
  - 建议: 将入口迁移到 instances(集合 action)或 sync-sessions(资源化). 推荐: `POST /api/v1/instances/actions/sync-accounts`.
- 位置: `app/api/v1/namespaces/accounts.py:656`
  - 类型: 设计/归属
  - 描述: `POST /api/v1/accounts/actions/sync` 需要 payload `instance_id`, 本质是 instance action, 但路径挂在 accounts 下, 且与 `POST /api/v1/instances/{instance_id}/actions/sync-capacity` 不对称.
  - 建议: 迁移为 `POST /api/v1/instances/{instance_id}/actions/sync-accounts`, 并将 `instance_id` 从 path 表达(不再放在 body).
- 位置: `app/api/v1/namespaces/databases.py:403`
  - 类型: 设计/层级
  - 描述: `GET /api/v1/databases/ledgers/{database_id}/capacity-trend` 把 database_id 放在 ledgers 子资源下, 容易被误解为 "ledger item 的子资源" 而非 "database 的子资源".
  - 建议: 迁移为 `GET /api/v1/databases/{database_id}/capacity-trend`, 保持 `ledgers` 仅承载台账集合视图.
- 位置: `app/api/v1/namespaces/instances_connections.py:449`
  - 类型: 设计/一致性
  - 描述: `GET /api/v1/instances/status/{instance_id}` 把资源 id 放在末尾, 与 `GET/PUT/DELETE /api/v1/instances/{instance_id}` 的路径风格不一致.
  - 建议: 迁移为 `GET /api/v1/instances/{instance_id}/connection-status`(或 `.../status`), 保持 id 前置并表达具体语义.

### P1: 动词路径与 actions 约定不一致

- 位置: `app/api/v1/namespaces/instances.py:890`
  - 类型: 命名/规范
  - 描述: `POST /api/v1/instances/batch-create` 属于非 CRUD 动作, 但未使用 `/actions/*`, 且包含动词 create.
  - 建议: 迁移为 `POST /api/v1/instances/actions/batch-create` 或资源化为 `POST /api/v1/instance-batches`.
- 位置: `app/api/v1/namespaces/instances.py:937`
  - 类型: 命名/规范
  - 描述: `POST /api/v1/instances/batch-delete` 同上, 且 delete 动词应优先用 `DELETE` 或 `/actions/*`.
  - 建议: 迁移为 `POST /api/v1/instances/actions/batch-delete`(批量删除通常仍用 POST 以避免 DELETE body 兼容性问题).
- 位置: `app/api/v1/namespaces/instances.py:583`
  - 类型: 命名/规范
  - 描述: `GET /api/v1/instances/export` 使用动词型路径段 `export`.
  - 建议: 若继续使用下载直出模式, 推荐改为名词子资源 `GET /api/v1/instances/exports`.
- 位置: `app/api/v1/namespaces/accounts.py:472`
  - 类型: 命名/规范
  - 描述: `GET /api/v1/accounts/ledgers/export` 使用动词型路径段 `export`.
  - 建议: 统一改为 `GET /api/v1/accounts/ledgers/exports`.
- 位置: `app/api/v1/namespaces/databases.py:320`
  - 类型: 命名/规范
  - 描述: `GET /api/v1/databases/ledgers/export` 使用动词型路径段 `export`.
  - 建议: 统一改为 `GET /api/v1/databases/ledgers/exports`.
- 位置: `app/api/v1/namespaces/instances_connections.py:314`
  - 类型: 命名/可读性
  - 描述: `POST /api/v1/instances/actions/test` action 名过短, 难以从路径推断是 "连接测试" 还是其它测试.
  - 建议: 改为 `POST /api/v1/instances/actions/test-connection`.
- 位置: `app/api/v1/namespaces/instances_connections.py:362`
  - 类型: 命名/可读性
  - 描述: `POST /api/v1/instances/actions/validate-params` action 名未包含 domain, 与其它模块潜在冲突.
  - 建议: 改为 `POST /api/v1/instances/actions/validate-connection-params`.
- 位置: `app/api/v1/namespaces/instances_connections.py:395`
  - 类型: 命名/可读性
  - 描述: `POST /api/v1/instances/actions/batch-test` 同上, action 名不够自描述.
  - 建议: 改为 `POST /api/v1/instances/actions/batch-test-connections`.

### P2: 兼容/分页等次要一致性问题(非路径, 但建议顺手收敛)

- 位置: `app/api/v1/namespaces/databases.py:336`
  - 类型: 兼容
  - 描述: export 路径对 `tags` 同时支持 query 重复 key 与逗号分隔字符串(`tags=a&tags=b` vs `tags=a,b`). 这类兼容逻辑目前只存在于 export, 与 list(ledgers) 行为不一致.
  - 建议: 统一 tags 解析策略(建议以重复 key 作为 canonical, 逗号分隔作为迁移期 alias), 并在迁移窗口结束后删除逗号分隔兼容.
- 位置: `app/api/v1/namespaces/databases.py:276`
  - 类型: 兼容/一致性
  - 描述: `/databases/ledgers` 使用 `page` + `page_size`, 但响应字段使用 `per_page`/`limit` 等不同命名, 易造成调用方误读.
  - 建议: 将响应字段统一为 `page` + `page_size`(或至少在 OpenAPI/contract 中固定并解释), 避免 "limit/per_page/page_size" 三套名词并存.

## 推荐的路径重构方案(Current -> Proposed)

说明:

- 本节只列出建议变更的 endpoint, 不维护全量 endpoint 表(全量清单以 `docs/Obsidian/canvas/**-api-contract.canvas` 与 OpenAPI 为准).
- 若采用全局 no-alias(见 `docs/architecture/layer-first-api-restructure.md`), 需要后端与前端在同一发布窗口完成迁移.

### Accounts

1) 同步动作从 accounts 下迁出(推荐归属 instances):

- Current: `POST /api/v1/accounts/actions/sync-all`
  - Proposed: `POST /api/v1/instances/actions/sync-accounts`
  - 语义: 默认同步所有 active instances; 如需扩展, 可在 payload 中增加 `instance_ids` 以支持批量.
- Current: `POST /api/v1/accounts/actions/sync`(payload: `instance_id`)
  - Proposed: `POST /api/v1/instances/{instance_id}/actions/sync-accounts`
  - 语义: 同步指定 instance 的 accounts; `instance_id` 从 path 表达, body 可为空.

2) 导出路径动词收敛为名词子资源(可选, P1):

- Current: `GET /api/v1/accounts/ledgers/export`
  - Proposed: `GET /api/v1/accounts/ledgers/exports`

### Instances

1) 批量操作收敛到 actions:

- Current: `POST /api/v1/instances/batch-create`
  - Proposed: `POST /api/v1/instances/actions/batch-create`
- Current: `POST /api/v1/instances/batch-delete`
  - Proposed: `POST /api/v1/instances/actions/batch-delete`

2) 下载类路径收敛为名词子资源:

- Current: `GET /api/v1/instances/export`
  - Proposed: `GET /api/v1/instances/exports`
- Current: `GET /api/v1/instances/import-template`
  - Proposed: `GET /api/v1/instances/imports/template`

3) 连接相关 actions 命名明确化 + status 形态统一:

- Current: `POST /api/v1/instances/actions/test`
  - Proposed: `POST /api/v1/instances/actions/test-connection`
- Current: `POST /api/v1/instances/actions/validate-params`
  - Proposed: `POST /api/v1/instances/actions/validate-connection-params`
- Current: `POST /api/v1/instances/actions/batch-test`
  - Proposed: `POST /api/v1/instances/actions/batch-test-connections`
- Current: `GET /api/v1/instances/status/{instance_id}`
  - Proposed: `GET /api/v1/instances/{instance_id}/connection-status`

4) `sync-capacity` 的命名建议(可选, 针对歧义):

- Current: `POST /api/v1/instances/{instance_id}/actions/sync-capacity`
  - Proposed: `POST /api/v1/instances/{instance_id}/actions/sync-database-capacity`
  - 备注: 该改动仅提升可读性, 需要同步更新前端调用与 OpenAPI/contract.

### Databases

1) 容量走势归属到 database 资源:

- Current: `GET /api/v1/databases/ledgers/{database_id}/capacity-trend`
  - Proposed: `GET /api/v1/databases/{database_id}/capacity-trend`

2) 导出路径动词收敛为名词子资源(可选, P1):

- Current: `GET /api/v1/databases/ledgers/export`
  - Proposed: `GET /api/v1/databases/ledgers/exports`

## 迁移影响面(仓库内调用点)

### 前端/模板

- Accounts sync:
  - `app/templates/instances/detail.html:13` 使用 `data-sync-accounts-url="/api/v1/accounts/actions/sync"`.
  - `app/static/js/modules/services/instance_management_service.js:67` 默认使用 `/api/v1/accounts/actions/sync`.
  - `app/static/js/modules/services/instance_management_service.js:79` 使用 `/api/v1/accounts/actions/sync-all`.
- Instances export/import/batch:
  - `app/templates/instances/list.html:32` 使用 `/api/v1/instances/export`.
  - `app/templates/instances/modals/batch-create-modal.html:8` 使用 `/api/v1/instances/import-template`.
  - `app/static/js/modules/services/instance_management_service.js:128` 使用 `/api/v1/instances/batch-delete`.
  - `app/static/js/modules/services/instance_management_service.js:137` 使用 `/api/v1/instances/batch-create`.
- Connections:
  - `app/static/js/modules/services/connection_service.js:51` 使用 `/api/v1/instances/actions/test`.
  - `app/static/js/modules/services/connection_service.js:73` 使用 `/api/v1/instances/actions/validate-params`.
  - `app/static/js/modules/services/connection_service.js:84` 使用 `/api/v1/instances/actions/batch-test`.
  - `app/static/js/modules/services/connection_service.js:100` 使用 `/api/v1/instances/status/{instance_id}`.
- Exports:
  - `app/templates/accounts/ledgers.html:27` 与 `app/static/js/modules/views/accounts/ledgers.js:56` 使用 `/api/v1/accounts/ledgers/export`.
  - `app/templates/databases/ledgers.html:20` 使用 `/api/v1/databases/ledgers/export`.
  - `app/static/js/modules/services/database_ledger_service.js:64` 使用 `/api/v1/databases/ledgers` 与 `/api/v1/databases/ledgers/{database_id}/capacity-trend`.

## 兼容/适配/回退策略(路径层)

推荐默认策略: 全局 no-alias(不保留旧路径), 原因与约束见:

- `docs/architecture/layer-first-api-restructure.md`
- `docs/changes/refactor/024-layer-first-api-restructure-plan.md`

如必须提供迁移期 alias(不推荐), 需额外约定:

- alias 存在的截止版本/日期.
- contract canvas Notes 中标注 "deprecated" 与下线计划.
- 测试覆盖: 新旧路径同时满足最小契约测试, 避免只迁移一半.

## 验收与门禁(实施时)

- OpenAPI 校验: `uv run python scripts/dev/openapi/export_openapi.py --check`
- Contract 覆盖率: `uv run python scripts/dev/openapi/export_api_contract_canvas.py --check`
- 单测: `uv run pytest -m unit`

## 附录: 兼容/防御/回退/适配逻辑盘点(与本次路径重构强相关)

- 位置: `app/api/v1/namespaces/accounts.py:332`
  - 类型: 防御
  - 描述: query 缺省值使用 `or ""` 兜底并 `strip()`, 防止 `None` 引发异常(例如 `search = (args.get("search") or "").strip()`).
  - 建议: 保留. 该类属于输入规范化, 不应在路径重构中被误删.
- 位置: `app/api/v1/namespaces/accounts.py:283`
  - 类型: 兼容/防御
  - 描述: `_normalize_sync_result` 兼容下游结果缺少 `success/message` 字段, 使用默认值兜底.
  - 建议: 若下游 schema 已稳定, 可在 coordinator/service 层引入 schema_version 并逐步移除兜底.
- 位置: `app/api/v1/namespaces/databases.py:336`
  - 类型: 兼容
  - 描述: `tags` 同时兼容重复 query key 与逗号分隔字符串(`getlist("tags")` 为空时 fallback `split(",")`).
  - 建议: 明确 canonical 为重复 key, 在文档与 OpenAPI 中固定; 迁移期保留 fallback, 并设定删除窗口.
- 位置: `app/api/v1/namespaces/instances.py:953`
  - 类型: 防御
  - 描述: `payload = request.get_json(silent=True) or {}` 兜底空 body, 避免 `NoneType` 访问报错.
  - 建议: 保留, 但应配合 schema 校验确保必填字段缺失时返回 400.
- 位置: `app/api/v1/namespaces/instances_connections.py:338`
  - 类型: 适配
  - 描述: 同一个 endpoint(`/actions/test`) 同时承载 "测试既有实例" 与 "测试新连接", 通过 payload 是否包含 `instance_id` 做分支.
  - 建议: 若后续要进一步资源化, 可拆为 2 个 endpoint: `/instances/{instance_id}/actions/test-connection` 与 `/instances/actions/test-connection`, 并删除分支适配.
