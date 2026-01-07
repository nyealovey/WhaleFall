# 账户与权限域(Accounts + Permissions) 研发图表包

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-06
> 更新: 2026-01-06
> 范围: 研发视角, accounts/permissions 写入与读取链路
> 关联: ./spec.md; ./flows/whalefall-data-sync-flows.md; ../plans/2025-12-30-account-permissions-refactor-v4.md

## 1. 目标

- 让研发在 10 分钟内回答: "账户从外部 DB 进来后, 如何落库, 如何被读取, 失败怎么定位".
- 图表与代码落点一一对应, 用于 code review, 拆域重构, 排障.

## 2. 域边界

### 2.1 In scope

- Inventory(清单阶段): 维护 `instance_accounts`(账户存在性, is_active 生命周期).
- Permissions(权限阶段): 写 `account_permission.permission_snapshot(version=4)` 与 `account_permission.permission_facts`.
- Change log: 写 `account_change_log`(差异日志, 仅 change_type != "none").
- Sessions(批量/任务模式): 写 `sync_sessions`/`sync_instance_records` 追踪进度与结果.

### 2.2 Out of scope(但有依赖)

- 账户分类: 读取 `permission_facts` 作为规则输入(见 `docs/architecture/account-classification-v2-design.md`).
- 标签: 台账读取会关联 instance tags(见 `app/repositories/ledgers/accounts_ledger_repository.py`).

## 3. 组件与依赖(代码落点)

```mermaid
flowchart LR
  subgraph Domain["Accounts + Permissions Domain"]
    subgraph Routes["Routes (Flask-RESTX)"]
      SyncAll["POST /api/v1/accounts/actions/sync-all"]
      SyncOne["POST /api/v1/accounts/actions/sync"]
      LedgerList["GET /api/v1/accounts/ledgers"]
      LedgerPerm["GET /api/v1/accounts/ledgers/{account_id}/permissions"]
      Stats["GET /api/v1/accounts/statistics*"]

      SessList["GET /api/v1/sync-sessions"]
      SessDetail["GET /api/v1/sync-sessions/{session_id}"]
      SessCancel["POST /api/v1/sync-sessions/{session_id}/actions/cancel"]
    end

    subgraph Tasks["Tasks (Scheduler/Background Thread)"]
      SyncTask["tasks.accounts_sync_tasks.sync_accounts"]
    end

    subgraph Services["Services"]
      SyncSvc["services.accounts_sync.accounts_sync_service (AccountSyncService)"]
      Coordinator["services.accounts_sync.AccountSyncCoordinator"]
      Inventory["services.accounts_sync.AccountInventoryManager"]
      PermMgr["services.accounts_sync.AccountPermissionManager"]
      SnapshotView["services.accounts_permissions.snapshot_view"]
      FactsBuilder["services.accounts_permissions.facts_builder"]
      SessSvc["services.sync_session_service"]
      LedgerListSvc["services.ledgers.AccountsLedgerListService"]
      LedgerPermSvc["services.ledgers.AccountsLedgerPermissionsService"]
      InstAccountsSvc["services.instances.InstanceAccountsService"]
      StatsSvc["services.accounts.AccountsStatisticsReadService"]
      SessReadSvc["services.history_sessions.HistorySessionsReadService"]
    end

    subgraph Repos["Repositories"]
      LedgerRepo["repositories.ledgers.AccountsLedgerRepository"]
      InstRepo["repositories.instance_accounts_repository"]
      StatsRepo["repositories.account_statistics_repository"]
      SessRepo["repositories.history_sessions_repository"]
    end

    subgraph Models["Models (SQLAlchemy)"]
      MInst["models.Instance"]
      MIA["models.InstanceAccount"]
      MAP["models.AccountPermission"]
      MLog["models.AccountChangeLog"]
      MSess["models.SyncSession"]
      MRec["models.SyncInstanceRecord"]
    end
  end

  subgraph Adapters["Adapters"]
    ConnFactory["connection_adapters.ConnectionFactory"]
    AccountAdapter["accounts_sync.adapters.*"]
  end

  subgraph Storage["Storage"]
    PG["PostgreSQL (主库)"]
    Redis["Redis (Flask-Caching, not used)"]
  end

  subgraph External["External DBs"]
    X1["MySQL/PostgreSQL/SQLServer/Oracle"]
  end

  SyncOne --> SyncSvc --> Coordinator
  SyncAll --> SyncTask
  SyncTask --> SessSvc
  SyncTask --> Coordinator
  SyncSvc --> SessSvc

  Coordinator --> ConnFactory --> AccountAdapter --> X1
  Coordinator --> Inventory --> MIA --> PG
  Coordinator --> PermMgr --> MAP --> PG
  PermMgr --> MLog --> PG
  PermMgr --> SnapshotView
  PermMgr --> FactsBuilder

  LedgerList --> LedgerListSvc --> LedgerRepo --> MAP
  LedgerPerm --> LedgerPermSvc --> LedgerRepo --> MAP
  LedgerRepo --> MIA
  LedgerRepo --> MInst
  MAP --> PG
  MIA --> PG
  MInst --> PG

  InstAccounts --> InstAccountsSvc --> InstRepo --> MAP
  InstPerm --> InstAccountsSvc --> InstRepo --> MAP
  InstHistory --> InstAccountsSvc --> InstRepo --> MLog
  InstAccountsSvc --> SnapshotView
  InstRepo --> MIA
  InstRepo --> MInst

  Stats --> StatsSvc --> StatsRepo --> PG
  StatsRepo --> MAP
  StatsRepo --> MIA
  StatsRepo --> MInst

  SessList --> SessReadSvc --> SessRepo --> MSess --> PG
  SessDetail --> SessReadSvc --> SessRepo
  SessRepo --> MRec --> PG
  SessCancel --> SessSvc --> MSess --> PG
  SessSvc --> MRec --> PG
```

代码入口参考:

- 单实例同步: `app/api/v1/namespaces/accounts.py` -> `AccountsSyncInstanceActionResource.post` -> `AccountSyncService.sync_accounts`.
- 全量批量同步: `app/api/v1/namespaces/accounts.py` -> `AccountsSyncAllResource.post` -> background thread -> `app/tasks/accounts_sync_tasks.py::sync_accounts`.
- 台账读取: `app/api/v1/namespaces/accounts.py` -> `AccountsLedgersListResource.get` / `AccountsLedgersPermissionsResource.get`.

## 4. 数据模型(ERD)

```mermaid
erDiagram
  INSTANCES ||--o{ INSTANCE_ACCOUNTS : has
  INSTANCES ||--o{ ACCOUNT_PERMISSION : has
  INSTANCE_ACCOUNTS ||--|| ACCOUNT_PERMISSION : current
  INSTANCES ||--o{ ACCOUNT_CHANGE_LOG : has
  SYNC_SESSIONS ||--o{ SYNC_INSTANCE_RECORDS : tracks
  INSTANCES ||--o{ SYNC_INSTANCE_RECORDS : targets

  INSTANCES {
    int id PK
    string db_type
    string name
    string host
    bool is_active
  }

  INSTANCE_ACCOUNTS {
    int id PK
    int instance_id FK
    string username
    string db_type
    bool is_active
    datetime first_seen_at
    datetime last_seen_at
    datetime deleted_at
  }

  ACCOUNT_PERMISSION {
    int id PK
    int instance_id FK
    int instance_account_id FK
    string db_type
    string username
    json permission_snapshot
    json permission_facts
    datetime last_sync_time
    string last_change_type
    datetime last_change_time
  }

  ACCOUNT_CHANGE_LOG {
    int id PK
    int instance_id FK
    string db_type
    string username
    string change_type
    datetime change_time
    string session_id
    json privilege_diff
    json other_diff
  }

  SYNC_SESSIONS {
    int id PK
    string session_id
    string sync_type
    string sync_category
    string status
    int total_instances
    int successful_instances
    int failed_instances
  }

  SYNC_INSTANCE_RECORDS {
    int id PK
    string session_id FK
    int instance_id FK
    string sync_category
    string status
    int items_synced
    int items_created
    int items_updated
    int items_deleted
    text error_message
  }
```

关键约束(落库一致性):

- `instance_accounts` 唯一约束: `(instance_id, db_type, username)`.
- `account_permission` 唯一约束: `(instance_id, db_type, username)`, 且必须关联 `instance_account_id`.
- `account_change_log` 不做 `account_permission` 外键, 通过 `(instance_id, db_type, username)` 逻辑关联.
- `sync_sessions` 唯一约束: `session_id`.
- `sync_instance_records.session_id` 外键指向 `sync_sessions.session_id`(注意不是 `sync_sessions.id`).
- `permission_snapshot` 仅支持 `version = 4`, 读取端不做 legacy fallback(见 `app/services/accounts_permissions/snapshot_view.py`).

## 5. 写入链路: 账户同步(Inventory + Permissions)

### 5.1 主流程(概览)

```mermaid
flowchart TD
  Start["触发同步"] --> Mode{"sync_type?"}
  Mode -->|manual_single| Single["单实例同步(无 SyncSession)"]
  Mode -->|manual_task/scheduled_task/manual_batch| Session["会话模式(有 SyncSession)"]

  Single --> C1["AccountSyncCoordinator.connect()"]
  Session --> SessCreate["sync_session_service.create_session(...)"]
  SessCreate --> RecAdd["sync_session_service.add_instance_records(...)"]
  RecAdd --> RecStart["sync_session_service.start_instance_sync(record_id)"]
  RecStart --> C1

  C1 --> ConnOK{"connected?"}
  ConnOK -->|no| Err["连接失败/异常"]
  ConnOK -->|yes| Fetch["adapter.fetch_remote_accounts(...)"]

  Fetch --> Inv["AccountInventoryManager.synchronize(...)"]
  Inv --> IA["upsert instance_accounts + 标记 is_active"]
  IA --> Enrich{"需要 enrich_permissions?"}
  Enrich -->|yes| EnrichCall["adapter.enrich_permissions(..., usernames=pending)"]
  Enrich -->|no| Perm["AccountPermissionManager.synchronize(...)"]
  EnrichCall --> Perm

  Perm --> PermOK{"permission sync ok?"}
  PermOK -->|no| Err["PermissionSyncError/DB error"]
  PermOK -->|yes| AP["upsert account_permission(snapshot v4 + facts)"]

  AP --> Diff{"changed?"}
  Diff -->|yes| Log["insert account_change_log(change_type != none)"]
  Diff -->|no| Done["mark last_sync_time"]
  Log --> Done

  Done --> Cache["Redis cache? (not used)"]
  Cache --> EndMode{"会话模式?"}
  EndMode -->|yes| RecOK["complete_instance_sync(stats, details)"]
  EndMode -->|no| ReturnOK["return result"]

  Err --> EndErr{"会话模式?"}
  EndErr -->|yes| RecFail["fail_instance_sync(error, details)"]
  EndErr -->|no| ReturnFail["return error"]
```

事务边界(研发需要知道):

- API 路由通过 `safe_route_call` 统一 `commit/rollback`(见 `app/utils/route_safety.py::safe_route_call`).
- `AccountInventoryManager` 与 `AccountPermissionManager` 内部使用 `db.session.begin_nested()` 形成 savepoint, 但不负责最终 `commit`.
- `tasks.accounts_sync_tasks.sync_accounts` 在每个实例执行前后显式 `db.session.commit()`.

### 5.2 时序图: 单实例同步(manual_single)

```mermaid
sequenceDiagram
  autonumber
  participant UI as API(/accounts/actions/sync)
  participant Safe as safe_route_call
  participant SVC as AccountSyncService
  participant CO as AccountSyncCoordinator
  participant CF as ConnectionFactory
  participant AD as AccountAdapter
  participant EXT as External DB
  participant INV as AccountInventoryManager
  participant PER as AccountPermissionManager
  participant PG as PostgreSQL
  participant R as Redis (not used)

  Note over R: 本链路不写缓存,不做 cache invalidation

  UI->>Safe: execute()
  Safe->>SVC: sync_accounts(sync_type=manual_single)
  SVC->>CO: with AccountSyncCoordinator(instance)
  CO->>CF: create_connection(instance)
  CF-->>CO: connection
  CO->>CO: connection.connect()
  CO->>AD: fetch_remote_accounts(instance, connection)
  AD->>EXT: query accounts list
  EXT-->>AD: rows
  AD-->>CO: remote_accounts
  CO->>INV: synchronize(instance, remote_accounts)
  INV->>PG: upsert instance_accounts, mark is_active
  CO->>AD: enrich_permissions(..., usernames=pending)
  AD->>EXT: query permissions for active accounts
  EXT-->>AD: permissions rows
  AD-->>CO: remote_accounts(enriched)
  CO->>PER: synchronize(instance, remote_accounts, active_accounts)
  PER->>PG: upsert account_permission(snapshot v4 + facts)
  PER->>PG: insert account_change_log(if changed)
  CO-->>SVC: summary{inventory, collection}
  SVC-->>Safe: result(success/message/counts)
  Safe->>PG: commit()
  Safe-->>UI: success envelope
```

### 5.3 时序图: 全量批量同步(sync-all -> background -> task)

```mermaid
sequenceDiagram
  autonumber
  participant UI as API(/accounts/actions/sync-all)
  participant BG as Background Thread
  participant Task as tasks.sync_accounts
  participant SESS as sync_session_service
  participant CO as AccountSyncCoordinator
  participant CF as ConnectionFactory
  participant AD as AccountAdapter
  participant EXT as External DB
  participant PG as PostgreSQL
  participant R as Redis (not used)

  Note over R: 本链路不写缓存,不做 cache invalidation

  UI->>BG: launch sync_accounts_task(manual_run=True, session_id)
  BG-->>UI: return session_id

  BG->>Task: sync_accounts(manual_run=True, session_id)
  Task->>Task: create_app() + app_context()
  Task->>PG: query active instances
  Task->>SESS: get_session_by_id(session_id)
  alt session not found
    Task->>SESS: create_session(sync_type=manual_task, session_id)
  end
  Task->>SESS: add_instance_records(session_id, instance_ids)
  loop each instance
    Task->>SESS: start_instance_sync(record_id)
    Task->>PG: commit()
    Task->>CO: with AccountSyncCoordinator(instance)
    CO->>CF: create_connection(instance)
    CF-->>CO: connection
    CO->>AD: fetch_remote_accounts(...)
    AD->>EXT: query accounts list
    EXT-->>AD: rows
    AD-->>CO: remote_accounts
    CO->>AD: enrich_permissions(..., usernames=pending)
    AD->>EXT: query permissions for active accounts
    EXT-->>AD: permissions rows
    AD-->>CO: remote_accounts(enriched)
    CO->>PG: upsert instance_accounts + account_permission + account_change_log
    CO-->>Task: summary or PermissionSyncError/RuntimeError
    alt success
      Task->>SESS: complete_instance_sync(record_id, stats, details)
    else failure
      Task->>SESS: fail_instance_sync(record_id, error, details?)
    end
    Task->>PG: commit()
  end
  Task->>PG: update sync_sessions(status, totals, completed_at)
  Task->>PG: commit()
```

## 6. 读取链路: 账户台账与权限详情

### 6.1 台账列表(GET /accounts/ledgers)

```mermaid
sequenceDiagram
  autonumber
  participant UI as API(/accounts/ledgers)
  participant Safe as safe_route_call
  participant SVC as AccountsLedgerListService
  participant Repo as AccountsLedgerRepository
  participant DB as PostgreSQL

  UI->>Safe: execute()
  Safe->>SVC: list_accounts(filters, sort)
  SVC->>Repo: list_accounts(filters)
  Repo->>DB: query AccountPermission join InstanceAccount join Instance
  Repo->>DB: filter InstanceAccount.is_active = true
  Repo->>DB: fetch tags_map(instance_ids)
  Repo->>DB: fetch classifications_map(account_ids)
  Repo-->>SVC: page_result + metrics
  SVC-->>Safe: PaginatedResult[AccountLedgerItem]
  Safe->>DB: commit()
  Safe-->>UI: success envelope
```

### 6.2 权限详情(GET /accounts/ledgers/{account_id}/permissions)

```mermaid
sequenceDiagram
  autonumber
  participant UI as API(/accounts/ledgers/{id}/permissions)
  participant Safe as safe_route_call
  participant SVC as AccountsLedgerPermissionsService
  participant Repo as AccountsLedgerRepository
  participant View as build_permission_snapshot_view
  participant DB as PostgreSQL

  UI->>Safe: execute()
  Safe->>SVC: get_permissions(account_id)
  SVC->>Repo: get_account_with_instance(account_id)
  Repo->>DB: query AccountPermission join Instance
  Repo-->>SVC: account(permission row)
  SVC->>View: build_permission_snapshot_view(account)
  alt snapshot.version == 4
    View-->>SVC: snapshot
    SVC-->>Safe: DTO(permissions + account)
    Safe->>DB: commit()
    Safe-->>UI: success envelope
  else snapshot missing or legacy
    View-->>SVC: raise AppError(SNAPSHOT_MISSING, 409)
    Safe->>DB: rollback()
    Safe-->>UI: error envelope
  end
```

## 7. 状态机与关键约束

### 7.1 SyncSession 状态机(会话级)

```mermaid
stateDiagram-v2
  [*] --> running
  running --> completed: all instances done, failed_instances == 0
  running --> failed: all instances done, failed_instances > 0
  running --> cancelled: cancel(session_id)
  cancelled --> [*]
  completed --> [*]
  failed --> [*]

  note right of cancelled
    cancel 仅标记状态为 cancelled
    不会强制中断正在执行的任务
  end note

  note right of failed
    retry = 重新触发同步
    会创建新的 session_id
  end note
```

实现参考: `app/models/sync_session.py::update_statistics`, `app/services/sync_session_service.py`.

### 7.2 SyncInstanceRecord 状态机(实例级)

```mermaid
stateDiagram-v2
  [*] --> pending
  pending --> running: start_instance_sync
  running --> completed: complete_instance_sync
  running --> failed: fail_instance_sync
  completed --> [*]
  failed --> [*]

  note right of failed
    retry = 重新触发同步
    通常会生成新的 record_id
  end note
```

### 7.3 权限快照契约(强约束, 无 fallback)

```mermaid
stateDiagram-v2
  [*] --> snapshot_missing
  snapshot_missing --> error_409: build_permission_snapshot_view
  [*] --> snapshot_v4
  snapshot_v4 --> readable: downstream consumers
```

约束点:

- 写入端统一生成 `permission_snapshot.version = 4`(见 `app/services/accounts_sync/permission_manager.py::_build_permission_snapshot`).
- 读取端只接受 v4, 否则直接抛 `SNAPSHOT_MISSING`(见 `app/services/accounts_permissions/snapshot_view.py`).

### 7.4 InstanceAccount 生命周期(清单阶段)

```mermaid
stateDiagram-v2
  [*] --> active: first_seen
  active --> inactive: not seen in remote list
  inactive --> active: reactivated(appear again)
```

实现参考: `app/services/accounts_sync/inventory_manager.py::synchronize`.

## 8. 失败模式与排查线索(研发版)

| 现象 | 常见原因 | 关键日志/事件(event) | 落点 |
| --- | --- | --- | --- |
| 单实例同步报 "数据库连接问题" | 凭据错误, 网络不可达, 超时 | `accounts_sync_connection_init_failed` / `accounts_sync_connection_exception` | `app/services/accounts_sync/coordinator.py::connect` |
| 权限阶段失败(PermissionSyncError) | diff 日志写入失败, snapshot 构建异常, DB flush/commit 失败 | `account_permission_sync_failed` / `account_permission_change_log_failed` | `app/services/accounts_sync/permission_manager.py` |
| 权限阶段被跳过 | 无活跃账户(active_accounts 为空) | `accounts_sync_collection_skipped_no_active_accounts` | `app/services/accounts_sync/coordinator.py::synchronize_permissions` |
| 权限详情接口返回 409 | snapshot 缺失或不是 v4 | `SNAPSHOT_MISSING` | `app/services/accounts_permissions/snapshot_view.py` |
| 台账列表看不到账户 | instance_account.is_active = false | (查询过滤) | `app/repositories/ledgers/accounts_ledger_repository.py::_build_account_query` |

## 9. API 契约(Optional)

说明:

- response envelope: 所有 endpoints 通过 `BaseResource.success`/`safe_call` 返回统一封套.
- error envelope: 业务异常透传, 未捕获异常会被包装为统一 `public_error`.
- idempotency: 无显式 idempotency-key; 读取类 endpoints 具备幂等语义, 写入/触发类不保证幂等.

| Method | Path | Purpose | Idempotency | Pagination | Notes |
| --- | --- | --- | --- | --- | --- |
| POST | /api/v1/accounts/actions/sync-all | trigger background full sync | no | - | returns `session_id`; runs `tasks.accounts_sync_tasks.sync_accounts` |
| POST | /api/v1/accounts/actions/sync | sync one instance | no | - | payload: `instance_id`; connects External DB and writes `instance_accounts` + `account_permission` |
| GET | /api/v1/accounts/ledgers | list accounts ledger | yes (read) | page/limit | filters: search/db_type/instance_id/is_locked/is_superuser/tags/classification/sort/order |
| GET | /api/v1/accounts/ledgers/{account_id}/permissions | account permissions detail | yes (read) | - | requires `permission_snapshot.version == 4`, else 409 `SNAPSHOT_MISSING` |
| GET | /api/v1/accounts/statistics | accounts statistics | yes (read) | - | aggregated counts + db_type/classification breakdown |
| GET | /api/v1/accounts/statistics/summary | accounts summary | yes (read) | - | query: `instance_id`, `db_type` |
| GET | /api/v1/accounts/statistics/db-types | db_type stats | yes (read) | - | uses `account_permission` + `instance_accounts` |
| GET | /api/v1/accounts/statistics/classifications | classification stats | yes (read) | - | depends on classification assignments |
| GET | /api/v1/sync-sessions | list sync sessions | yes (read) | page/limit | filters: `sync_type`, `sync_category`, `status`, sort/order |
| GET | /api/v1/sync-sessions/{session_id} | session detail + records | yes (read) | - | reads `sync_sessions` + `sync_instance_records` |
| GET | /api/v1/sync-sessions/{session_id}/error-logs | session error records | yes (read) | - | subset of records where `status == failed` |
| POST | /api/v1/sync-sessions/{session_id}/actions/cancel | cancel session | yes-ish | - | best-effort: marks status `cancelled`, does not stop running task thread |
