# SQL 脚本说明

## 文件结构

### 主要初始化脚本
- `init_postgresql.sql` - PostgreSQL数据库主初始化脚本
- `permission_configs.sql` - 权限配置数据脚本（从现有数据库导出）
- `init_scheduler_tasks.sql` - 定时任务配置说明脚本

### 数据库迁移脚本
- `migrate_add_missing_fields.sql` - 添加缺失字段的迁移脚本（修复 current_account_sync_data 表）

### 数据库类型特定脚本
- `setup_mysql_monitor_user.sql` - MySQL监控用户设置
- `setup_postgresql_monitor_user.sql` - PostgreSQL监控用户设置
- `setup_sqlserver_monitor_user.sql` - SQL Server监控用户设置
- `setup_oracle_monitor_user.sql` - Oracle监控用户设置

## 使用说明

### 1. 初始化数据库
```bash
# 执行主初始化脚本
psql -h localhost -U postgres -d taifish -f init_postgresql.sql

# 执行权限配置数据
psql -h localhost -U postgres -d taifish -f permission_configs.sql

# 查看定时任务配置说明（可选）
psql -h localhost -U postgres -d taifish -f init_scheduler_tasks.sql
```

### 2. 数据库迁移（如果使用旧版本）
如果您使用的是旧版本的数据库，需要执行迁移脚本来添加缺失的字段：

```bash
# 执行字段修复迁移脚本
psql -h localhost -U postgres -d taifish -f migrate_add_missing_fields.sql
```

**注意**：迁移脚本是幂等的，可以安全地多次执行，不会重复添加字段。

### 3. 设置监控用户
根据您的数据库类型，执行相应的监控用户设置脚本：

```bash
# MySQL
mysql -h localhost -u root -p < setup_mysql_monitor_user.sql

# PostgreSQL
psql -h localhost -U postgres -d taifish -f setup_postgresql_monitor_user.sql

# SQL Server
sqlcmd -S localhost -U sa -P <password> -i setup_sqlserver_monitor_user.sql

# Oracle
sqlplus sys/<password>@localhost:1521/orcl @setup_oracle_monitor_user.sql
```

## 权限配置数据

`permission_configs.sql` 文件包含了从现有数据库导出的完整权限配置数据，包括：

- **MySQL权限**: 全局权限和数据库权限
- **PostgreSQL权限**: 角色属性、预定义角色、数据库权限、表空间权限
- **SQL Server权限**: 服务器角色、服务器权限、数据库角色、数据库权限
- **Oracle权限**: 系统权限、角色、表空间权限、表空间配额

这些权限配置数据支持鲸落系统的智能账户分类功能。

## 定时任务管理

### APScheduler任务表
- `apscheduler_jobs` - 定时任务存储表
- 任务配置从 `config/scheduler_tasks.yaml` 加载
- 支持通过Web界面管理任务

### 默认任务
1. **账户同步任务** (`sync_accounts`)
   - 执行频率：每30分钟
   - 功能：同步所有数据库实例的账户信息

2. **清理旧日志任务** (`cleanup_logs`)
   - 执行频率：每天凌晨2点
   - 功能：清理30天前的日志和临时文件

### 任务管理命令
```sql
-- 查看当前任务
SELECT id, next_run_time FROM apscheduler_jobs;

-- 查看任务详情（需要解码job_state字段）
SELECT id, next_run_time, 
       pg_size_pretty(pg_column_size(job_state)) as job_size
FROM apscheduler_jobs;
```

## 注意事项

1. 执行脚本前请确保数据库用户有足够的权限
2. 权限配置数据使用 `ON CONFLICT DO NOTHING` 确保幂等性
3. 所有脚本都支持重复执行而不会产生错误
4. 建议在生产环境执行前先在测试环境验证
5. 定时任务会在应用启动时自动加载，无需手动插入