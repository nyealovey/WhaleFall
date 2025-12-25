# PostgreSQL Schema 基线与迁移使用说明

本文用于说明当前仓库中 **PostgreSQL Schema 的“基线来源”**、**全新部署建库方式**、以及 **Alembic（Flask-Migrate）如何与初始化脚本配合**。

## 1. 基线来源（Source of Truth）

- 生产库结构导出（权威基准）：`docs/reports/artifacts/public.sql`
  - Navicat 导出的 public schema DDL。
  - 包含 `DROP ...`、`ALTER ... OWNER TO ...`、`SELECT setval(...)` 等内容，**不建议直接用于建库**。
- 全新部署建库脚本（可执行 DDL）：`sql/init_postgresql.sql`（基础结构）+ `sql/init_postgresql_partitions_2025_07.sql`（月份分区子表）
  - 由 `docs/reports/artifacts/public.sql` 清洗生成：**移除 `DROP *` 与序列 `setval`**，仅保留 DDL（表/索引/约束/函数/触发器/分区等）。
- Alembic 基线迁移（全新历史）：`migrations/versions/20251219161048_baseline_production_schema.py`
  - 仅包含一个基线 revision（`20251219161048`），用于让 Alembic 版本与“当前生产库结构”对齐。

## 2. 全新部署（空库）建库方式

二选一即可，不要重复执行：

### 方案 A：用 `sql/init_postgresql.sql` 建库（推荐用于“纯初始化”）

1) 对空库执行（先基础结构，后月份分区子表）：

`psql "$DATABASE_URL" -f sql/init_postgresql.sql`

`psql "$DATABASE_URL" -f sql/init_postgresql_partitions_2025_07.sql`

2) 建库完成后，**把 Alembic 版本戳到基线**（避免后续 `upgrade` 重复建表）：

`flask db stamp 20251219161048`

### 方案 B：用 Alembic 直接建库（推荐用于“统一由迁移驱动”）

对空库执行：

`flask db upgrade`

## 3. 既有库（结构已存在）如何切换到新 Alembic 历史

当数据库结构已经是“生产库同构”，但你删除了历史迁移文件后，应该使用 **stamp** 而不是 **upgrade**：

`flask db stamp 20251219161048`

说明：
- `stamp` 只修改 `alembic_version`，不会执行 DDL。
- 如果库结构与基线不一致，建议先用 `pg_dump --schema-only` 对比差异后再决定补迁移还是回滚改动。

## 4. 一致性校验建议（可复制执行）

### 4.1 Schema diff（推荐）

1) 从目标数据库导出 schema：

`pg_dump --schema-only --no-owner --no-privileges "$DATABASE_URL" > /tmp/current_schema.sql`

2) 与基线对比（忽略注释/空白时可用更强的 diff 工具）：

`cat sql/init_postgresql.sql sql/init_postgresql_partitions_2025_07.sql > /tmp/init_schema.sql`

`diff -u /tmp/init_schema.sql /tmp/current_schema.sql | head -n 200`

### 4.2 关键对象自检（最低成本）

- 分区父表是否存在：`database_size_stats`、`instance_size_stats`、`database_size_aggregations`、`instance_size_aggregations`
- 触发器函数是否存在：`update_updated_at_column()`、`instance_size_stats_partition_trigger()`、`auto_create_database_size_partition()` 等
- 典型唯一约束是否存在：
  - `account_permission` 的 `UNIQUE(instance_id, db_type, username)`
  - `instance_databases` 的 `UNIQUE(instance_id, database_name)`
