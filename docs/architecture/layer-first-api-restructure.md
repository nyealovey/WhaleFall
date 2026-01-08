# Layer-first API/Directory Restructure Proposal

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-28
> 更新: 2026-01-07
> 范围: `app/api/v1/**` 对外 API 路径, 以及后端目录结构(层优先)
> 关联:
> - `docs/Obsidian/standards/backend/api-naming-standards.md`
> - `docs/changes/refactor/004-flask-restx-openapi-migration-plan.md`
> - `docs/reference/api/api-routes-documentation.md`

## 1. 背景与问题

当前仓库已经具备明显的"按域拆服务"雏形(例如 `app/services/instances/`, `app/services/tags/`), 但 API v1 的 namespace 是"平铺式模块列表"(例如 `files`, `health`, `cache` 与 `instances`, `accounts` 同一层级). 这会带来两个评估层面的混乱:

- 认知混乱: 调用方很难区分哪些是核心业务域, 哪些是平台能力/运维能力, 哪些是跨域交付介质(例如 export/template).
- 命名漂移: 部分 endpoint 已符合 `api-naming-standards.md`(kebab-case, actions), 但仍存在 `list/search/detail` 这类"视图式"路径, 以及多个"动词路径"未收敛到 `/actions/*`.

本文件给出一个"layer-first"方案, 用于你评估:

1) 在不引入 `app/domains/**` 的前提下, 目录结构如何保持 layer-first 并整理 API v1 的落点与依赖方向.
2) 哪些 API 路径建议修改, 以及兼容策略(统一 no-alias).

## 2. 目标 / 非目标

### 2.1 目标

- 用"层"作为主要导航维度: 目录保持 layer-first(API/Services/Repositories/Models/Tasks), "模块"作为次级维度用于命名与 ownership(例如 `instances`, `tags`, `logs`, `sync-sessions`, `scheduler`), 并为未来虚拟机相关模块预留落点.
- 收敛 API v1 路径命名: 对齐 `docs/Obsidian/standards/backend/api-naming-standards.md`.
- 给出可落地的迁移路径: 允许分模块渐进迁移, 但路径变更统一按 breaking(no-alias)评估(不保留旧入口).

### 2.2 非目标

- 不要求一次性重写所有业务 Service/Repository.
- 不强制一次性把所有历史 endpoint 变成"完美 REST": 允许先统一概念与归属, 再分阶段做路径收敛. 但凡发生路径变更, 均不提供 alias.

### 2.3 Decisions(已确认)

- 当前核心域收敛为 1 个: 数据库域(以 `instances` 为聚合根).
- `instance` 仍是聚合根: accounts/databases 在数据模型上依附 instance, 但 API v1 设计为顶层资源入口:
  - `accounts`: `/api/v1/accounts/*`(ID 使用 `InstanceAccount.id`, 全局唯一), 支持 `instance_id` 过滤/聚合.
  - `databases`: `/api/v1/databases/*`(ID 使用 `InstanceDatabase.id`, 全局唯一), 支持 `instance_id` 过滤/聚合.
  - `instances`: `/api/v1/instances/*` 继续承载实例级 CRUD 与 instance actions(restore/sync-capacity 等).
- 非核心但仍需顶层建模: `tags`, `logs`, `sync-sessions`, `scheduler`(以及后台 tasks)等更偏平台/运维/可观测/交付介质.
- 未来核心域规划: 引入虚拟机相关域(平台、虚拟机清单、虚拟机统计、虚拟机大小统计等), 与数据库域并列演进.
- `partition` base path 迁移为 `/partitions`(见 7.5).
- 全局 no-alias: 本文所有 Proposed 路径变更均不保留旧路径(无兼容别名).
- Exports 采用下沉方案(Option B), 且不保留 `/api/v1/files/*` alias(见 7.11).

### 2.4 Breaking changes(no alias, global)

说明: 因为已确认全局 no-alias, 本表仅列出主要的 base path/高影响变更. 细节映射见 7.*.

| Current | Proposed | Notes |
|---|---|---|
| `/api/v1/health/health` | `/api/v1/health` | 见 7.1. |
| `/api/v1/history/logs/*` | `/api/v1/logs/*` | 见 7.2. |
| `/api/v1/history/sessions/*` | `/api/v1/sync-sessions/*` | 见 7.3. |
| `/api/v1/scheduler/jobs/<job_id>/(pause|resume|run)` | `/api/v1/scheduler/jobs/<job_id>/actions/*` | 见 7.4. |
| `/api/v1/scheduler/jobs/reload` | `/api/v1/scheduler/jobs/actions/reload` | 见 7.4. |
| `/api/v1/partition/*` | `/api/v1/partitions/*` | 见 7.5. |
| `/api/v1/tags/bulk/(assign|remove|remove-all)` | `/api/v1/tags/bulk/actions/*` | 见 7.6. |
| `/api/v1/cache/clear/*` | `/api/v1/cache/actions/*` | 见 7.7. |
| `/api/v1/instances/<instance_id>/accounts/*` | `/api/v1/accounts/ledgers*` | 见 7.8.1. |
| `/api/v1/instances/<instance_id>/databases/sizes` | `/api/v1/databases/sizes` | 见 7.9.2. |
| `/api/v1/instances/<instance_id>/databases/<database_name>/tables/sizes*` | `/api/v1/databases/<database_id>/tables/sizes*` | 见 7.9.2. |
| `/api/v1/files/*` | move into owning modules | 见 7.11. |

## 3. Layer-first 的定义(本仓库口径)

在本仓库中, layer-first 表示:

- 目录按技术分层组织: `app/api`(对外 API), `app/routes`/`app/views`(页面), `app/services`(业务编排), `app/repositories`(存储访问), `app/models`(数据模型), `app/tasks`(后台任务)等.
- 同一业务模块在不同层通过一致命名表达归属(例如 `instances`): API 层 `app/api/v1/namespaces/*`, 服务层 `app/services/*`, 存储层 `app/repositories/*`.
- 依赖方向保持单向: API/routes/tasks → services → repositories → models(以及 schemas/types). services 不反向依赖 API/routes.
- 本文仍会使用"域/模块"描述 API 资源归属与 ownership, 但不再要求映射成 `app/domains/**` 目录结构.

注意: "files" 不是业务模块, 更像交付介质(exports/downloads/templates). 本方案仍要求你为 exports/templates 明确归属: 要么作为平台能力(集中管理), 要么下沉到具体业务模块(见 7.11).

### 3.1 聚合根 vs 子资源 vs 报表视图

为了避免把"实体名"误当成"业务模块", 本文采用下面的口径:

- 聚合根(aggregate root): 业务上最稳定的主对象, 其子对象的生命周期/一致性通常由它承载. 在你的语义里, `instance` 是聚合根.
- 子资源(sub-resource): 依附于聚合根存在的对象, 例如 instance 下的 accounts, databases.
- 报表视图(reporting view): 基于某个 scope 的汇总/检索/导出/统计能力, 可以是 instance-scoped 或跨实例. 本文约定:
  - 聚合根与 API base path 不必一一对应(聚合根是领域一致性边界, API 资源是对外导航边界).
  - 当子资源具备全局唯一 ID(如 `InstanceAccount.id`, `InstanceDatabase.id`)时, 可以用顶层资源方式暴露, 并通过 `instance_id` 进行 scope 过滤.

因此, 本文采用顶层入口 + 可选过滤的方案:

- `instances`: `/api/v1/instances/*`(实例管理与 instance actions)
- `accounts`: `/api/v1/accounts/*`(台账/权限/同步/统计/分类; 支持 `instance_id` 过滤)
- `databases`: `/api/v1/databases/*`(台账/趋势/尺寸视图; 支持 `instance_id` 过滤)

## 4. 建议的模块划分(用于导航与 ownership)

下面是基于你当前产品边界与 API v1 namespace 的建议划分(可按你后续引入 VM 域再微调):

- 核心模块(业务核心):
  - `database`(当前唯一核心域, 以 `instances` 为聚合根):
    - `instances`: 实例管理(聚合根), 主要承载实例级 CRUD 与 actions(restore/sync-capacity 等).
    - `accounts`: 账户台账/权限/同步/统计/分类(顶层入口, 支持 `instance_id` 过滤).
    - `databases`: 数据库台账/趋势/尺寸视图(顶层入口, 支持 `instance_id` 过滤).
    - `credentials`: 凭据 CRUD(服务于 instances).
    - `connections`: 连接测试与状态(服务于 instances).
  - `virtualization`(未来核心域规划):
    - `platforms`: 虚拟化/云平台管理.
    - `virtual-machines`: 虚拟机清单/详情.
    - `vm-statistics`: 虚拟机统计.
    - `vm-size-statistics`: 虚拟机大小统计.
- 支撑模块(顶层但非核心):
  - `tags`: 标签 CRUD, options/categories, bulk 子模块.
  - `logs`: 统一日志中心(`UnifiedLog` 查询/筛选/统计/导出).
  - `sync-sessions`: 同步会话中心(`SyncSession`, 覆盖 account/capacity/aggregation 等类别).
  - `scheduler`: 定时任务管理(以及后台 tasks 的外部入口).
  - `partitions`: 分区管理.
  - `users`: 用户管理与统计.
  - `dashboard`: 仪表板聚合数据(视图).
- 平台模块:
  - `auth`: 登录/登出/CSRF/JWT 刷新/me.
  - `health`: 健康检查.
  - `cache`: 缓存统计与清理.
  - `admin`: 应用元信息(app-info)等.
  - `common`: UI 侧通用下拉/options.

### 4.1 功能与数据流(从代码扫描)

本文件的域划分不只来自 "API 名称", 还来自业务能力与数据流(以代码为准):

- 核心能力概述: `README.md` (实例管理/账户与权限治理/容量洞察/调度与自动化/统一日志中心).
- 数据模型: `app/models/*` (Instance/Credential/Tag/InstanceAccount/InstanceDatabase/AccountPermission/AccountChangeLog/AccountClassification/SyncSession/UnifiedLog/...).
- 同步任务与会话:
  - 账户同步(两阶段: inventory + collection): `app/tasks/accounts_sync_tasks.py`, `app/services/accounts_sync/coordinator.py`.
  - 容量采集(数据库清单同步 + 容量采集落库): `app/tasks/capacity_collection_tasks.py`, `app/services/database_sync/coordinator.py`.
  - 聚合计算(daily/weekly/monthly/quarterly): `app/tasks/capacity_aggregation_tasks.py`.
  - 同步会话与实例记录: `app/models/sync_session.py`, `app/services/sync_session_service.py`.
- 台账/报表视图:
  - 账户台账: `app/services/ledgers/accounts_ledger_list_service.py`.
  - 数据库台账: `app/services/ledgers/database_ledger_service.py`.
- 运维与可观测:
  - 分区创建/清理/健康监控: `app/tasks/partition_management_tasks.py`.
  - 日志/会话清理(30 天): `app/tasks/log_cleanup_tasks.py`.

因此, 在 API 资源归属上, 本项目推荐:

- `instances` 作为聚合根模块, 主要承载实例管理与实例级 actions.
- `accounts`/`databases` 作为顶层资源入口(读模型/报表/治理), scope 通过 `instance_id` query 表达, 不再以 `instances/{instance_id}/...` 作为主要入口.
- 同步会话(`SyncSession`)是跨多个同步类别的中心概念, 更适合用独立模块(`sync-sessions`)而不是归入 `history/*`.
- 统一日志(`UnifiedLog`)是系统可观测能力, 更适合用 `logs` 模块.

## 5. 目录结构建议(层优先)

### 5.1 目标目录结构(示例)

```text
app/
  api/
    __init__.py                 # register_api_blueprints, /api/v1 挂载
    v1/
      __init__.py               # create_api_v1_blueprint, add_namespace
      api.py                    # WhaleFallApi
      models/                   # envelope + shared models
      resources/                # BaseResource + decorators
      namespaces/
        # 约定: namespaces 只负责 HTTP 层(入参/序列化/错误映射), 业务逻辑下沉到 services
        core/
          instances.py          # /instances + instance actions
          accounts.py
          databases.py
          credentials.py
          connections.py
        supporting/
          tags.py
          logs.py
          sync_sessions.py
          scheduler.py
          partitions.py
          users.py
          dashboard.py
        platform/
          auth.py
          health.py
          cache.py
          admin.py
          common.py

  services/                     # 业务编排/用例(按模块分包)
    instances/
    accounts/
    databases/
    credentials/
    connections/
    tags/
    logs/
    sync_sessions/
    scheduler/
    partitions/
    users/
    dashboard/
    auth/
    health/
    cache/
    admin/
    common/
    files/

  repositories/                 # 存储访问(按模块分包可选)
  models/                       # ORM models
  schemas/                      # 序列化/校验
  tasks/                        # 后台任务(调度入口)
  utils/
  routes/                       # SSR pages routes (可选, 与 API 解耦)
  views/
  templates/
  static/
```

### 5.2 迁移原则

- 先迁移 API v1 的"职责边界"不动行为: `app/api/v1/namespaces/**` 只保留入参解析/权限/序列化/错误映射, 业务逻辑下沉到 `app/services/**`(必要时使用 `app/repositories/**`). 若对 `namespaces/` 做 Python 路径整理(例如 core/supporting/platform 子包), 可以短期保留 re-export shim.
- 每迁移 1 个模块, 对齐依赖方向: `app/api`/`app/routes`/`app/tasks` → `app/services` → `app/repositories` → `app/models`(以及 schemas/types). 业务层不依赖 API 侧的 envelope/models.

## 6. API 路径收敛策略(对齐命名规范)

统一遵循 `docs/Obsidian/standards/backend/api-naming-standards.md`, 额外补充本文件的评估约定:

- "视图式"路径收敛: `list/search/detail` 倾向合并为集合 GET + query + 单体 GET.
- "动词路径"收敛: `pause/resume/run/cancel/clear/remove/assign/create/cleanup` 等动词优先放到 `/actions/<action-name>`.
- "跨域导出"需要明确归属: 本文选择下沉到具体业务模块(见 7.11), 并按 breaking change 评估.

## 7. 需要修改的 API 清单(建议)

说明:

- "Current" 指现有对外路径(来自 `app/api/v1/**`).
- "Proposed" 指 layer-first(目录组织) + 命名规范下的目标路径.
- Compatibility: 全局 no-alias. 本文所有 Proposed 路径变更均不保留旧路径, 不提供 alias/deprecated 过渡.

### 7.1 Health(命名重复)

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/health/health` | `GET /api/v1/health` | 去重. `health` namespace 下不再出现 `health/health`. |

Breaking change: 不保留 `/api/v1/health/health`. 所有调用方必须迁移到 `/api/v1/health`.

### 7.2 Logs(统一日志)

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/history/logs/list` | `GET /api/v1/logs` | 列表与筛选统一用 query 参数(当前 filters 已支持 search/level/module/start_time/end_time/hours 等). |
| `GET /api/v1/history/logs/search` | `GET /api/v1/logs` | 与 list 合并. |
| `GET /api/v1/history/logs/detail/<log_id>` | `GET /api/v1/logs/<log_id>` | 资源化 detail. |
| `GET /api/v1/history/logs/statistics` | `GET /api/v1/logs/statistics` | 保持语义, 仅调整 base path. |
| `GET /api/v1/history/logs/modules` | `GET /api/v1/logs/modules` | 保持语义, 仅调整 base path. |

Breaking change: 不保留 `/api/v1/history/logs/*` alias. 所有调用方必须迁移到 `/api/v1/logs/*`.

### 7.3 Sync sessions(同步会话)

同步会话是跨 accounts/capacity/aggregation 等类别的统一追踪中心(见 `SyncSession.sync_category`), 建议从 `history/*` 里抽出, 用更明确的 `sync-sessions` 命名.

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/history/sessions` | `GET /api/v1/sync-sessions` | list. |
| `GET /api/v1/history/sessions/<session_id>` | `GET /api/v1/sync-sessions/<session_id>` | detail. |
| `GET /api/v1/history/sessions/<session_id>/error-logs` | `GET /api/v1/sync-sessions/<session_id>/error-logs` | errors. |
| `POST /api/v1/history/sessions/<session_id>/cancel` | `POST /api/v1/sync-sessions/<session_id>/actions/cancel` | action 收敛. |

Breaking change: 不保留 `/api/v1/history/sessions/*` alias. 所有调用方必须迁移到 `/api/v1/sync-sessions/*`.
Breaking change: 不保留 `POST /api/v1/sync-sessions/<session_id>/cancel`. 统一使用 `.../actions/cancel`.

### 7.4 Scheduler(action 收敛)

| Current | Proposed | Notes |
|---|---|---|
| `POST /api/v1/scheduler/jobs/<job_id>/pause` | `POST /api/v1/scheduler/jobs/<job_id>/actions/pause` | action 收敛. |
| `POST /api/v1/scheduler/jobs/<job_id>/resume` | `POST /api/v1/scheduler/jobs/<job_id>/actions/resume` | action 收敛. |
| `POST /api/v1/scheduler/jobs/<job_id>/run` | `POST /api/v1/scheduler/jobs/<job_id>/actions/run` | action 收敛. |
| `POST /api/v1/scheduler/jobs/reload` | `POST /api/v1/scheduler/jobs/actions/reload` | 批量/全局动作使用 collection actions. |

Breaking change: 不保留旧路径. 所有调用方必须迁移到 `.../actions/*`.

### 7.5 Partitions(resource 命名 + action 收敛)

现状 base path 是 `/partition`(单数), 并且 list 是 `/partition/partitions`. 建议统一为复数资源: `/partitions`.

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/partition/partitions` | `GET /api/v1/partitions` | 统一复数集合. |
| `POST /api/v1/partition/create` | `POST /api/v1/partitions` | 用 POST collection 表达 create. |
| `POST /api/v1/partition/cleanup` | `POST /api/v1/partitions/actions/cleanup` | cleanup 是动作. |
| `GET /api/v1/partition/info` | `GET /api/v1/partitions/info` | base path 统一. |
| `GET /api/v1/partition/status` | `GET /api/v1/partitions/status` | base path 统一. |
| `GET /api/v1/partition/statistics` | `GET /api/v1/partitions/statistics` | base path 统一. |
| `GET /api/v1/partition/aggregations/core-metrics` | `GET /api/v1/partitions/aggregations/core-metrics` | base path 统一. |

Breaking change: 不保留 `/api/v1/partition/*` 旧路径. 所有调用方必须迁移到 `/api/v1/partitions/*`.

### 7.6 Tags bulk(action 收敛)

| Current | Proposed | Notes |
|---|---|---|
| `POST /api/v1/tags/bulk/assign` | `POST /api/v1/tags/bulk/actions/assign` | action 收敛. |
| `POST /api/v1/tags/bulk/remove` | `POST /api/v1/tags/bulk/actions/remove` | action 收敛. |
| `POST /api/v1/tags/bulk/remove-all` | `POST /api/v1/tags/bulk/actions/remove-all` | action 收敛. |

保留不变(建议): `GET /api/v1/tags/bulk/instances`, `GET /api/v1/tags/bulk/tags`, `POST /api/v1/tags/bulk/instance-tags`.

Breaking change: 不保留 `/api/v1/tags/bulk/(assign|remove|remove-all)`. 统一使用 `/api/v1/tags/bulk/actions/*`.

### 7.7 Cache(action 收敛)

| Current | Proposed | Notes |
|---|---|---|
| `POST /api/v1/cache/clear/user` | `POST /api/v1/cache/actions/clear-user` | action 收敛. |
| `POST /api/v1/cache/clear/instance` | `POST /api/v1/cache/actions/clear-instance` | action 收敛. |
| `POST /api/v1/cache/clear/all` | `POST /api/v1/cache/actions/clear-all` | action 收敛. |
| `POST /api/v1/cache/classification/clear` | `POST /api/v1/cache/actions/clear-classification` | 将分类清理也收敛到 actions(避免 path 里出现动词 clear). |
| `POST /api/v1/cache/classification/clear/<db_type>` | `POST /api/v1/cache/actions/clear-classification` | 用 payload 传 `db_type` 做可选过滤, 删除 path param 变体. |

保留不变(建议): `GET /api/v1/cache/stats`, `GET /api/v1/cache/classification/stats`.

Breaking change: 不保留 `/api/v1/cache/clear/*` 与 `/api/v1/cache/classification/clear*`. 统一使用 `/api/v1/cache/actions/*`.

### 7.8 Accounts: 顶层资源(台账/权限/统计/同步/分类)

目标: `accounts` 作为顶层资源入口存在: `/api/v1/accounts/*`. 其中 `account_id` 统一指 `InstanceAccount.id`(全局唯一), instance scope 通过 query `instance_id` 表达, 不再依赖 `instances/<instance_id>/...` 的子资源路径作为主要入口.

#### 7.8.1 账户列表/权限/变更历史(读模型)

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/accounts/ledgers` | (keep) | 顶层列表入口, 支持 `instance_id` query 做 scope 过滤. |
| `GET /api/v1/instances/<instance_id>/accounts` | `GET /api/v1/accounts/ledgers?instance_id=<instance_id>` | 统一列表入口(移除 instances 子资源版本). |
| `GET /api/v1/accounts/ledgers/<account_id>/permissions` | (keep) | `account_id` 即 `InstanceAccount.id`. |
| `GET /api/v1/instances/<instance_id>/accounts/<account_id>/permissions` | `GET /api/v1/accounts/ledgers/<account_id>/permissions` | 统一权限入口(移除 instances scope 变体). |
| `GET /api/v1/instances/<instance_id>/accounts/<account_id>/change-history` | `GET /api/v1/accounts/ledgers/<account_id>/change-history` | 顶层提供 change history(移除 instances scope 变体). |

Breaking change: 不保留 `/api/v1/instances/<instance_id>/accounts/*` 旧路径. 调用方迁移到 `/api/v1/accounts/ledgers*`(必要时用 `instance_id` query 过滤).

#### 7.8.2 Statistics(统计)

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/accounts/statistics` | (keep) | 顶层统计入口. |
| `GET /api/v1/accounts/statistics/summary` | (keep) | 可选按 `instance_id`/`db_type` 过滤(与现状一致). |
| `GET /api/v1/accounts/statistics/db-types` | (keep) | 顶层统计入口. |
| `GET /api/v1/accounts/statistics/classifications` | (keep) | 顶层统计入口. |

#### 7.8.3 同步动作(sync accounts)

同步账户本质上是 instance 级动作(需要 `instance_id`), 但入口保持在 accounts 顶层 actions 下:

| Current | Proposed | Notes |
|---|---|---|
| `POST /api/v1/accounts/actions/sync` | (keep) | payload 传 `instance_id`. |
| `POST /api/v1/accounts/actions/sync-all` | (keep) | 批量同步所有 active instances 的账户. |

#### 7.8.4 账户分类(account classifications)

账户分类对应的模型与服务是独立的一套能力(`AccountClassification`/`ClassificationRule`/`Assignment`). 本方案将其作为 accounts 顶层治理能力, 并允许通过 query/payload 传 `instance_id` 做局部作用域.

| Current | Proposed | Notes |
|---|---|---|
| `/api/v1/accounts/classifications/*` | (keep) | 顶层入口. |

### 7.9 Databases: 顶层资源(台账/趋势/尺寸视图)

在数据模型里, databases 依附于 instance(`InstanceDatabase.instance_id`). 但因为 `InstanceDatabase.id` 是全局唯一 ID, 所以 API v1 提供顶层 `databases` 入口, 并通过 `instance_id` query 表达 scope 过滤.

#### 7.9.1 台账与趋势(报表视图)

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/databases/ledgers` | (keep) | 顶层入口; 支持 `instance_id` query 作为可选过滤. |
| `GET /api/v1/databases/ledgers/<database_id>/capacity-trend` | (keep) | `database_id` 即 `InstanceDatabase.id`. |

#### 7.9.2 sizes / tables sizes 视图(从 instances 子资源迁移到 databases 顶层)

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/instances/<instance_id>/databases/sizes` | `GET /api/v1/databases/sizes?instance_id=<instance_id>` | 将 sizes 视图收敛到 databases 顶层入口. |
| `GET /api/v1/instances/<instance_id>/databases/<database_name>/tables/sizes` | `GET /api/v1/databases/<database_id>/tables/sizes` | 使用 `database_id(InstanceDatabase.id)` 作为稳定标识, 避免 path 里携带 `instance_id/database_name`. |
| `POST /api/v1/instances/<instance_id>/databases/<database_name>/tables/sizes/actions/refresh` | `POST /api/v1/databases/<database_id>/tables/sizes/actions/refresh` | action 收敛到 databases 顶层. |
| `POST /api/v1/instances/<instance_id>/actions/sync-capacity` | (keep) | capacity sync 是 instance action. |

Breaking change: 不保留 `GET /api/v1/instances/<instance_id>/databases/sizes` 与 `.../tables/sizes*` 旧路径. 调用方迁移到 `GET /api/v1/databases/sizes`(传 `instance_id`) 与 `/api/v1/databases/<database_id>/tables/sizes*`.

### 7.10 Instances/Tags/Credentials(delete/restore 收敛)

| Current | Proposed | Notes |
|---|---|---|
| `POST /api/v1/instances/<instance_id>/delete` | `DELETE /api/v1/instances/<instance_id>` | 用标准 method 表达 delete. |
| `POST /api/v1/instances/<instance_id>/restore` | `POST /api/v1/instances/<instance_id>/actions/restore` | restore 是动作. |
| `POST /api/v1/tags/<tag_id>/delete` | `DELETE /api/v1/tags/<tag_id>` | 同上. |
| `POST /api/v1/credentials/<credential_id>/delete` | `DELETE /api/v1/credentials/<credential_id>` | 同上. |

可选收敛(看你愿不愿意动前端): 将 `batch-create/batch-delete/batch-delete` 统一迁移到 `.../actions/*` 下, 使动作全部集中.

Breaking change: 不保留旧路径. 所有调用方必须迁移到标准 method 或 `.../actions/*`.

### 7.11 Exports/templates(现 files) 的归属选择

这是你最关心的点. 这里给 2 个可选方案, 便于评估成本.

#### Option A: 保留 platform exports(最小改动, 仅改"概念归属")

- 路径保留: `GET /api/v1/files/*`
- 代码归属调整: 将 `files` 明确归为 platform 模块(例如 `app/api/v1/namespaces/platform/files.py` + `app/services/files/**`), 并在文档中声明: 它是跨模块导出/模板入口, 不是业务模块.
- 优点: 不改前端, 风险最小.
- 缺点: "files" 名称仍偏泛, 心智成本仍存在.

#### Option B: 下沉到具体业务模块(更符合资源归属, 但需要前端改动)

Decision (2025-12-29): 选择 Option B, 且不保留旧路径 alias.

建议目标形态:

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/files/account-export` | `GET /api/v1/accounts/ledgers/export` | accounts ledgers export(可选用 `instance_id` query 限定 scope). |
| `GET /api/v1/files/instance-export` | `GET /api/v1/instances/export` | export 属于 instances 集合视图. |
| `GET /api/v1/files/database-ledger-export` | `GET /api/v1/databases/ledgers/export` | databases ledgers export(可选用 `instance_id` query 限定 scope). |
| `GET /api/v1/files/log-export` | `GET /api/v1/logs/export` | export 属于 logs 视图. |
| `GET /api/v1/files/template-download` | `GET /api/v1/instances/import-template` | template 属于 instances 导入能力. |

Breaking change: 不保留 `/api/v1/files/*` alias. 所有调用方(前端模板/JS/外部调用)必须按上表迁移.

## 8. 影响面(用于你评估改动成本)

主要调用点(用于回归/后续漂移检查):

- `/api/v1/health`:
  - `app/static/js/modules/services/partition_service.js`
- `/api/v1/logs`:
  - `app/static/js/modules/services/logs_service.js`
  - `app/static/js/modules/views/history/logs/logs.js`
- `/api/v1/sync-sessions`:
  - `app/static/js/modules/services/sync_sessions_service.js`
  - `app/static/js/modules/views/history/sessions/sync-sessions.js`
- `/api/v1/partitions/*`:
  - `app/static/js/modules/services/partition_service.js`
  - `app/static/js/modules/views/admin/partitions/partition-list.js`
- `/api/v1/accounts/ledgers*`:
  - `app/templates/accounts/ledgers.html`
  - `app/static/js/modules/views/accounts/ledgers.js`
  - `app/static/js/modules/views/instances/detail.js`
- `/api/v1/accounts/ledgers/<account_id>/permissions`:
  - `app/static/js/modules/services/permission_service.js`
  - `app/static/js/modules/views/components/permissions/permission-viewer.js`
- `/api/v1/accounts/ledgers/<account_id>/change-history`:
  - `app/static/js/modules/services/instance_management_service.js`
- `/api/v1/accounts/actions/sync*`:
  - `app/templates/instances/detail.html`
  - `app/static/js/modules/services/instance_management_service.js`
- `/api/v1/databases/ledgers*`:
  - `app/templates/databases/ledgers.html`
  - `app/static/js/modules/services/database_ledger_service.js`
- `/api/v1/databases/sizes`:
  - `app/static/js/modules/views/instances/detail.js`
  - `app/static/js/modules/services/instance_management_service.js`
- `/api/v1/databases/<database_id>/tables/sizes*`:
  - `app/static/js/modules/services/instance_management_service.js`
- `/api/v1/instances/export`:
  - `app/templates/instances/list.html`
- `/api/v1/instances/import-template`:
  - `app/templates/instances/modals/batch-create-modal.html`
- method 收敛:
  - `DELETE /api/v1/instances/<instance_id>`:
    - `app/static/js/modules/services/instance_service.js`
  - `POST /api/v1/instances/<instance_id>/actions/restore`:
    - `app/static/js/modules/services/instance_management_service.js`
  - `DELETE /api/v1/tags/<tag_id>`:
    - `app/static/js/modules/services/tag_management_service.js`
    - `app/static/js/modules/views/tags/index.js`
  - `DELETE /api/v1/credentials/<credential_id>`:
    - `app/static/js/modules/services/credentials_service.js`

## 9. 迁移建议(分阶段)

建议按风险从低到高推进:

1) 仅做 concept/ownership 收敛(不改路径): 在代码与文档中标注模块归属, 按 layer-first 整理 `namespaces/services/repositories` 的职责边界与落点, 保持 URL 不动.
2) 收敛低风险动词路径到 actions: `sync_sessions.cancel`, `scheduler.pause/resume/run/reload`, `tags_bulk`, `cache`.
3) 收敛 resource 形态: `logs` 去掉 list/search/detail, `health/health` 去重.
4) 最后再处理 high churn 的 base path 级别调整: `instances/<instance_id>/accounts/*` 与 `instances/<instance_id>/databases/*` 迁移到顶层 `accounts/*`/`databases/*`, exports(files) 下沉, 以及 `partition -> partitions`.

注意: 因为全局 no-alias, 只要阶段涉及路径变更, 即为 breaking release, 需要同步更新前端与外部调用方.

每个阶段都建议配套:

- OpenAPI schema 校验: `python scripts/dev/openapi/export_openapi.py --check`
- 最小契约测试: 覆盖 200 + 4xx.

## 10. Confirmed decisions(2026-01-07)

1) 当前核心域收敛为 1 个: 数据库域(以 `instances` 为聚合根), 但 API v1 顶层资源入口包含 `instances`/`accounts`/`databases`.
2) `accounts` 顶层入口: `/api/v1/accounts/*`(ID 使用 `InstanceAccount.id`). 不保留 `instances/<instance_id>/accounts/*` 子资源路径.
3) `databases` 顶层入口: `/api/v1/databases/*`(ID 使用 `InstanceDatabase.id`). 不保留 `instances/<instance_id>/databases/sizes` 与 `instances/<instance_id>/databases/<database_name>/tables/sizes*` 子资源路径.
4) Exports 采用下沉方案(Option B), 且不保留 `/api/v1/files/*` alias(见 7.11).
5) 接受 `partition` base path 从 `/partition` 迁移到 `/partitions`(breaking, no alias).
6) 兼容策略采用全局 no-alias: 本文所有 Proposed 路径变更均不保留旧入口.
