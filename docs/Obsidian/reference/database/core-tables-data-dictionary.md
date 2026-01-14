---
title: 核心表数据字典(core tables)
aliases:
  - core-tables-data-dictionary
  - core-tables
tags:
  - reference
  - reference/database
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: 核心表字段含义, 关键索引/唯一性, 保留策略与常用自查 SQL
related:
  - "[[reference/database/README|database reference]]"
  - "[[operations/observability-ops]]"
  - "[[standards/backend/database-migrations]]"
---

# 核心表数据字典(core tables)

> [!info] 说明
> 本文以 SQLAlchemy models 为准, 只覆盖"开发与排障最常查"的核心表.

## 1. Unified logs

### 1.1 `unified_logs`

Source:

- model: `app/models/unified_log.py`
- writer: `app/utils/logging/handlers.py` -> `DatabaseLogHandler`

用途:

- 存储 structlog 结构化日志(去文件化, 便于检索与排障).

字段(核心):

| Column | Type(概念) | Notes |
| --- | --- | --- |
| `id` | int | 自增主键 |
| `timestamp` | timestamptz | 日志时间(UTC), 查询主入口 |
| `level` | enum | `DEBUG/INFO/WARNING/ERROR/CRITICAL` |
| `module` | varchar | 模块名(例如 `scheduler`, `accounts_sync`) |
| `message` | text | 事件摘要(面向人) |
| `traceback` | text? | 异常堆栈(仅异常时) |
| `context` | json? | 上下文字段(含 `request_id`, `user_id`, `url`, `method` 等) |
| `created_at` | timestamptz | 入库时间 |

索引(代码侧声明):

- `idx_timestamp_level_module(timestamp, level, module)`
- `idx_timestamp_module(timestamp, module)`
- `idx_level_timestamp(level, timestamp)`

保留策略:

- 当前未提供自动清理任务, 如需清理请走运维/手工归档策略.

常用自查 SQL:

```sql
-- 最近错误
SELECT timestamp, level, module, message
FROM unified_logs
WHERE level IN ('ERROR', 'CRITICAL')
ORDER BY timestamp DESC
LIMIT 50;
```

```sql
-- 按 request_id 追踪(依赖 context.request_id)
SELECT timestamp, level, module, message, context
FROM unified_logs
WHERE context->>'request_id' = '<request_id>'
ORDER BY timestamp ASC;
```

## 2. Sync sessions

### 2.1 `sync_sessions`

Source:

- model: `app/models/sync_session.py`

用途:

- 记录一次批量同步/采集/聚合的会话级元信息与统计, 支持 UI/排障侧按 session_id 聚合查看.

字段(核心):

| Column | Notes |
| --- | --- |
| `id` | int, 内部主键 |
| `session_id` | uuid string, 外部稳定标识; `sync_instance_records.session_id` 通过它做关联 |
| `sync_type` | `manual_single/manual_batch/manual_task/scheduled_task` |
| `sync_category` | `account/capacity/config/aggregation/other` |
| `status` | `running/completed/failed/cancelled` |
| `started_at` / `completed_at` | 会话开始/结束时间 |
| `total_instances/successful_instances/failed_instances` | 会话级统计 |
| `created_by` | 手动触发时的用户 ID |
| `created_at/updated_at` | 创建/更新时间 |

索引/关联:

- `session_id` 有 unique + index.
- `sync_instance_records.session_id` 外键指向 `sync_sessions.session_id`(不是 `sync_sessions.id`).

保留策略:

- 当前未提供自动清理任务, 如需清理请走运维/手工归档策略.

### 2.2 `sync_instance_records`

Source:

- model: `app/models/sync_instance_record.py`

用途:

- 记录一个 session 中每个 instance 的执行结果(状态, 耗时, 统计, 错误信息).

字段(核心):

| Column | Notes |
| --- | --- |
| `session_id` | 关联会话(外键指向 `sync_sessions.session_id`) |
| `instance_id` | 关联实例(外键指向 `instances.id`) |
| `sync_category` | 与 session 同类, 但记录级可覆盖 |
| `status` | `pending/running/completed/failed` |
| `started_at/completed_at` | 实例级开始/结束时间 |
| `items_synced/items_created/items_updated/items_deleted` | 通用统计字段 |
| `error_message` | 错误摘要 |
| `sync_details` | JSON 详情(尽量放可序列化小对象) |
| `created_at` | 创建时间(用于清理) |

保留策略:

- 当前未提供自动清理任务, 如需清理请走运维/手工归档策略.

常用自查 SQL:

```sql
-- 按 session 聚合查看失败实例
SELECT instance_id, instance_name, status, error_message
FROM sync_instance_records
WHERE session_id = '<session_id>'
  AND status = 'failed'
ORDER BY created_at DESC;
```

## 3. Capacity stats(tables are partitioned)

> [!note]
> 分区管理服务会同时管理 4 张容量表:
> - `database_size_stats`
> - `database_size_aggregations`
> - `instance_size_stats`
> - `instance_size_aggregations`
>
> 入口: `app/services/partition_management_service.py` (API: `app/api/v1/namespaces/partition.py`).

### 3.1 `database_size_stats`

Source:

- model: `app/models/database_size_stat.py`
- partition key: `collected_date`

用途:

- 存储"每日"数据库级容量数据(单位 MB), 用于趋势与聚合.

字段(核心):

| Column | Notes |
| --- | --- |
| `instance_id` | 实例 ID |
| `database_name` | 数据库名 |
| `size_mb` | 总大小(MB) |
| `data_size_mb` | 数据大小(MB, optional) |
| `log_size_mb` | 日志大小(MB, SQL Server optional) |
| `collected_date` | 采集日期(分区键) |
| `collected_at` | 采集时间戳 |

唯一性/索引:

- unique: `uq_daily_database_size(instance_id, database_name, collected_date)`
- index: `ix_database_size_stats_collected_date(collected_date)`
- index: `ix_database_size_stats_instance_date(instance_id, collected_date)`

保留策略:

- 按月分区, 默认保留 `DATABASE_SIZE_RETENTION_MONTHS`(默认 12)个月.
- 旧分区清理由管理员通过 Partition API 触发,最终落到 `PartitionManagementService.cleanup_old_partitions`.

### 3.2 `database_size_aggregations`

Source:

- model: `app/models/database_size_aggregation.py`
- partition key: `period_start`

用途:

- 存储按周期的数据库级聚合(weekly/monthly/quarterly), 包含均值/极值/增量/增长率.

唯一性/索引:

- unique: `uq_database_size_aggregation(instance_id, database_name, period_type, period_start)`
- index: `ix_database_size_aggregations_instance_period(instance_id, period_type, period_start)`
- index: `ix_database_size_aggregations_period_type(period_type, period_start)`

保留策略:

- 同样按月分区, 跟随 `DATABASE_SIZE_RETENTION_MONTHS`.

### 3.3 `instance_size_stats`

Source:

- model: `app/models/instance_size_stat.py`
- partition key: `collected_date`

用途:

- 存储实例级每日总容量, 作为"实例趋势"与聚合输入.

字段(核心):

| Column | Notes |
| --- | --- |
| `instance_id` | 实例 ID |
| `total_size_mb` | 实例总大小(MB) |
| `database_count` | 数据库数量 |
| `collected_date` | 采集日期(分区键) |
| `is_deleted/deleted_at` | 软删除标记(实例被回收站后) |

保留策略:

- 同样按月分区, 跟随 `DATABASE_SIZE_RETENTION_MONTHS`.

### 3.4 `instance_size_aggregations`

Source:

- model: `app/models/instance_size_aggregation.py`
- partition key: `period_start`

用途:

- 存储实例级聚合(daily/weekly/monthly/quarterly), 包含趋势方向与增长率.

唯一性/索引:

- unique: `uq_instance_size_aggregation(instance_id, period_type, period_start)`
- index: `ix_instance_size_aggregations_instance_period(instance_id, period_type, period_start)`
- index: `ix_instance_size_aggregations_period_type(period_type, period_start)`

保留策略:

- 同样按月分区, 跟随 `DATABASE_SIZE_RETENTION_MONTHS`.

### 3.5 `database_table_size_stats`(latest snapshot)

Source:

- model: `app/models/database_table_size_stat.py`
- writer: `app/services/database_sync/table_size_coordinator.py`(upsert + cleanup removed)

用途:

- 存储表级容量快照, 仅保留最新状态(会被 upsert 覆盖, 并删除"本次采集不存在"的表记录).

唯一性/索引:

- unique: `uq_database_table_size_stats_key(instance_id, database_name, schema_name, table_name)`
- index: `ix_database_table_size_stats_instance_database(instance_id, database_name)`
- index: `ix_database_table_size_stats_instance_database_size(instance_id, database_name, size_mb)`

## 4. 变更历史

- 2026-01-10: 新增核心表数据字典, 覆盖 unified_logs, sync_sessions, capacity stats.
