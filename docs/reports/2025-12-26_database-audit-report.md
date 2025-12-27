# 数据库模型与迁移审计报告 - 2025-12-26

> 状态: Draft
> 负责人: WhaleFall DBAudit
> 创建: 2025-12-26
> 更新: 2025-12-26
> 范围: `app/models/**`, `migrations/**`, `sql/**`, `app/routes/**`, `app/services/**`, `app/repositories/**`, `scripts/deploy/**`
> 关联: [docs/standards/documentation-standards.md](../standards/documentation-standards.md); [docs/standards/backend/database-migrations.md](../standards/backend/database-migrations.md); [docs/reference/database/schema-baseline.md](../reference/database/schema-baseline.md); [docs/standards/backend/configuration-and-secrets.md](../standards/backend/configuration-and-secrets.md)

## I. 摘要结论(先给结论)

- P0: `credentials.password` 使用 `varchar(255)` 存储,但当前加密实现会产生较长密文,存在被截断导致"不可解密/连接失败"的高风险; 同时未配置 `PASSWORD_ENCRYPTION_KEY` 时会生成临时密钥,重启后历史凭据不可解密,等价于数据不可用(见 `app/models/credential.py:80`, `app/utils/password_crypto_utils.py:50`, `migrations/versions/20251219161048_baseline_production_schema.py:373`).
- P0: 容量域分区父表 `database_size_stats`/`database_size_aggregations` 已在迁移中补齐复合主键 `(id, 分区键)`,但 ORM 仍将 `id` 视为单列主键,存在 ORM identity 冲突与错误回表/更新的隐患(见 `migrations/versions/20251224164000_add_primary_keys_to_partitioned_capacity_tables.py:31`, `app/models/database_size_stat.py:47`, `app/models/database_size_aggregation.py:59`).
- P1: 多个核心列表页查询依赖 `%LIKE%`/`contains` + `OFFSET/LIMIT`,且标签过滤 join 方向缺少 `instance_tags.tag_id` 侧索引,在数据量增长后会出现"慢查询 + 写入变慢 + 业务页面卡顿"(见 `app/repositories/ledgers/accounts_ledger_repository.py:108`, `app/repositories/ledgers/database_ledger_repository.py:143`, `app/models/tag.py:183`).
- P1: "最新容量"查询目前采用 `GROUP BY + max(collected_at)` 再回表的形态,对按月分区的大表不友好,需要配套索引与查询形态调整,否则 dashboard/台账会随历史增长持续劣化(见 `app/repositories/ledgers/database_ledger_repository.py:166`).
- P1: 约束与一致性存在缺口: `database_size_aggregations.instance_id` 在 DB 侧未建立外键,且 `account_permission` 同时保存 `instance_id` 与 `instance_account_id` 但缺少"两者一致"的 DB 级约束,脏数据一旦产生将很难排查与修复(见 `migrations/versions/20251219161048_baseline_production_schema.py:593`, `migrations/versions/20251219161048_baseline_production_schema.py:1790`).

## II. 范围与方法

### 范围

- ORM 模型: `app/models/**`
- 迁移与基线: `migrations/**`
- 关键读写链路: `app/routes/**`, `app/services/**`, `app/repositories/**`
- 发布与基线对齐脚本(兼容/回退): `scripts/deploy/**`

### 方法(按步骤 A-E 输出)

### A. Schema 地图

#### A1. 关键实体清单(从代码推断)

- 用户与权限: `users`, `permission_configs`, `database_type_configs`
- 实例与连接: `instances`, `credentials`, `tags`, `instance_tags`
- 账户域: `instance_accounts`, `account_permission`, `account_change_log`, `account_classifications`, `classification_rules`, `account_classification_assignments`
- 同步与历史: `sync_sessions`, `sync_instance_records`, `unified_logs`
- 容量域(分区表): `database_size_stats`, `database_size_aggregations`, `instance_size_stats`, `instance_size_aggregations`

#### A2. Schema 概览(文字 ERD)

```text
credentials 1 --- N instances
instances 1 --- N instance_accounts
instances 1 --- N instance_databases
instances N --- N tags (via instance_tags)

instance_accounts 1 --- 1 account_permission (logical, via instance_account_id)
instances 1 --- N account_permission
instances 1 --- N account_change_log (logical, via instance_id + db_type + username)

account_classifications 1 --- N classification_rules
account_permission N --- N account_classifications (via account_classification_assignments)
users 1 --- N account_classification_assignments (assigned_by)

sync_sessions 1 --- N sync_instance_records (via session_id)
instances 1 --- N sync_instance_records

instances 1 --- N database_size_stats (partitioned by collected_date)
instances 1 --- N database_size_aggregations (partitioned by period_start, DB-side FK missing)
instances 1 --- N instance_size_stats (partitioned by collected_date)
instances 1 --- N instance_size_aggregations (partitioned by period_start)
```

#### A3. Schema 明细(表/字段/约束/索引/触发器)

> 说明: 下列结构以 `migrations/versions/20251219161048_baseline_production_schema.py` 为基线,并叠加后续迁移:
> - `20251224120000`: 删除 `credentials.instance_ids`
> - `20251224134000`: 聚合表 `calculated_at/created_at` 迁移为 `timestamptz`
> - `20251224164000`: 为 `database_size_stats`/`database_size_aggregations` 补齐复合主键

##### `users` (model: `User`)

- Columns: `id` int4 PK; `username` varchar(255) NN; `password` varchar(255) NN; `role` varchar(50) NN default 'user'; `created_at` timestamptz NN default now(); `last_login` timestamptz; `is_active` bool NN default true
- PK: `users_pkey(id)`
- Unique: `users_username_key(username)`
- Indexes: `ix_users_username(username)`

##### `credentials` (model: `Credential`)

- Columns: `id` int4 PK; `name` varchar(255) NN; `credential_type` varchar(50) NN; `db_type` varchar(50); `username` varchar(255) NN; `password` varchar(255) NN; `description` text; `category_id` int4; `is_active` bool NN default true; `created_at` timestamptz default now(); `updated_at` timestamptz default now(); `deleted_at` timestamptz
- PK: `credentials_pkey(id)`
- Unique: `credentials_name_key(name)` (同时存在冗余索引 `ix_credentials_name`)
- Indexes: `ix_credentials_name(name)`, `ix_credentials_credential_type(credential_type)`, `ix_credentials_db_type(db_type)`
- Triggers: `update_credentials_updated_at` (BEFORE UPDATE)
- Migration note: `instance_ids` 已在 `20251224120000` 删除

##### `instances` (model: `Instance`)

- Columns: `id` int4 PK; `name` varchar(255) NN; `db_type` varchar(50) NN; `host` varchar(255) NN; `port` int4 NN; `database_name` varchar(255); `database_version` varchar(1000); `main_version` varchar(20); `detailed_version` varchar(50); `sync_count` int4 NN default 0; `credential_id` int4; `description` text; `is_active` bool NN default true; `last_connected` timestamptz; `created_at` timestamptz default now(); `updated_at` timestamptz default now(); `deleted_at` timestamptz
- PK: `instances_pkey(id)`
- FK: `instances_credential_id_fkey(credential_id -> credentials.id)`
- Unique: `instances_name_key(name)` (同时存在冗余 unique index `ix_instances_name`)
- Indexes: `ix_instances_db_type(db_type)`, `ix_instances_name(name)`
- Triggers: `update_instances_updated_at` (BEFORE UPDATE)

##### `tags` (model: `Tag`, assoc: `instance_tags`)

- Columns: `id` int4 PK; `name` varchar(50) NN; `display_name` varchar(100) NN; `category` varchar(50) NN; `color` varchar(20) NN default 'primary'; `is_active` bool NN default true; `created_at` timestamptz default now(); `updated_at` timestamptz default now()
- PK: `tags_pkey(id)`
- Unique: `tags_name_key(name)` (同时存在冗余索引 `ix_tags_name`)
- Indexes: `ix_tags_name(name)`, `ix_tags_category(category)`
- Triggers: `update_tags_updated_at` (BEFORE UPDATE)

##### `instance_tags` (assoc table)

- Columns: `instance_id` int4 NN; `tag_id` int4 NN; `created_at` timestamptz default now()
- PK: `instance_tags_pkey(instance_id, tag_id)`
- FKs: `instance_tags_instance_id_fkey(instance_id -> instances.id)`, `instance_tags_tag_id_fkey(tag_id -> tags.id)`
- Indexes: (无单列索引; 目前仅复合主键)

##### `instance_accounts` (model: `InstanceAccount`)

- Columns: `id` int4 PK; `instance_id` int4 NN; `username` varchar(255) NN; `db_type` varchar(50) NN; `is_active` bool NN default true; `first_seen_at` timestamptz NN default now(); `last_seen_at` timestamptz NN default now(); `deleted_at` timestamptz; `created_at` timestamptz NN default now(); `updated_at` timestamptz NN default now()
- PK: `instance_accounts_pkey(id)`
- FK: `instance_accounts_instance_id_fkey(instance_id -> instances.id)`
- Unique: `uq_instance_account_instance_username(instance_id, db_type, username)`
- Indexes: `ix_instance_accounts_active(is_active)`, `ix_instance_accounts_last_seen(last_seen_at)`, `ix_instance_accounts_username(username)`

##### `account_permission` (model: `AccountPermission`)

- Columns: `id` int4 PK; `instance_id` int4 NN; `db_type` varchar(20) NN; `username` varchar(255) NN; `is_superuser` bool default false; `...`(多列 jsonb 权限快照); `last_sync_time` timestamptz default now(); `last_change_type` varchar(20) default 'add'; `last_change_time` timestamptz default now(); `instance_account_id` int4 NN; `is_locked` bool NN
- PK: `account_permission_pkey(id)`
- FKs: `fk_account_permission_instance(instance_id -> instances.id)`, `fk_account_permission_instance_account(instance_account_id -> instance_accounts.id, ON DELETE CASCADE)`
- Unique: `uq_current_account_sync` unique index `(instance_id, db_type, username)` (DB 为 unique index 形态,非 `ADD CONSTRAINT`)
- Indexes: `idx_instance_dbtype(instance_id, db_type)`, `idx_username(username)`, `idx_last_sync_time(last_sync_time)`, `idx_last_change_time(last_change_time)`, `ix_account_permission_is_locked(is_locked)`

##### `account_change_log` (model: `AccountChangeLog`)

- Columns: `id` int4 PK; `instance_id` int4 NN; `db_type` varchar(20) NN; `username` varchar(255) NN; `change_type` varchar(50) NN; `change_time` timestamptz default now(); `session_id` varchar(128); `status` varchar(20) default 'success'; `message` text; `privilege_diff` jsonb; `other_diff` jsonb
- PK: `account_change_log_pkey(id)`
- FK: `account_change_log_instance_id_fkey(instance_id -> instances.id)`
- Indexes: `idx_instance_dbtype_username_time(instance_id, db_type, username, change_time)`, `idx_change_type_time(change_type, change_time)`, `idx_username_time(username, change_time)`, 以及单列索引 `idx_account_change_log_*`

##### `account_classifications` (model: `AccountClassification`)

- Columns: `id` int4 PK; `name` varchar(100) NN; `description` text; `risk_level` varchar(20) NN default 'medium'; `color` varchar(20); `icon_name` varchar(50) default 'fa-tag'; `priority` int4 default 0; `is_system` bool NN default false; `is_active` bool NN default true; `created_at` timestamptz default now(); `updated_at` timestamptz default now()
- PK: `account_classifications_pkey(id)`
- Unique: `account_classifications_name_key(name)`
- Triggers: `update_account_classifications_updated_at` (BEFORE UPDATE)

##### `classification_rules` (model: `ClassificationRule`)

- Columns: `id` int4 PK; `classification_id` int4 NN; `db_type` varchar(20) NN; `rule_name` varchar(100) NN; `rule_expression` text NN; `is_active` bool NN default true; `created_at` timestamptz default now(); `updated_at` timestamptz default now()
- PK: `classification_rules_pkey(id)`
- FK: `classification_rules_classification_id_fkey(classification_id -> account_classifications.id)`
- Triggers: `update_classification_rules_updated_at` (BEFORE UPDATE)

##### `account_classification_assignments` (model: `AccountClassificationAssignment`)

- Columns: `id` int4 PK; `account_id` int4 NN; `classification_id` int4 NN; `rule_id` int4; `assigned_by` int4; `assignment_type` varchar(20) NN default 'auto'; `confidence_score` float4; `notes` text; `batch_id` varchar(36); `is_active` bool default true; `assigned_at` timestamptz NN; `created_at` timestamptz default now(); `updated_at` timestamptz default now()
- PK: `account_classification_assignments_pkey(id)`
- FKs: `account_classification_assignments_account_id_fkey(account_id -> account_permission.id)`, `account_classification_assignments_classification_id_fkey(classification_id -> account_classifications.id)`, `account_classification_assignments_assigned_by_fkey(assigned_by -> users.id)`, `fk_account_classification_assignments_rule_id(rule_id -> classification_rules.id, ON DELETE SET NULL)`
- Unique: `unique_account_classification_batch(account_id, classification_id, batch_id)`
- Indexes: `idx_account_classification_assignments_account_id(account_id)`, `idx_account_classification_assignments_classification_id(classification_id)`, `idx_account_classification_assignments_is_active(is_active)`
- Triggers: `update_account_classification_assignments_updated_at` (BEFORE UPDATE)

##### `permission_configs` (model: `PermissionConfig`)

- Columns: `id` int4 PK; `db_type` varchar(50) NN; `category` varchar(50) NN; `permission_name` varchar(255) NN; `description` text; `is_active` bool default true; `sort_order` int4 default 0; `created_at` timestamptz default now(); `updated_at` timestamptz default now()
- PK: `permission_configs_pkey(id)`
- Unique: `uq_permission_config(db_type, category, permission_name)`
- Indexes: `idx_permission_config_db_type(db_type)`, `idx_permission_config_category(category)`
- Triggers: `update_permission_configs_updated_at` (BEFORE UPDATE)

##### `database_type_configs` (model: `DatabaseTypeConfig`)

- Columns: `id` int4 PK; `name` varchar(50) NN; `display_name` varchar(100) NN; `driver` varchar(50) NN; `default_port` int4 NN; `default_schema` varchar(50) NN; `connection_timeout` int4 default 30; `description` text; `icon` varchar(50) default 'fa-database'; `color` varchar(20) default 'primary'; `features` text; `is_active` bool default true; `is_system` bool default false; `sort_order` int4 default 0; `created_at` timestamptz default now(); `updated_at` timestamptz default now()
- PK: `database_type_configs_pkey(id)`
- Unique: `database_type_configs_name_key(name)`
- Triggers: `update_database_type_configs_updated_at` (BEFORE UPDATE)

##### `sync_sessions` (model: `SyncSession`)

- Columns: `id` int4 PK; `session_id` varchar(36) NN; `sync_type` varchar(20) NN; `sync_category` varchar(20) NN default 'account'; `status` varchar(20) NN default 'running'; `started_at` timestamptz NN default now(); `completed_at` timestamptz; `total_instances` int4 default 0; `successful_instances` int4 default 0; `failed_instances` int4 default 0; `created_by` int4; `created_at` timestamptz default now(); `updated_at` timestamptz default now()
- PK: `sync_sessions_pkey(id)`
- Unique: `sync_sessions_session_id_key(session_id)`
- Checks: `sync_sessions_status_check`, `sync_sessions_sync_type_check`, `sync_sessions_sync_category_check`
- Indexes: `idx_sync_sessions_session_id(session_id)`, `idx_sync_sessions_status(status)`, `idx_sync_sessions_sync_category(sync_category)`, `idx_sync_sessions_sync_type(sync_type)`, `idx_sync_sessions_created_at(created_at)`
- Triggers: `update_sync_sessions_updated_at` (BEFORE UPDATE)

##### `sync_instance_records` (model: `SyncInstanceRecord`)

- Columns: `id` int4 PK; `session_id` varchar(36) NN; `instance_id` int4 NN; `instance_name` varchar(255); `sync_category` varchar(20) NN default 'account'; `status` varchar(20) NN default 'pending'; `started_at` timestamptz; `completed_at` timestamptz; `items_synced` int4 default 0; `items_created` int4 default 0; `items_updated` int4 default 0; `items_deleted` int4 default 0; `error_message` text; `sync_details` jsonb; `created_at` timestamptz default now()
- PK: `sync_instance_records_pkey(id)`
- FKs: `sync_instance_records_session_id_fkey(session_id -> sync_sessions.session_id, ON DELETE CASCADE)`, `sync_instance_records_instance_id_fkey(instance_id -> instances.id, ON DELETE CASCADE)`
- Checks: `sync_instance_records_status_check`, `sync_instance_records_sync_category_check`
- Indexes: `idx_sync_instance_records_session_id(session_id)`, `idx_sync_instance_records_instance_id(instance_id)`, `idx_sync_instance_records_status(status)`, `idx_sync_instance_records_sync_category(sync_category)`, `idx_sync_instance_records_created_at(created_at)`

##### `unified_logs` (model: `UnifiedLog`)

- Type: `log_level` enum (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- Columns: `id` int4 PK; `timestamp` timestamptz NN; `level` log_level NN; `module` varchar(100) NN; `message` text NN; `traceback` text; `context` jsonb; `created_at` timestamptz NN default now()
- PK: `unified_logs_pkey(id)`
- Checks: `unified_logs_level_check`
- Indexes: `idx_timestamp_level_module(timestamp, level, module)`, `idx_timestamp_module(timestamp, module)`, `idx_level_timestamp(level, timestamp)`, 以及单列索引 `idx_unified_logs_timestamp`, `idx_unified_logs_level`, `idx_unified_logs_module`, `idx_unified_logs_created_at`

##### `instance_databases` (model: `InstanceDatabase`)

- Columns: `id` int4 PK; `instance_id` int4 NN; `database_name` varchar(255) NN; `is_active` bool NN default true; `first_seen_date` date NN default current_date; `last_seen_date` date NN default current_date; `deleted_at` timestamptz; `created_at` timestamptz default now(); `updated_at` timestamptz default now()
- PK: `instance_databases_pkey(id)`
- FK: `instance_databases_instance_id_fkey(instance_id -> instances.id, ON DELETE CASCADE)`
- Unique: `instance_databases_instance_id_database_name_key(instance_id, database_name)`
- Indexes: `ix_instance_databases_instance_id(instance_id)`, `ix_instance_databases_database_name(database_name)`, `ix_instance_databases_active(is_active)`, `ix_instance_databases_last_seen(last_seen_date)`

##### `database_size_stats` (partitioned, model: `DatabaseSizeStat`)

- Partition: RANGE(`collected_date`) by month
- Columns: `id` int8; `instance_id` int4 NN; `database_name` varchar(255) NN; `size_mb` int8 NN; `data_size_mb` int8; `log_size_mb` int8; `collected_date` date NN; `collected_at` timestamptz NN default now(); `created_at` timestamptz NN default now(); `updated_at` timestamptz NN default now()
- PK: `database_size_stats_pkey(id, collected_date)` (added in `20251224164000`)
- FK: `database_size_stats_instance_id_fkey(instance_id -> instances.id)`
- Unique: `uq_daily_database_size(instance_id, database_name, collected_date)`
- Indexes(parent): `ix_database_size_stats_collected_date(collected_date)`, `ix_database_size_stats_instance_date(instance_id, collected_date)`, `ix_database_size_stats_instance_db(instance_id, database_name)`
- Triggers: `trg_update_instance_database_last_seen` (AFTER INSERT)

##### `database_size_aggregations` (partitioned, model: `DatabaseSizeAggregation`)

- Partition: RANGE(`period_start`) by month
- Columns: `id` int8; `instance_id` int4 NN; `database_name` varchar(255) NN; `period_type` varchar(20) NN; `period_start` date NN; `period_end` date NN; `avg_size_mb`/`max_size_mb`/`min_size_mb` int8 NN; `data_count` int4 NN; `...`(增量字段 numeric/int8); `calculated_at` timestamptz NN; `created_at` timestamptz NN
- PK: `database_size_aggregations_pkey(id, period_start)` (added in `20251224164000`)
- FK: (DB 侧缺失,当前仅 ORM 声明了 `instances.id` 外键)
- Unique: `uq_database_size_aggregation(instance_id, database_name, period_type, period_start)`
- Indexes(parent): `ix_database_size_aggregations_id(id)`, `ix_database_size_aggregations_instance_period(instance_id, period_type, period_start)`, `ix_database_size_aggregations_period_type(period_type, period_start)`
- Migration note: `calculated_at/created_at` 已在 `20251224134000` 迁移为 `timestamptz`

##### `instance_size_stats` (partitioned, model: `InstanceSizeStat`)

- Partition: RANGE(`collected_date`) by month
- Columns: `id` int4; `instance_id` int4 NN; `total_size_mb` int4 NN default 0; `database_count` int4 NN default 0; `collected_date` date NN; `collected_at` timestamptz NN default now(); `is_deleted` bool NN default false; `deleted_at` timestamptz; `created_at` timestamptz default now(); `updated_at` timestamptz default now()
- PK: `instance_size_stats_pkey(id, collected_date)`
- FK: `instance_size_stats_instance_id_fkey(instance_id -> instances.id, ON DELETE CASCADE)`
- Unique(partial): `uq_instance_size_stats_instance_date(instance_id, collected_date) WHERE is_deleted = false`
- Indexes(parent): `ix_instance_size_stats_instance_date(instance_id, collected_date)`, `ix_instance_size_stats_collected_date(collected_date)`, `ix_instance_size_stats_deleted(is_deleted)`, `ix_instance_size_stats_instance_id(instance_id)`, `ix_instance_size_stats_total_size(total_size_mb)`
- Triggers: `instance_size_stats_partition_trigger` (BEFORE INSERT, auto-create monthly partition)

##### `instance_size_aggregations` (partitioned, model: `InstanceSizeAggregation`)

- Partition: RANGE(`period_start`) by month
- Columns: `id` int8; `instance_id` int4 NN; `period_type` varchar(20) NN; `period_start` date NN; `period_end` date NN; `total_size_mb`/`avg_size_mb`/`max_size_mb`/`min_size_mb` int8 NN; `data_count` int4 NN; `database_count` int4 NN; `...`(变化字段 numeric/int); `trend_direction` varchar(20); `calculated_at` timestamptz NN; `created_at` timestamptz NN
- PK: `instance_size_aggregations_pkey(id, period_start)`
- FK: `instance_size_aggregations_instance_id_fkey(instance_id -> instances.id)`
- Unique: `uq_instance_size_aggregation(instance_id, period_type, period_start)`
- Indexes(parent): `ix_instance_size_aggregations_id(id)`, `ix_instance_size_aggregations_instance_period(instance_id, period_type, period_start)`, `ix_instance_size_aggregations_period_type(period_type, period_start)`
- Migration note: `calculated_at/created_at` 已在 `20251224134000` 迁移为 `timestamptz`

### B. 关键用例反推(Top 10 查询/写入路径)

> 说明: 这里按"用户访问频率 + 数据量敏感度 + 读写放大风险"选取 Top 10. 未提供真实访问与表规模时,瓶颈判断以"未来 10x-100x 数据增长"为假设.

1) 实例列表(筛选/搜索/标签/排序): `app/repositories/instances_repository.py:115`
   - Tables: `instances`, `instance_tags`, `tags`, `sync_instance_records`, `instance_databases`, `instance_accounts`
   - 依赖: `ix_instances_name`, `ix_instances_db_type`, `instance_tags_pkey`, `ix_tags_name`
   - 风险: `ILIKE '%term%'` 无法走 btree; tags join 方向依赖 `instance_tags.tag_id` 侧索引; `OFFSET` 深分页退化

2) 账户台账列表(筛选/搜索/标签/分类): `app/repositories/ledgers/accounts_ledger_repository.py:86`
   - Tables: `account_permission`, `instance_accounts`, `instances`, `instance_tags`, `tags`, `account_classification_assignments`, `account_classifications`
   - 依赖: `idx_instance_dbtype`, `idx_username`, `ix_instance_accounts_active`, `ix_tags_name`
   - 风险: `contains` 触发 `%LIKE%`; 标签过滤 join 缺少 `instance_tags(tag_id)`; 多 join + `OFFSET` 在账号量大时明显变慢

3) 实例详情-账户列表(是否包含权限详情/搜索/排序): `app/repositories/instance_accounts_repository.py:65`
   - Tables: `account_permission`, `instance_accounts`, `account_change_log`
   - 依赖: `idx_username`, `idx_last_change_time`, `ix_instance_accounts_active`, `idx_instance_dbtype_username_time`
   - 风险: `ILIKE '%term%'` 扫描用户名; 变更日志若不做归档会持续膨胀

4) 数据库台账列表 + 最新容量回表: `app/repositories/ledgers/database_ledger_repository.py:35`, `app/repositories/ledgers/database_ledger_repository.py:166`
   - Tables: `instance_databases`, `instances`, `database_size_stats`(partitioned), `instance_tags`, `tags`
   - 依赖: `instance_databases_instance_id_database_name_key`, `ix_database_size_stats_instance_db`
   - 风险: `GROUP BY(instance_id, database_name) + max(collected_at)` 需要扫历史分区; tags join 同样依赖 `instance_tags(tag_id)`

5) 数据库容量聚合列表/摘要(Top N): `app/repositories/capacity_databases_repository.py:41`, `app/repositories/capacity_databases_repository.py:89`
   - Tables: `database_size_aggregations`(partitioned), `instances`, `instance_databases`
   - 依赖: `ix_database_size_aggregations_instance_period`, `instance_databases_instance_id_database_name_key`
   - 风险: `GROUP BY + max(period_end)` 再 `tuple IN` 回表; 未来分区增多后对计划与内存压力更大

6) 历史日志检索(时间窗口/级别/模块/关键字): `app/repositories/history_logs_repository.py:27`
   - Tables: `unified_logs`
   - 依赖: `idx_timestamp_level_module`, `idx_timestamp_module`, `idx_level_timestamp`
   - 风险: `LIKE '%term%'` + `context::text LIKE` 难以利用现有 btree; 日志表缺少生命周期策略时,查询会持续劣化

7) 同步会话列表(筛选/排序): `app/repositories/history_sessions_repository.py:24`
   - Tables: `sync_sessions`
   - 依赖: `idx_sync_sessions_created_at`, `idx_sync_sessions_status`, `idx_sync_sessions_sync_category`
   - 风险: `OFFSET` 深分页; 但数据量通常可控

8) 容量采集写入(upsert): `app/services/database_sync/persistence.py:32`
   - Tables: `database_size_stats`(partitioned), `instance_size_stats`(partitioned), `instance_databases`
   - 依赖: `uq_daily_database_size`, `uq_instance_size_stats_instance_date`(partial), 分区存在性,以及分区索引/约束继承
   - 风险: 月初缺分区导致插入失败; 分区索引未对齐会导致 `ON CONFLICT` 失败或变慢

9) 账户权限快照写入(增量 + 变更日志): `app/services/accounts_sync/permission_manager.py:308`
   - Tables: `account_permission`, `account_change_log`, `instance_accounts`
   - 依赖: `uq_current_account_sync`, `idx_instance_dbtype_username_time`
   - 风险: 大量 jsonb 列更新导致写放大; 缺少"一致性约束"时产生脏数据难排查

10) 分区创建/清理/健康监控(运维写入): `app/tasks/partition_management_tasks.py:49`
   - Tables: 4 张分区父表 + `pg_catalog` 元数据
   - 依赖: Postgres 分区 DDL,以及分区上索引/约束的创建策略
   - 风险: 若在业务高峰执行 drop/create 分区,可能引发锁与计划抖动; 需要执行窗口与演练

### C. 核心实体逐条审查(输出在 III,并按 P0/P1/P2 汇总)

- 逐个实体对齐: 职责边界,字段可空性/默认值,是否存在"万能表/过度 JSON 化",业务唯一性与幂等约束是否在 DB 层兜底.

### D. 迁移可演进审查(输出在 III,并按 P0/P1/P2 汇总)

- 检查点: 是否可回滚,是否支持滚动发布,是否存在大表 `ALTER` 风险,分区表约束/索引是否可在不中断写入的情况下补齐.

### E. 输出问题清单与路线图(输出在 IV,<= 8 条行动项)

## III. 发现清单(按 P0/P1/P2)

### P0

#### 模型设计问题清单

##### P0-1(Columns, Governance) 凭据密文长度与密钥管理存在"数据不可用"风险

- 证据:
  - `credentials.password` 为 `varchar(255)` (DB): `migrations/versions/20251219161048_baseline_production_schema.py:373`
  - ORM 同样限制为 `String(255)`: `app/models/credential.py:80`
  - 加密实现返回 `base64.b64encode(Fernet.encrypt(...))`,密文长度随明文长度增长: `app/utils/password_crypto_utils.py:66`
  - 未设置 `PASSWORD_ENCRYPTION_KEY` 时会生成临时密钥并提示"重启后无法解密": `app/utils/password_crypto_utils.py:50`
- 影响:
  - 密文被截断后无法解密,连接测试/同步会直接失败,且难以自动恢复.
  - 密钥未配置会导致"重启后全量凭据不可用",属于高风险的配置/数据治理缺陷.
- 根因:
  - DB 列类型/长度与加密产物尺寸未对齐; 同时缺少对关键密钥配置的强校验与启动门禁.
- 建议:
  - 结构侧: 将 `credentials.password` 调整为 `text`(推荐)或至少 `varchar(1024)`,并补充长度验证(防止异常写入).
  - 配置侧: 在 `app/settings.py` 增加 `PASSWORD_ENCRYPTION_KEY` 的必须校验(生产环境 MUST),并提供轮换策略说明(ADR).
- 验证:
  - SQL: `SELECT max(length(password)) FROM credentials;` 确认能超过 255 且不截断.
  - 行为: 使用长度 64/128 的密码创建凭据,重启服务后执行连接测试,确认可解密且一致.
  - 回归: 跑 `pytest -m unit` 覆盖 `Credential.set_password/get_plain_password` 的长密码用例.

##### P0-2(Migrations, Integrity) 分区父表复合主键已落地,但 ORM 仍用单列主键,存在 identity 冲突风险

- 证据:
  - 迁移为 `database_size_stats`/`database_size_aggregations` 增加 PK `(id, 分区键)`: `migrations/versions/20251224164000_add_primary_keys_to_partitioned_capacity_tables.py:31`
  - ORM `DatabaseSizeStat` 仅以 `id` 为主键: `app/models/database_size_stat.py:47`
  - ORM `DatabaseSizeAggregation` 仅以 `id` 为主键,`period_start` 非 PK: `app/models/database_size_aggregation.py:59`, `app/models/database_size_aggregation.py:65`
- 影响:
  - 只要出现相同 `id` 不同分区键的两行,SQLAlchemy identity map 会把两行视为同一对象,导致读取/更新串线.
  - 即使当前序列"看似全局递增",仍存在运维/修复脚本写入或序列重置带来的碰撞可能; 风险随时间累积.
- 根因:
  - 分区表在 DB 侧采用复合主键保证语义正确,但 ORM 映射未同步调整.
- 建议:
  - 立即对齐 ORM: 将 `DatabaseSizeStat` 改为复合主键 `(id, collected_date)`,将 `DatabaseSizeAggregation` 改为复合主键 `(id, period_start)`.
  - 同步检查所有基于主键的读路径(例如 `Session.get`, backref, 以及任何按 `id` 查询的 API).
- 验证:
  - SQL: `SELECT id, count(*) FROM database_size_stats GROUP BY id HAVING count(*) > 1;` 若存在结果,当前 ORM 映射必然有问题.
  - 单测: 针对两条同 `id` 不同 `collected_date` 的行(可用 sqlite 不易复现,建议引入 Postgres integration test)验证 ORM 行为.
  - 迁移演练: 在 staging 跑 `flask db upgrade` 后,执行典型容量列表/趋势查询,确认无回归.

#### 兼容/防御/回退/适配清单

| 位置 | 类型 | 描述 | 建议 |
| --- | --- | --- | --- |
| `tests/conftest.py:13` | 环境回退 | 单测默认使用 SQLite,无法覆盖 Postgres 分区/enum/jsonb/触发器语义 | 增加 Postgres integration 测试(至少覆盖分区表 upsert, enum, jsonb, 关键索引),并在 CI 跑一条最小 `flask db upgrade` 演练 |
| `app/utils/password_crypto_utils.py:50` | 配置兜底 | 未设置 `PASSWORD_ENCRYPTION_KEY` 时自动生成临时密钥,导致重启后历史密文不可解密 | 在生产环境强制要求配置,并在启动时 fail-fast; 同时补充密钥轮换与应急预案 |

### P1

#### 模型设计问题清单

##### P1-1(Performance) 标签过滤缺少 `instance_tags(tag_id)` 侧索引,join 方向会退化

- 证据:
  - 标签过滤通过 `Tag.id == instance_tags.c.tag_id` 连接并按 `Tag.name in (...)` 过滤: `app/repositories/ledgers/accounts_ledger_repository.py:146`, `app/repositories/ledgers/database_ledger_repository.py:154`
  - `instance_tags` 仅有复合主键 `(instance_id, tag_id)`,缺少 `tag_id` 前导索引: `migrations/versions/20251219161048_baseline_production_schema.py:1452`, `app/models/tag.py:183`
- 影响:
  - 当按 tag 反查实例/台账时,planner 很难利用 `(instance_id, tag_id)` 的前导列,容易走 hash join 或 seq scan.
  - 标签使用越广,该路径越接近"常用且慢",会拖垮多个列表页.
- 根因:
  - 关联表索引仅覆盖 instance_id 前导访问,未覆盖 tag_id 前导访问.
- 建议:
  - 新增索引: `CREATE INDEX CONCURRENTLY ix_instance_tags_tag_id ON instance_tags(tag_id);`
  - 若存在 tag_id + instance_id 的复合访问,可补 `CREATE INDEX CONCURRENTLY ix_instance_tags_tag_id_instance_id ON instance_tags(tag_id, instance_id);`
- 验证:
  - EXPLAIN: 对 `tags` 筛选的台账查询做 `EXPLAIN (ANALYZE, BUFFERS)` 对比索引前后.
  - 观测: 统计 tags 过滤 API 的 p95/p99 与 rows scanned.

##### P1-2(Performance) 多处搜索使用 `%LIKE%`/`contains`,需要明确索引策略(Trgm/FTS)

- 证据:
  - 账户台账搜索: `contains(search)` 同时作用于 `username`, `instance.name`, `instance.host`: `app/repositories/ledgers/accounts_ledger_repository.py:108`
  - 数据库台账搜索: `ilike('%term%')` 匹配 `database_name/name/host`: `app/repositories/ledgers/database_ledger_repository.py:143`
  - 历史日志搜索: `message LIKE '%term%'` 以及 `context::text LIKE '%term%'`: `app/repositories/history_logs_repository.py:39`
- 影响:
  - btree 索引无法支持前导通配符,数据增长后会出现不可避免的全表/全分区扫描.
- 根因:
  - 缺少统一的"搜索策略 ADR": 是前缀匹配,还是 trigram,还是全文检索; 目前实现混用且无索引配套.
- 建议:
  - 短期(止血): 对高频字段启用 `pg_trgm` + `GIN`/`GiST` trigram 索引(需评估扩展权限与写入开销).
  - 中期: 对日志与台账提供更明确的搜索入口(字段化搜索/前缀搜索/全文检索),避免把所有字段都 `%LIKE%`.
- 验证:
  - 选 3 条代表性查询做 `EXPLAIN (ANALYZE, BUFFERS)` 留存到 `docs/reports/artifacts/` 作为基线.
  - 对比上线前后 pg_stat_statements Top N(按 mean/max, rows, calls).

##### P1-3(Performance) "最新容量"回表模式对分区大表不友好,需要索引与 SQL 形态调整

- 证据:
  - 最新容量通过子查询 `group_by(instance_id, database_name) + max(collected_at)` 再 join 回表: `app/repositories/ledgers/database_ledger_repository.py:166`
  - `database_size_stats` 为按月分区大表,且 parent 侧索引不包含 `collected_at`: `migrations/versions/20251219161048_baseline_production_schema.py:1688`
- 影响:
  - 数据增长后,每次台账查询都可能触发多分区聚合与回表,延迟与成本线性上升.
- 根因:
  - 查询形态未针对"最新一条"优化; 索引也未覆盖 `ORDER BY collected_at DESC` 的访问路径.
- 建议:
  - SQL 形态: 使用 `DISTINCT ON (instance_id, database_name) ... ORDER BY collected_at DESC` 或 window function(`row_number() over (...) = 1`)替代 `group_by + max`.
  - 索引: 在分区上增加 `(instance_id, database_name, collected_at DESC)` 方向索引(可由分区管理任务在新分区创建时自动补齐).
- 验证:
  - 对比 `EXPLAIN (ANALYZE, BUFFERS)` 的扫描分区数与总 IO.
  - 压测: 选择 10x 数据量的 staging(可用复制数据/生成数据)测 p95.

##### P1-4(Integrity, Modeling) `database_size_aggregations` DB 侧缺少外键,存在孤儿数据与一致性缺口

- 证据:
  - 表定义仅声明 `instance_id int4 NOT NULL`,但未建立 `REFERENCES instances(id)`: `migrations/versions/20251219161048_baseline_production_schema.py:593`
  - 外键段落仅包含 `database_size_stats` 而不包含 `database_size_aggregations`: `migrations/versions/20251219161048_baseline_production_schema.py:1828`
  - ORM 声明了外键: `app/models/database_size_aggregation.py:60`
- 影响:
  - 可能产生无法关联到实例的聚合行,导致聚合页面/统计口径异常且难以定位.
  - ORM 与 DB 约束不一致,会导致 autogenerate 漂移或开发误判.
- 根因:
  - 大表/分区表上是否加 FK 的策略未被明确(性能顾虑 vs 数据完整性).
- 建议:
  - 若允许: 为父表增加 `FOREIGN KEY (instance_id) REFERENCES instances(id) NOT VALID`,再分批 `VALIDATE CONSTRAINT`(避免长锁).
  - 若不允许: 在 ADR 中明确"容量聚合表不加 FK"并在写入链路做强校验(写入前检查 instance 存在).
- 验证:
  - SQL: `SELECT a.instance_id FROM database_size_aggregations a LEFT JOIN instances i ON i.id = a.instance_id WHERE i.id IS NULL LIMIT 10;`
  - 迁移演练: 在有数据的 staging 上执行 `NOT VALID` + `VALIDATE`.

##### P1-5(Concurrency, Integrity) `account_permission` 双标识字段缺少 DB 级一致性约束

- 证据:
  - `account_permission` 同时保存 `instance_id` 与 `instance_account_id`,且两者都参与业务查询: `migrations/versions/20251219161048_baseline_production_schema.py:323`, `migrations/versions/20251219161048_baseline_production_schema.py:344`
  - 外键仅约束 `instance_account_id -> instance_accounts.id`,无法保证 `account_permission.instance_id == instance_accounts.instance_id`: `migrations/versions/20251219161048_baseline_production_schema.py:1790`
- 影响:
  - 任何写入 bug/并发竞态一旦写出不一致,读路径会出现"看似有数据但 join 丢失/统计不准",排查成本极高.
- 根因:
  - 为了查询便利冗余保存 `instance_id`,但未补齐"冗余一致性"约束.
- 建议:
  - 短期: 增加组合外键约束: 先在 `instance_accounts` 上补一个 `UNIQUE(id, instance_id)`,再在 `account_permission` 上加 `FOREIGN KEY (instance_account_id, instance_id) REFERENCES instance_accounts(id, instance_id)`.
  - 中期: 评估是否可以移除 `account_permission.instance_id`,改为通过 `instance_account_id` 反查,避免冗余字段.
- 验证:
  - SQL: `SELECT ap.id FROM account_permission ap JOIN instance_accounts ia ON ia.id = ap.instance_account_id WHERE ia.instance_id <> ap.instance_id LIMIT 10;`
  - 写入侧: 对同步写入增加断言(写入前后校验 instance_id 一致).

#### 兼容/防御/回退/适配清单

| 位置 | 类型 | 描述 | 建议 |
| --- | --- | --- | --- |
| `scripts/deploy/update-prod-flask.sh:345` | 基线兼容 | 通过检测 `credentials.instance_ids`/`database_size_aggregations.calculated_at` 类型推断 stamp revision,用于避免重复跑 baseline | 建议把该推断逻辑收敛到一份"版本判定表"(随迁移更新),并在每次新增迁移时补齐用例 |
| `app/static/js/modules/views/history/sessions/sync-sessions.js:512` | 前后端状态兼容 | UI 侧将 `pending/paused` 视为 running,但 DB 侧 `sync_sessions_status_check` 不包含这些值 | 明确 `sync_sessions.status` 的唯一来源与可选集合,删除无效状态或在 API 层做映射,避免前端误判 |

### P2

#### 模型设计问题清单

##### P2-1(Performance) 冗余 unique index/unique constraint 叠加,增加写入与维护成本

- 证据:
  - `instances.name` 同时存在 unique index 与 unique constraint: `migrations/versions/20251219161048_baseline_production_schema.py:1462`, `migrations/versions/20251219161048_baseline_production_schema.py:1476`
  - `credentials.name` 同时存在普通 index 与 unique constraint: `migrations/versions/20251219161048_baseline_production_schema.py:1364`, `migrations/versions/20251219161048_baseline_production_schema.py:1378`
  - `tags.name` 同时存在 index 与 unique constraint: `migrations/versions/20251219161048_baseline_production_schema.py:1589`, `migrations/versions/20251219161048_baseline_production_schema.py:1603`
- 影响:
  - 写入时重复维护索引,影响 insert/update 性能; 也会增加磁盘占用与 vacuum 成本.
- 根因:
  - 基线 SQL 来自导出,可能包含"索引 + 约束"重复表达.
- 建议:
  - 逐表确认冗余是否可删除(优先保留约束创建的索引),并通过新迁移在低峰清理.
- 验证:
  - SQL: 查询 `pg_indexes`/`pg_constraint` 对比是否重复覆盖相同列.
  - `EXPLAIN` 与写入压测对比删除前后.

##### P2-2(Naming, Maintainability) `account_permission.id` 序列命名与表语义不一致,增加维护成本

- 证据:
  - `account_permission.id` 使用 `current_account_sync_data_id_seq`: `migrations/versions/20251219161048_baseline_production_schema.py:322`
- 影响:
  - 运维排障与 schema 认知成本上升,新成员容易误判对象用途.
- 根因:
  - 历史表/序列重命名后未清理遗留对象名.
- 建议:
  - 在不影响业务的前提下重命名 sequence/index(单独迁移),并更新文档/脚本引用.
- 验证:
  - SQL: `ALTER SEQUENCE ... RENAME TO ...` 后跑全量同步与迁移演练.

##### P2-3(Consistency) 分区创建策略存在"DB trigger + 应用任务"双轨,建议统一单一真源

- 证据:
  - `instance_size_stats` 存在 BEFORE INSERT 触发器自动建分区: `migrations/versions/20251219161048_baseline_production_schema.py:983`, `migrations/versions/20251219161048_baseline_production_schema.py:1767`
  - 应用侧也提供分区创建任务/接口,覆盖 4 张分区表: `app/tasks/partition_management_tasks.py:49`, `app/services/partition_management_service.py:100`
- 影响:
  - 双轨策略易产生"一边变更,另一边遗忘"的漂移; 也会让分区 DDL 行为难以预测与演练.
- 根因:
  - 基线导出保留了部分 trigger,同时项目又实现了应用侧分区管理.
- 建议:
  - 明确采用一种策略作为真源(推荐应用侧任务,可观测且易灰度),并清理另一侧的遗留函数/触发器.
- 验证:
  - 在 staging 禁用 trigger 后,验证分区任务能覆盖所有分区表并正确创建索引/约束.

#### 兼容/防御/回退/适配清单

| 位置 | 类型 | 描述 | 建议 |
| --- | --- | --- | --- |
| `migrations/versions/20251219161048_baseline_production_schema.py:1850` | 迁移回退 | baseline 迁移不提供 downgrade | 在 runbook 中明确"回滚靠新迁移",并为高风险变更提供专用回滚迁移模板 |

## IV. 建议与后续行动

### 缺口地图(建议补写的建模规范/ADR 标题)

- 主键策略(自增 vs UUID,分区表复合主键约束)
- 密文与敏感字段治理(字段类型,长度,加密密钥管理与轮换)
- JSONB 使用规范(JSON vs JSONB,索引与查询准则)
- 软删除与审计字段规范(`is_active/is_deleted/deleted_at`,partial unique index)
- 分区表索引与分区创建策略(父表索引,新分区索引自动化,触发器 vs 任务)
- 搜索策略(前缀匹配 vs pg_trgm vs 全文检索,以及索引成本)
- 大表迁移分阶段策略(零停机,`NOT VALID`/`VALIDATE`,并发建索引)
- 数据保留与归档策略(容量历史,日志,变更日志)

### 最小可执行路线图(<= 8 条,按 P0 -> P2)

1) P0: 扩容 `credentials.password` 为 `text` 并在生产强制校验 `PASSWORD_ENCRYPTION_KEY`,补充单测与回滚预案
2) P0: 对齐 ORM 主键映射: `DatabaseSizeStat(id, collected_date)`, `DatabaseSizeAggregation(id, period_start)`,并补一条 Postgres integration test
3) P1: 为 `instance_tags` 增加 `tag_id` 侧索引(优先 `CONCURRENTLY`),验证 accounts/database ledger tags 过滤的执行计划
4) P1: 统一"搜索索引"方案: 先为 `account_permission.username`, `instances.name/host`, `instance_databases.database_name` 选定 trigram 或前缀策略并落索引
5) P1: 重写"最新容量"查询为 `DISTINCT ON`/window function,并为分区补 `(instance_id, database_name, collected_at desc)` 索引策略
6) P1: 补齐 `database_size_aggregations.instance_id` 外键策略(加 FK 或写入强校验+ADR),并跑一次数据一致性扫描 SQL
7) P1: 为 `account_permission` 增加一致性约束(组合 FK 或 trigger),同时补齐异常数据巡检 SQL 与修复脚本
8) P2: 清理冗余索引/约束与遗留命名(sequence/index),并在 `docs/reference/database/` 更新最终口径

## V. 证据与数据来源

- 代码与模型:
  - `app/models/credential.py`
  - `app/utils/password_crypto_utils.py`
  - `app/models/database_size_stat.py`
  - `app/models/database_size_aggregation.py`
  - `app/models/tag.py`
  - `app/repositories/ledgers/accounts_ledger_repository.py`
  - `app/repositories/ledgers/database_ledger_repository.py`
  - `app/repositories/history_logs_repository.py`
  - `app/tasks/partition_management_tasks.py`
- 迁移与基线:
  - `migrations/versions/20251219161048_baseline_production_schema.py`
  - `migrations/versions/20251224120000_drop_credentials_instance_ids.py`
  - `migrations/versions/20251224134000_convert_aggregation_timestamps_to_timestamptz.py`
  - `migrations/versions/20251224164000_add_primary_keys_to_partitioned_capacity_tables.py`
- 部署与兼容脚本:
  - `scripts/deploy/update-prod-flask.sh`
- 说明:
  - 本报告未接入线上真实 `pg_stat_statements`/表行数/写入 QPS,性能瓶颈判断基于代码形态与分区表增长规律. 建议在后续行动中补齐"数据规模预期"与"慢查询证据"(EXPLAIN, pg_stat_statements Top N)并沉淀到 `docs/reports/artifacts/`.
