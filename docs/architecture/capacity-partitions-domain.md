# 容量与分区域(Capacity + Partitions)研发图表包

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-06
> 更新: 2026-01-06
> 范围: capacity collection/aggregation + postgres partitions
> 关联: ./instances-domain.md; ./spec.md; ./flows/whalefall-data-sync-flows.md

## 1. 主流程图(Flow)

### 1.1 Scheduled pipeline: collect -> aggregate

场景: 定时任务采集所有实例容量并落库,随后触发聚合.

入口: scheduler job `collect_database_sizes` -> `app/tasks/capacity_collection_tasks.py::collect_database_sizes`

```mermaid
flowchart TD
  S0["Scheduler tick"] --> Task["capacity_collection_tasks.collect_database_sizes"]
  Task --> Ctx["create_app() + app_context()"]
  Ctx --> Q["Query active instances from PostgreSQL"]
  Q --> Any{"instances empty?"}
  Any -->|yes| End0["Return success (no work)"]
  Any -->|no| Sess["sync_session_service.create_session(sync_category=capacity)"]
  Sess --> Rec["add_instance_records(session_id, instance_ids)"]

  Rec --> Loop{"for each instance"}
  Loop --> StartRec["start_instance_sync(record_id)"]
  StartRec --> CO["CapacitySyncCoordinator(instance)"]

  CO --> Conn["connect() via ConnectionFactory"]
  Conn --> ConnOK{"connected?"}
  ConnOK -->|no| FailRec["fail_instance_sync(record_id, error)"]
  ConnOK -->|yes| Inv["synchronize_inventory()"]
  Inv --> InvWrite["upsert instance_databases"]
  InvWrite --> Active{"active_databases empty?"}
  Active -->|yes| DoneInv["complete_instance_sync(inventory only)"]
  Active -->|no| Collect["collect_capacity(active_databases)"]
  Collect --> ColOK{"collected empty?"}
  ColOK -->|yes| FailData["fail_instance_sync(record_id, SYNC_DATA_ERROR)"]
  ColOK -->|no| PersistDB["save_database_stats() -> database_size_stats"]
  PersistDB --> PersistInst["update_instance_total_size() -> instance_size_stats"]
  PersistInst --> DoneRec["complete_instance_sync(record_id, stats + details)"]

  DoneInv --> Next["commit + next instance"]
  DoneRec --> Next
  FailRec --> Next
  FailData --> Next
  Next --> Loop

  Loop --> Wrap["update SyncSession totals/status/completed_at"]
  Wrap --> End["commit + return summary"]
```

补充入口(同域,但不走 SyncSession):

- 单实例手动触发: `POST /api/v1/instances/{id}/actions/sync-capacity` (见 `docs/architecture/instances-domain.md`).

### 1.2 Partition management: create/cleanup/monitor

场景: 为容量相关分区表按月创建分区,清理旧分区,并监控缺失分区.

入口: scheduler jobs -> `app/tasks/partition_management_tasks.py`

```mermaid
flowchart TD
  P0["Scheduler tick"] --> PJob{"which job?"}
  PJob -->|create| PCreate["create_database_size_partitions"]
  PJob -->|cleanup| PClean["cleanup_database_size_partitions"]
  PJob -->|monitor| PMon["monitor_partition_health"]

  PCreate --> PMgmt["PartitionManagementService.create_future_partitions(months_ahead=3)"]
  PMgmt --> DDL1["PostgreSQL DDL: CREATE TABLE ... PARTITION OF ..."]
  DDL1 --> PDone1["commit + log"]

  PClean --> PMgmt2["PartitionManagementService.cleanup_old_partitions(retention_months)"]
  PMgmt2 --> DDL2["PostgreSQL DDL: DROP TABLE partitions"]
  DDL2 --> PDone2["commit + log"]

  PMon --> PStats["PartitionStatisticsService.get_partition_info/statistics"]
  PStats --> Missing{"next month partition missing?"}
  Missing -->|no| POk["return healthy snapshot"]
  Missing -->|yes| Auto["PartitionManagementService.create_partition(next_month)"]
  Auto --> POk2["commit + return snapshot"]
```

## 2. 主时序图(Sequence)

场景: 定时采集容量(`collect_database_sizes`)的单轮执行.

```mermaid
sequenceDiagram
  autonumber
  participant SCH as Scheduler (APScheduler)
  participant Task as collect_database_sizes
  participant SESS as sync_session_service
  participant CO as CapacitySyncCoordinator
  participant CF as ConnectionFactory
  participant EXT as External DB
  participant PG as PostgreSQL
  participant AGG as AggregationService (best-effort)
  participant R as Redis (not used)

  SCH->>Task: run job collect_database_sizes
  Task->>Task: create_app() + app_context()
  Task->>PG: SELECT active instances
  Task->>SESS: create_session(sync_category=capacity)
  SESS-->>Task: session_id
  Task->>SESS: add_instance_records(session_id, instance_ids)
  loop each instance
    Task->>SESS: start_instance_sync(record_id)
    Task->>CO: new CapacitySyncCoordinator(instance)
    Task->>CO: connect()
    CO->>CF: create_connection(instance)
    CF-->>CO: connection
    CO->>EXT: connect()
    alt connect failed
      Task->>SESS: fail_instance_sync(record_id, error)
      Task->>PG: COMMIT
    else connected
      Task->>CO: synchronize_inventory()
      CO->>EXT: fetch inventory (databases)
      CO->>PG: upsert instance_databases
      alt no active databases
        Task->>SESS: complete_instance_sync(record_id, inventory-only)
        Task->>PG: COMMIT
      else has active databases
        Task->>CO: collect_capacity(active_databases)
        CO->>EXT: fetch capacity (sizes)
        alt collected empty
          Task->>SESS: fail_instance_sync(record_id, SYNC_DATA_ERROR)
          Task->>PG: COMMIT
        else collected ok
          Task->>CO: save_database_stats(databases_data)
          CO->>PG: upsert database_size_stats
          Task->>CO: update_instance_total_size()
          CO->>PG: upsert instance_size_stats
          Task->>AGG: calculate daily aggregations
          Task->>SESS: complete_instance_sync(record_id, stats + details)
          Task->>PG: COMMIT
        end
      end
      Task->>CO: disconnect()
    end
  end
  Task->>PG: update sync_sessions(status, totals, completed_at)
  Task->>PG: COMMIT
```

## 3. 状态机(Optional but valuable)

### 3.1 SyncSession + SyncInstanceRecord

容量采集/聚合任务的可观测性主要依赖会话中心模型:

- session: `sync_sessions` (running/completed/failed/cancelled)
- record: `sync_instance_records` (pending/running/completed/failed)

```mermaid
stateDiagram-v2
  state "SyncSession" as SS {
    [*] --> running
    running --> completed: all instance records done, failed_instances == 0
    running --> failed: all instance records done, failed_instances > 0
    running --> cancelled: cancel(session_id)
    cancelled --> [*]
    completed --> [*]
    failed --> [*]
  }
```

```mermaid
stateDiagram-v2
  [*] --> pending
  pending --> running: start_instance_sync
  running --> completed: complete_instance_sync
  running --> failed: fail_instance_sync
  completed --> [*]
  failed --> [*]
```

### 3.2 Partition lifecycle (per month, per table)

```mermaid
stateDiagram-v2
  [*] --> absent
  absent --> created: create_partition / create_future_partitions
  created --> dropped: cleanup_old_partitions
  dropped --> [*]
```

## 4. API 契约(Optional)

说明:

- read APIs: capacity/partition endpoints mostly read-only, return unified success envelope.
- write APIs: partition create/cleanup endpoints execute PostgreSQL DDL and must be permission-gated.
- cross-domain entrypoints: instance action sync-capacity and table-size refresh live under instances API.

| Method | Path | Purpose | Idempotency | Pagination | Notes |
| --- | --- | --- | --- | --- | --- |
| POST | /api/v1/capacity/aggregations/current | trigger current-period aggregation | no (writes aggregations) | - | scope defaults to all |
| GET | /api/v1/capacity/databases | list database aggregations | yes (read) | page/limit | supports start_date/end_date |
| GET | /api/v1/capacity/databases/summary | summary of database aggregations | yes (read) | - | supports time_range or start/end |
| GET | /api/v1/capacity/instances | list instance aggregations | yes (read) | page/limit | supports start_date/end_date |
| GET | /api/v1/capacity/instances/summary | summary of instance aggregations | yes (read) | - | supports time_range or start/end |
| GET | /api/v1/partitions/info | partition info snapshot | yes (read) | - | joins pg metadata via services |
| GET | /api/v1/partitions/status | partition health snapshot | yes (read) | - | warns when missing partitions |
| GET | /api/v1/partitions | list partitions | yes (read) | page/limit | supports search/sort/status filters |
| POST | /api/v1/partitions | create partitions | no | - | runs DDL, permission required |
| POST | /api/v1/partitions/actions/cleanup | cleanup old partitions | no | - | runs DDL, permission required |
| GET | /api/v1/partitions/statistics | partition statistics | yes (read) | - | used for dashboard |
| GET | /api/v1/partitions/aggregations/core-metrics | core metrics series | yes (read) | - | chart-focused payload |
