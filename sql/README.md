# SQL 脚本目录说明

本目录用于存放**初始化/运维/一次性修复**相关的 SQL 脚本，避免把“手工 SQL”散落在文档或聊天记录里。

> 约定：涉及生产 Schema 演进的变更，优先走 `migrations/**`（Alembic/Flask-Migrate）。

## 目录结构（单一真源）

```
sql/
  init/                       # 空库初始化（DDL）
    postgresql/
      init_postgresql.sql
      partitions/             # 按月份拆分的分区子表脚本（只增不改）
        init_postgresql_partitions_YYYY_MM.sql

  seed/                       # 初始化数据/基线数据（DML）
    postgresql/
      permission_configs.sql

  ops/                        # 运维脚本（外部数据库账号等）
    monitor-user/
      setup_mysql_monitor_user.sql
      setup_postgresql_monitor_user.sql
      setup_sqlserver_monitor_user.sql
      setup_oracle_monitor_user.sql

  patches/                    # 一次性修复脚本（建议按年份归档）
    YYYY/
      YYYYMMDD_description.sql
```

## 使用建议

### 1) PostgreSQL：空库初始化（SQL 初始化路径）

```bash
psql "$DATABASE_URL" -f sql/init/postgresql/init_postgresql.sql
psql "$DATABASE_URL" -f sql/init/postgresql/partitions/init_postgresql_partitions_2025_07.sql
psql "$DATABASE_URL" -f sql/init/postgresql/partitions/init_postgresql_partitions_2025_08.sql

# 建库完成后把版本戳到基线，避免后续 upgrade 重复建表
flask db stamp 20251219161048
```

### 2) PostgreSQL：导入权限配置（种子数据）

> 注意：`permission_configs.sql` 是“真实配置导出”，通常假设目标表为空；重复执行可能因主键/唯一约束而失败。

```bash
psql "$DATABASE_URL" -f sql/seed/postgresql/permission_configs.sql
```

### 3) 外部数据库：创建监控账号（只读/最小权限）

> 注意：脚本内口令为占位符，必须替换为强密码；并建议把 MySQL 的 `%` 收敛为可信网段/来源。

```bash
# MySQL
mysql -u root -p < sql/ops/monitor-user/setup_mysql_monitor_user.sql

# PostgreSQL
psql -U postgres -d postgres -f sql/ops/monitor-user/setup_postgresql_monitor_user.sql

# SQL Server（示例：sqlcmd）
sqlcmd -S server -U sa -P password -i sql/ops/monitor-user/setup_sqlserver_monitor_user.sql

# Oracle（示例：sqlplus/sysdba）
sqlplus sys/password@database as sysdba @sql/ops/monitor-user/setup_oracle_monitor_user.sql
```

## 维护规则（简版）

- `init/**`：仅用于**空库初始化**；不用于“对已有库打补丁”。分区脚本按月份**只增不改**（历史脚本不回写）。
- `seed/**`：用于导入基础数据/枚举配置；尽量做成可重复执行（幂等/可回滚），避免多次导入造成脏数据。
- `ops/**`：用于运维/外部依赖账号授权；脚本应清晰标注**最小权限**与可选项。
- `patches/**`：用于紧急/一次性修复；执行后应尽快补齐迁移或代码侧对齐，并在 PR/Runbook 记录“是否已执行/执行环境/执行时间”。
