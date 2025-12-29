# Domain-first API/Directory Restructure Proposal

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-28
> 更新: 2025-12-29
> 范围: `app/api/v1/**` 对外 API 路径, 以及后端目录结构(域优先)
> 关联:
> - `docs/standards/backend/api-naming-standards.md`
> - `docs/changes/refactor/004-flask-restx-openapi-migration-plan.md`
> - `docs/reference/api/api-routes-documentation.md`

## 1. 背景与问题

当前仓库已经具备明显的"按域拆服务"雏形(例如 `app/services/instances/`, `app/services/tags/`), 但 API v1 的 namespace 是"平铺式模块列表"(例如 `files`, `health`, `cache` 与 `instances`, `accounts` 同一层级). 这会带来两个评估层面的混乱:

- 认知混乱: 调用方很难区分哪些是核心业务域, 哪些是平台能力/运维能力, 哪些是跨域交付介质(例如 export/template).
- 命名漂移: 部分 endpoint 已符合 `api-naming-standards.md`(kebab-case, actions), 但仍存在 `list/search/detail` 这类"视图式"路径, 以及多个"动词路径"未收敛到 `/actions/*`.

本文件给出一个"domain-first"方案, 用于你评估:

1) 目录结构如何从 layer-first 过渡到 domain-first.
2) 哪些 API 路径建议修改, 以及兼容策略(统一 no-alias).

## 2. 目标 / 非目标

### 2.1 目标

- 用"域"作为主要导航维度: 代码与文档中显式区分核心域(当前仅数据库域, 以 `instances` 为聚合根)、支撑域与平台域, 并为未来虚拟机相关域预留落点.
- 收敛 API v1 路径命名: 对齐 `docs/standards/backend/api-naming-standards.md`.
- 给出可落地的迁移路径: 允许分域渐进迁移, 但路径变更统一按 breaking(no-alias)评估(不保留旧入口).

### 2.2 非目标

- 不要求一次性重写所有业务 Service/Repository.
- 不强制一次性把所有历史 endpoint 变成"完美 REST": 允许先统一概念与归属, 再分阶段做路径收敛. 但凡发生路径变更, 均不提供 alias.

### 2.3 Decisions(已确认)

- 当前核心域收敛为 1 个: 数据库域(以 `instances` 为聚合根).
- `instance` 是聚合根: accounts/databases 作为 instance 子资源存在.
- 数据库域内允许存在多种对外资源形态(子资源/治理/报表), 但统一收敛为 instance scope:
  - `account-classifications`, `account-ledgers`, `database-ledgers`, `capacity` 等均挂在 `instances/{instance_id}/...` 下.
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
| `/api/v1/accounts/ledgers*` | `/api/v1/instances/<instance_id>/account-ledgers*` | 见 7.8.2. |
| `/api/v1/accounts/statistics*` | `/api/v1/instances/<instance_id>/account-ledgers/statistics*` | 见 7.8.2. |
| `/api/v1/accounts/actions/sync*` | instances actions | 见 7.8.3. |
| `/api/v1/accounts/classifications/*` | `/api/v1/instances/<instance_id>/account-classifications/*` | 见 7.8.4. |
| `/api/v1/databases/ledgers*` | `/api/v1/instances/<instance_id>/database-ledgers*` | 见 7.9.2. |
| `/api/v1/files/*` | move into owning domains | 见 7.11. |

## 3. Domain-first 的定义(本仓库口径)

在本仓库中, domain-first 表示:

- 每个业务域拥有自己的: API(handlers/resources), Service 编排, Repository(若有), domain types.
- 跨域能力(认证, 健康检查, 缓存, 元信息, 通用 options, 导出/模板)归入 platform domain, 不与 core domain 同权重混在一起.

注意: "files" 不是业务域, 更像交付介质(exports/downloads/templates). domain-first 方案会强制你做出选择: 要么把它明确归为 platform domain, 要么把它下沉到具体业务域.

### 3.1 聚合根 vs 子资源 vs 报表视图

为了避免把"实体名"误当成"domain", 本文采用下面的口径:

- 聚合根(aggregate root): 业务上最稳定的主对象, 其子对象的生命周期/一致性通常由它承载. 在你的语义里, `instance` 是聚合根.
- 子资源(sub-resource): 依附于聚合根存在的对象, 例如 instance 下的 accounts, databases.
- 报表视图(reporting view): 基于某个 scope 的汇总/检索/导出/统计能力, 可以是 instance-scoped 或跨实例. 本文决定将数据库相关报表能力统一收敛为 instance-scoped, 并挂在 `instances/{instance_id}/...` 下.

因此, 本文不把 `accounts` 作为 core domain, 而是:

- instance 内: accounts 作为 `instances/{instance_id}/accounts` 子资源存在.
- instance 内: 账户台账/统计/分类等治理与报表能力也收敛到 `instances/{instance_id}/...`(例如 `instances/{instance_id}/account-ledgers`, `instances/{instance_id}/account-classifications`).

## 4. 建议的域划分(用于导航与 ownership)

下面是基于你当前产品边界与 API v1 namespace 的建议划分(可按你后续引入 VM 域再微调):

- Core domain groups:
  - `database`(当前唯一核心域, 以 `instances` 为聚合根):
    - `instances`: 实例管理(聚合根), 并承载 instance scope 下的所有数据库相关能力:
      - 子资源: accounts/databases.
      - 治理: account-classifications.
      - 报表: account-ledgers/database-ledgers/capacity.
      - actions: sync-accounts/sync-capacity 等.
    - `credentials`: 凭据 CRUD(服务于 instances).
    - `connections`: 连接测试与状态(服务于 instances).
  - `virtualization`(未来核心域规划):
    - `platforms`: 虚拟化/云平台管理.
    - `virtual-machines`: 虚拟机清单/详情.
    - `vm-statistics`: 虚拟机统计.
    - `vm-size-statistics`: 虚拟机大小统计.
- Supporting domains(顶层但非核心):
  - `tags`: 标签 CRUD, options/categories, bulk 子模块.
  - `logs`: 统一日志中心(`UnifiedLog` 查询/筛选/统计/导出).
  - `sync-sessions`: 同步会话中心(`SyncSession`, 覆盖 account/capacity/aggregation 等类别).
  - `scheduler`: 定时任务管理(以及后台 tasks 的外部入口).
  - `partitions`: 分区管理.
  - `users`: 用户管理与统计.
  - `dashboard`: 仪表板聚合数据(视图).
- Platform domains:
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

因此, "domain-first" 在本项目里的推荐落点是:

- `instances` 作为聚合根 domain, accounts/databases 作为 instance 的子资源.
- instance 内的 "台账/统计/导出/分类" 作为 instances domain 的子模块, 路径统一收敛到 `instances/{instance_id}/...`.
- 同步会话(`SyncSession`)是跨多个同步类别的中心概念, 更适合用独立 domain(`sync-sessions`)而不是归入 `history/*`.
- 统一日志(`UnifiedLog`)是系统可观测能力, 更适合用 `logs` domain.

## 5. 目录结构建议(域优先)

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
      namespaces/               # 过渡期保留: 仅作为 re-export shim

  domains/
    # 约定: 一个 domain 的最小骨架
    # domains/<group>/<domain>/
    #   api_v1.py
    #   services/
    #   repositories/ (optional)
    #   types.py

    database/                   # current core domain group
      instances/
        api_v1.py                # mounts /instances and instance-scoped modules
        services/
        repositories/
        types.py
        modules/
          accounts/
            api_v1.py            # /instances/<instance_id>/accounts/*
            services/
            types.py
          databases/
            api_v1.py            # /instances/<instance_id>/databases/*
            services/
            types.py
          account_ledgers/
            api_v1.py            # /instances/<instance_id>/account-ledgers/*
            services/
            types.py
          database_ledgers/
            api_v1.py            # /instances/<instance_id>/database-ledgers/*
            services/
            types.py
          account_classifications/
            api_v1.py            # /instances/<instance_id>/account-classifications/*
            services/
            types.py
          capacity/
            api_v1.py            # /instances/<instance_id>/capacity/*
            services/
            types.py
      credentials/
        api_v1.py
        services/
        repositories/
        types.py
      connections/
        api_v1.py
        services/
        types.py

    virtualization/              # planned core domain group
      platforms/
        api_v1.py
        services/
        types.py
      virtual_machines/
        api_v1.py
        services/
        types.py
      vm_statistics/
        api_v1.py
        services/
        types.py
      vm_size_statistics/
        api_v1.py
        services/
        types.py

    supporting/                 # top-level but non-core
      tags/
        api_v1.py
        services/
        repositories/
        types.py
      logs/
        api_v1.py
        services/
        repositories/
        types.py
      sync_sessions/
        api_v1.py
        services/
        repositories/
        types.py
      scheduler/
        api_v1.py
        services/
        types.py
      partitions/
        api_v1.py
        services/
        types.py
      users/
        api_v1.py
        services/
        types.py
      dashboard/
        api_v1.py
        services/
        types.py

  platform/
    auth_api_v1.py
    health_api_v1.py
    cache_api_v1.py
    admin_api_v1.py
    common_api_v1.py
    # exports_api_v1.py         # (Decision: 不保留. 导出入口下沉到各业务域.)
```

### 5.2 迁移原则

- 先迁移"入口文件"不动行为: 将 `app/api/v1/namespaces/<x>.py` 变为 re-export, 逐步把实现搬到 `app/domains/**` 或 `app/platform/**`.
- 每迁移 1 个 domain, 对齐依赖方向: domain 内可以依赖 `app/api/v1/models`(envelope), 但不应反向依赖 `app/routes/**`.

## 6. API 路径收敛策略(对齐命名规范)

统一遵循 `docs/standards/backend/api-naming-standards.md`, 额外补充本文件的评估约定:

- "视图式"路径收敛: `list/search/detail` 倾向合并为集合 GET + query + 单体 GET.
- "动词路径"收敛: `pause/resume/run/cancel/clear/remove/assign/create/cleanup` 等动词优先放到 `/actions/<action-name>`.
- "跨域导出"需要明确归属: 本文选择下沉到具体 domain(见 7.11), 并按 breaking change 评估.

## 7. 需要修改的 API 清单(建议)

说明:

- "Current" 指现有对外路径(来自 `app/api/v1/**`).
- "Proposed" 指 domain-first + 命名规范下的目标路径.
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

### 7.8 Accounts: instances 子资源 + instance scope 收敛(台账/统计/分类)

目标: `accounts` 作为 instance 的子资源存在; 同时将账户台账/统计/分类等治理与报表能力统一收敛到 `instances/{instance_id}/...` 下, 避免出现 `accounts/*` 这种误导为顶层业务域的路径.

#### 7.8.1 instance 内 accounts(子资源)

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/instances/<instance_id>/accounts` | (keep) | 已符合子资源语义. |
| `GET /api/v1/instances/<instance_id>/accounts/<account_id>/permissions` | (keep) | 已符合子资源语义. |
| `GET /api/v1/instances/<instance_id>/accounts/<account_id>/change-history` | (keep) | 已符合子资源语义. |

#### 7.8.2 instance 内台账/统计(报表视图)

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/accounts/ledgers` | `GET /api/v1/instances/<instance_id>/account-ledgers` | 将台账视图收敛为 instance scope, 并使用 `account-ledgers` 概念避免误导为 `accounts` 顶层域. |
| `GET /api/v1/accounts/ledgers/<account_id>/permissions` | `GET /api/v1/instances/<instance_id>/account-ledgers/<account_id>/permissions` | instance-scoped permissions view. |
| `GET /api/v1/accounts/statistics` | `GET /api/v1/instances/<instance_id>/account-ledgers/statistics` | instance-scoped 统计聚合. |
| `GET /api/v1/accounts/statistics/summary` | `GET /api/v1/instances/<instance_id>/account-ledgers/statistics/summary` | 同上. |
| `GET /api/v1/accounts/statistics/db-types` | `GET /api/v1/instances/<instance_id>/account-ledgers/statistics/db-types` | 同上. |
| `GET /api/v1/accounts/statistics/classifications` | `GET /api/v1/instances/<instance_id>/account-ledgers/statistics/classifications` | 同上. |

Breaking change: 不保留 `/api/v1/accounts/ledgers*` 与 `/api/v1/accounts/statistics*` alias. 所有调用方必须迁移到 `/api/v1/instances/<instance_id>/account-ledgers*`.

#### 7.8.3 同步动作(sync accounts)

同步账户本质上是 instance 级动作(因为 accounts 属于 instance), 所以将 action 移到 instances 域:

| Current | Proposed | Notes |
|---|---|---|
| `POST /api/v1/accounts/actions/sync` | `POST /api/v1/instances/<instance_id>/actions/sync-accounts` | instance scoped. 原 endpoint 的 `instance_id` 从 body 迁移到 path. |
| `POST /api/v1/accounts/actions/sync-all` | `POST /api/v1/instances/actions/sync-accounts` | collection scoped. 语义为同步所有 active instances 的账户. |

Breaking change: 不保留 `/api/v1/accounts/actions/sync*` alias. 所有调用方必须迁移到 instances actions.

#### 7.8.4 账户分类(account classifications)

账户分类对应的模型与服务是独立的一套能力(`AccountClassification`/`ClassificationRule`/`Assignment`). 按你当前产品边界, 其配置与产出最终服务于 instance 内的 accounts, 因此本方案将其收敛为 instance-scoped 治理能力.

| Current | Proposed | Notes |
|---|---|---|
| `/api/v1/accounts/classifications/*` | `/api/v1/instances/<instance_id>/account-classifications/*` | 保持子路径结构不变, 增加 instance scope 并替换 base path. |

Breaking change: 不保留 `/api/v1/accounts/classifications/*` alias. 所有调用方必须迁移到 `/api/v1/instances/<instance_id>/account-classifications/*`.

### 7.9 Databases: instances 子资源 + instance scope 收敛(台账/趋势)

你提到"accounts 也是 instances 的子属性". 在你的数据模型里, databases 同样是 instance 的子资源(`InstanceDatabase` 依附于 `Instance`).

但当前 API v1 的 `databases` namespace 实际只对外暴露了"台账与趋势"(见 `app/api/v1/namespaces/databases.py`), 并没有对外提供 "instance 下数据库清单/详情" 的管理型资源. 按你当前边界(数据库能力全部收敛到 instances), domain-first 的口径是:

- instance 内: 数据库相关能力优先放在 `instances/{instance_id}/...` 下(例如 sizes, sync-capacity).
- instance 内: 数据库台账/趋势也收敛到 `instances/{instance_id}/database-ledgers/*`.

#### 7.9.1 instance 内 databases(子资源视图)

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/instances/<instance_id>/databases/sizes` | (keep) | 依附于 instance 的数据库视图, 语义上仍属于 instances domain. |
| `POST /api/v1/instances/<instance_id>/actions/sync-capacity` | (keep) | capacity sync 是 instance action. |

#### 7.9.2 instance 内台账/趋势(报表视图)

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/databases/ledgers` | `GET /api/v1/instances/<instance_id>/database-ledgers` | 将数据库台账视图收敛为 instance scope. |
| `GET /api/v1/databases/ledgers/<database_id>/capacity-trend` | `GET /api/v1/instances/<instance_id>/database-ledgers/<database_id>/capacity-trend` | instance-scoped trend view. |

Breaking change: 不保留 `/api/v1/databases/ledgers*` alias. 所有调用方必须迁移到 `/api/v1/instances/<instance_id>/database-ledgers*`.

### 7.10 Instances/Tags/Credentials(delete/restore 收敛)

| Current | Proposed | Notes |
|---|---|---|
| `POST /api/v1/instances/<instance_id>/delete` | `DELETE /api/v1/instances/<instance_id>` | 用标准 method 表达 delete. |
| `POST /api/v1/instances/<instance_id>/restore` | `POST /api/v1/instances/<instance_id>/actions/restore` | restore 是动作. |
| `POST /api/v1/tags/<tag_id>/delete` | `DELETE /api/v1/tags/<tag_id>` | 同上. |
| `POST /api/v1/credentials/<credential_id>/delete` | `DELETE /api/v1/credentials/<credential_id>` | 同上. |

可选收敛(看你愿不愿意动前端): 将 `batch-create/batch-delete/batch-delete` 统一迁移到 `.../actions/*` 下, 使动作全部集中.

Breaking change: 不保留旧路径. 所有调用方必须迁移到标准 method 或 `.../actions/*`.

### 7.11 Exports/templates(现 files) 的 domain-first 选择

这是你最关心的点. 这里给 2 个可选方案, 便于评估成本.

#### Option A: 保留 platform exports(最小改动, 仅改"概念归属")

- 路径保留: `GET /api/v1/files/*`
- 代码归属调整: 将 `files` 明确归为 platform domain(例如 `app/platform/exports_api_v1.py`), 并在文档中声明: 它是跨域导出/模板入口, 不是业务域.
- 优点: 不改前端, 风险最小.
- 缺点: "files" 名称仍偏泛, 心智成本仍存在.

#### Option B: 下沉到具体业务域(更 domain-first, 但需要前端改动)

Decision (2025-12-29): 选择 Option B, 且不保留旧路径 alias.

建议目标形态:

| Current | Proposed | Notes |
|---|---|---|
| `GET /api/v1/files/account-export` | `GET /api/v1/instances/<instance_id>/account-ledgers/export` | instance-scoped account ledgers export. |
| `GET /api/v1/files/instance-export` | `GET /api/v1/instances/export` | export 属于 instances 集合视图. |
| `GET /api/v1/files/database-ledger-export` | `GET /api/v1/instances/<instance_id>/database-ledgers/export` | instance-scoped database ledgers export. |
| `GET /api/v1/files/log-export` | `GET /api/v1/logs/export` | export 属于 logs 视图. |
| `GET /api/v1/files/template-download` | `GET /api/v1/instances/import-template` | template 属于 instances 导入能力. |

Breaking change: 不保留 `/api/v1/files/*` alias. 所有调用方(前端模板/JS/外部调用)必须按上表迁移.

## 8. 影响面(用于你评估改动成本)

从前端与模板中检索到的 API v1 引用(非完整清单, 但可作为评估起点):

- `history/logs`: 既使用了 `GET /api/v1/history/logs/list`, 也使用了 `GET /api/v1/history/logs`(需要统一).
- `health`: 使用了 `GET /api/v1/health/health`(已迁移到 `/api/v1/health`, no alias, 必须改前端).
- `partition`: 使用了 `/api/v1/partition/*`(已迁移到 `/api/v1/partitions/*`, no alias, 必须改前端).
- `files`: 模板与页面使用了 `/api/v1/files/*`(Decision: Option B + no alias, 必须改前端和模板).
  - 同时, `accounts/*`/`databases/*`/`history/*` 相关 API 目前被大量页面/JS 使用, 且本方案会将账户/数据库台账与分类能力进一步收敛为 instance scope(需要补齐 `instance_id` 上下文).

已确认的调用点(用于粗估改动量):

- `/api/v1/files/database-ledger-export`:
  - `app/templates/databases/ledgers.html`
- `/api/v1/files/instance-export`:
  - `app/templates/instances/list.html`
- `/api/v1/files/template-download`:
  - `app/templates/instances/modals/batch-create-modal.html`
- `/api/v1/files/account-export`:
  - `app/templates/accounts/ledgers.html`
  - `app/static/js/modules/views/accounts/ledgers.js`
- `/api/v1/accounts/ledgers`:
  - `app/static/js/modules/views/accounts/ledgers.js`
- `/api/v1/accounts/ledgers/<account_id>/permissions`:
  - `app/static/js/modules/services/permission_service.js`
  - `app/static/js/modules/views/components/permissions/permission-viewer.js`
- `/api/v1/accounts/statistics`:
  - `app/static/js/modules/views/accounts/statistics.js`
- `/api/v1/accounts/actions/sync`:
  - `app/templates/instances/detail.html`
  - `app/static/js/modules/services/instance_management_service.js`
- `/api/v1/accounts/actions/sync-all`:
  - `app/static/js/modules/services/instance_management_service.js`
- `/api/v1/databases/ledgers`:
  - `app/templates/databases/ledgers.html`
  - `app/static/js/modules/services/database_ledger_service.js`
- `/api/v1/databases/ledgers/<database_id>/capacity-trend`:
  - `app/static/js/modules/services/database_ledger_service.js`
- `/api/v1/history/logs/list`:
  - `app/static/js/modules/views/history/logs/logs.js`
- `/api/v1/history/sessions`:
  - `app/static/js/modules/services/sync_sessions_service.js`
  - `app/static/js/modules/views/history/sessions/sync-sessions.js`
- `/api/v1/accounts/classifications`:
  - `app/static/js/modules/services/account_classification_service.js`
- `/api/v1/health/health`:
  - `app/static/js/modules/services/partition_service.js`
- `/api/v1/partition/*`:
  - `app/static/js/modules/services/partition_service.js`
  - `app/static/js/modules/views/admin/partitions/partition-list.js`

## 9. 迁移建议(分阶段)

建议按风险从低到高推进:

1) 仅做 concept/ownership 收敛(不改路径): 在代码与文档中标注 domain, 调整目录落点, 保持 URL 不动.
2) 收敛低风险动词路径到 actions: `sync_sessions.cancel`, `scheduler.pause/resume/run/reload`, `tags_bulk`, `cache`.
3) 收敛 resource 形态: `logs` 去掉 list/search/detail, `health/health` 去重.
4) 最后再处理 high churn 的 base path 级别调整: `accounts/*`/`databases/*` 收敛到 `instances/{instance_id}/*`, exports(files) 下沉, 以及 `partition -> partitions`.

注意: 因为全局 no-alias, 只要阶段涉及路径变更, 即为 breaking release, 需要同步更新前端与外部调用方.

每个阶段都建议配套:

- OpenAPI schema 校验: `python scripts/dev/openapi/export_openapi.py --check`
- 最小契约测试: 覆盖 200 + 4xx.

## 10. Confirmed decisions(2025-12-29)

1) 当前核心域收敛为 1 个: 数据库域(以 `instances` 为聚合根), 账户分类/台账/容量/数据库台账等均归属于该核心域边界.
2) 账户分类/台账/数据库台账等治理与报表能力统一收敛为 instance scope: `/api/v1/instances/<instance_id>/*`.
3) 未来核心域规划: 引入虚拟机相关域(平台、虚拟机清单、虚拟机统计、虚拟机大小统计等), 与数据库域并列演进.
4) 接受 `partition` base path 从 `/partition` 迁移到 `/partitions`(breaking, no alias).
5) 兼容策略采用全局 no-alias: 所有 Proposed 路径变更均不保留旧入口.
