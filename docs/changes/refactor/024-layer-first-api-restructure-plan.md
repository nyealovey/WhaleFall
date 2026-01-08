# 024 layer first api restructure plan

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-07
> 更新: 2026-01-07
> 范围: API v1 路径收敛(health/logs/sync-sessions/scheduler/partitions/tags bulk/cache/instances/accounts/databases/files exports), layer-first 目录落点
> 关联:
> - `docs/architecture/layer-first-api-restructure.md`
> - `docs/Obsidian/standards/backend/api-naming-standards.md`
> - `docs/Obsidian/standards/changes-standards.md`
> - `docs/Obsidian/standards/documentation-standards.md`

---

## 动机与范围

目标(以 `docs/architecture/layer-first-api-restructure.md` 为单一真源):

- 目录结构保持 layer-first(不引入 `app/domains/**`), 同时收敛 API v1 的路径与 action 口径.
- 对外路径按命名规范收敛(去 `list/search/detail` 视图式路径, 动词统一放 `/actions/*`), 且全局 no-alias.
- 核心资源入口调整:
  - `accounts`/`databases` 以顶层入口暴露(使用 `InstanceAccount.id` / `InstanceDatabase.id` 作为稳定 ID, 用 query `instance_id` 表达 scope).
  - `instances` 保持实例管理与实例级 actions(restore/sync-capacity 等).
- exports/templates 下沉到 owning modules, 不保留 `/api/v1/files/*`.

覆盖范围(本计划关注的对外路径变化):

- 7.1 Health: `/health/health` → `/health`
- 7.2 Logs: `/history/logs/*` → `/logs/*`(list/search 合并, detail 资源化)
- 7.3 Sync sessions: `/history/sessions/*` → `/sync-sessions/*`(cancel → actions/cancel)
- 7.4 Scheduler: job 动作收敛到 `/actions/*`
- 7.5 Partitions: `/partition/*` → `/partitions/*`(create/cleanup 语义与 actions 收敛)
- 7.6 Tags bulk: bulk 动作收敛到 `/actions/*`
- 7.7 Cache: clear 动作收敛到 `/actions/*`(classification clear 的 db_type 从 path 变为 payload 可选字段)
- 7.8 Accounts: `instances/<instance_id>/accounts/*` → `accounts/ledgers*`(顶层入口 + change-history 顶层化)
- 7.9 Databases: `instances/<instance_id>/databases/sizes` 与 tables sizes 迁移到 databases 顶层
- 7.10 Instances/Tags/Credentials: delete/restore 收敛到标准 method 或 `/actions/*`
- 7.11 Exports/templates: `/files/*` 下沉到 `instances/accounts/databases/logs` 等 owning modules

非目标:

- 不改变数据模型的聚合根事实: `Instance` 仍是聚合根, accounts/databases 仍依附于 instance.
- 不引入 alias/deprecated 过渡入口(全局 no-alias).
- 不在本计划中新增全新的写接口/资源体系(例如新增 `POST /databases`), 仅按现有能力做路径与语义收敛.

## 不变约束(行为/契约/性能门槛)

- API response envelope 不变: 沿用 `app/api/v1/models/envelope.py` 与 `BaseResource` 口径.
- 权限体系与动作收敛口径不变: 继续使用 `api_permission_required` 与 `/actions/*` 规则.
- 全局 no-alias: 发生路径变更时不保留旧路径入口(调用方必须同步迁移).

## 兼容/适配/回退策略

- 兼容策略: 全局 no-alias(不保留旧入口, 不做 deprecated/alias).
- 回退策略: 仅允许通过 git revert 回滚到旧实现; 若短期必须恢复旧入口, 需要新增明确的“下线日期/版本窗口”并记录在 progress.

## 分层边界(依赖方向/禁止项)

- 依赖方向: `app/api/**`/`app/routes/**`/`app/tasks/**` → `app/services/**` → `app/repositories/**` → `app/models/**`(以及 `schemas/types`).
- API namespaces 只负责 HTTP 层: 入参解析/权限/序列化/错误映射; 业务逻辑落在 services.
- 顶层资源路由的 “ID 解析/归属映射”(例如 `database_id -> (instance_id, database_name)`) 允许在 service 层集中实现, 避免散落在多个 resource.

## 分阶段计划(每阶段验收口径)

### Phase 0: 方案与清单冻结

目标: 固定设计口径与迁移清单, 避免边实现边漂移.

- 更新架构提案: `docs/architecture/layer-first-api-restructure.md`(已完成)
- 建立 `plan/progress` 追踪: `docs/changes/refactor/024-layer-first-api-restructure-{plan,progress}.md`
- 固定前端调用点清单(用于后续迁移复核): 以 `docs/architecture/layer-first-api-restructure.md#8` 为准

验收:

- `docs/architecture/layer-first-api-restructure.md` 中 Breaking changes / 7.* 映射一致, 且索引入口不缺失.

### Phase 1: 动词路径收敛到 actions(低风险)

目标: 收敛动词型 endpoint, 优先用 `/actions/*` 表达, 降低后续 base path 变更的耦合成本.

- 7.3 Sync sessions: `cancel` → `.../actions/cancel`(并同时完成 history → sync-sessions 的路径迁移)
- 7.4 Scheduler: job pause/resume/run/reload 全部迁移到 `/actions/*`
- 7.6 Tags bulk: assign/remove/remove-all 迁移到 `/bulk/actions/*`
- 7.7 Cache: clear* 与 classification/clear* 迁移到 `/actions/*`(classification clear 的 `db_type` 从 path 改为 payload 可选字段)

验收:

- OpenAPI export 可生成, 且上述 actions 路径与 `docs/architecture/layer-first-api-restructure.md#7` 一致.
- UI 操作入口可用(必要时只做最小回归页面).

### Phase 2: 资源形态收敛(list/search/detail 合并)

目标: 收敛历史“视图式”路径, 统一为集合 GET + query + 单体 GET.

- 7.1 Health: `/health/health` 去重为 `/health`
- 7.2 Logs: `/history/logs/{list,search,detail}` 合并为 `/logs` 与 `/logs/<log_id>`, 保留 statistics/modules 语义仅调整 base path

验收:

- Logs 列表/筛选/详情/统计/模块均可用, 且 `/history/logs/*` 不再存在.
- Health 调用方全部迁移到 `/health`.

### Phase 3: 高 churn 的 base path 调整(核心入口变更)

目标: 以 `InstanceAccount.id` 为稳定 ID, 完成顶层读模型的完整闭环.

- 7.5 Partitions: `/partition/*` → `/partitions/*`(create/cleanup/actions 收敛)
- 7.8 Accounts: `instances/<instance_id>/accounts/*` → `accounts/ledgers*`(含 change-history 顶层化)
- 7.9 Databases: `instances/<instance_id>/databases/sizes` 与 tables sizes 迁移到 databases 顶层:
  - `GET /databases/sizes?instance_id=<instance_id>`
  - `GET/POST /databases/<database_id>/tables/sizes*`
- 7.11 Exports/templates: `/files/*` 下沉到 owning modules, 与顶层资源对齐

约束:

- `databases/sizes` 的 `instance_id` 建议为必填, 避免全库扫描(如需全局视图, 另起设计).

验收:

- OpenAPI export 可生成且路由集合与 `docs/architecture/layer-first-api-restructure.md` 一致.
- 关键页面/JS 可完成迁移并通过最小回归(见 progress checklist).

### Phase 4: method 收敛(delete/restore) + 清理

目标: 对 delete/restore 做 method/路径语义收敛, 并删除所有被替换的旧入口.

- 7.10 Instances/Tags/Credentials:
  - instances delete: `POST .../delete` → `DELETE ...`
  - instances restore: `POST .../restore` → `POST .../actions/restore`
  - tags/credentials delete: `POST .../delete` → `DELETE ...`

验收:

- OpenAPI schema 校验: `python scripts/dev/openapi/export_openapi.py --check`
- 单元测试: `uv run pytest -m unit`
- Ruff: `ruff check app`
- 类型检查: `make typecheck`

## 风险与回滚

- 风险: no-alias 带来前端/外部调用方同步改动成本.
  - 缓解: 以 progress 清单锁定迁移点, 每阶段合并都更新 progress 并跑 OpenAPI check.
  - 回滚: git revert 对应 PR; 或恢复旧 routes(仅限短期, 且必须写清下线窗口).
- 风险: `databases/sizes` 若允许缺省 `instance_id` 可能引发性能问题.
  - 缓解: 强制 `instance_id` 必填, 或在服务层做硬限制/分页.

## 验证与门禁

- OpenAPI schema 校验: `python scripts/dev/openapi/export_openapi.py --check`
- 单元测试: `uv run pytest -m unit`
- Ruff: `ruff check app`
- 类型检查: `make typecheck`
