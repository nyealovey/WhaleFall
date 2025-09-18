# SQL 脚本目录

本目录包含泰摸鱼吧项目相关的所有SQL脚本文件。

## 📁 文件说明

### 🗄️ 数据库初始化脚本

#### `init_postgresql.sql`
- **用途**: PostgreSQL数据库完整初始化脚本
- **功能**: 
  - 创建所有表结构（用户、实例、凭据、账户、分类、权限、任务等）
  - 插入初始数据和权限配置
  - 支持PostgreSQL优化特性（SERIAL、JSONB、索引等）
  - 确保幂等性（可重复运行）
- **使用**: 在PostgreSQL数据库中执行此脚本进行完整初始化


### 🔧 监控用户设置脚本

#### `setup_mysql_monitor_user.sql`
- **用途**: MySQL监控用户创建和权限设置
- **功能**: 
  - 创建`monitor_user`用户
  - 授予必要的监控权限
  - 配置MySQL数据库监控
- **使用**: `mysql -u root -p < sql/setup_mysql_monitor_user.sql`

#### `setup_postgresql_monitor_user.sql`
- **用途**: PostgreSQL监控用户创建和权限设置
- **功能**: 
  - 创建`monitor_user`用户
  - 授予数据库连接和查询权限
  - 配置PostgreSQL数据库监控
- **使用**: `psql -U postgres -d postgres -f sql/setup_postgresql_monitor_user.sql`

#### `setup_sqlserver_monitor_user.sql`
- **用途**: SQL Server监控用户创建和权限设置
- **功能**: 
  - 创建`monitor_user`登录和用户
  - 授予服务器和数据库权限
  - 配置SQL Server数据库监控
- **使用**: `sqlcmd -S server -U sa -P password -i sql/setup_sqlserver_monitor_user.sql`

#### `setup_sqlserver_monitor_user_advanced.sql`
- **用途**: SQL Server高级监控用户设置
- **功能**: 
  - 创建具有高级权限的监控用户
  - 支持跨数据库查询
  - 配置详细的监控权限
- **使用**: `sqlcmd -S server -U sa -P password -i sql/setup_sqlserver_monitor_user_advanced.sql`

#### `setup_sqlserver_monitor_user_cross_db.sql`
- **用途**: SQL Server跨数据库监控用户设置
- **功能**: 
  - 创建支持跨数据库查询的监控用户
  - 授予跨数据库权限
  - 配置多数据库监控
- **使用**: `sqlcmd -S server -U sa -P password -i sql/setup_sqlserver_monitor_user_cross_db.sql`

#### `setup_oracle_monitor_user.sql`
- **用途**: Oracle监控用户创建和权限设置
- **功能**: 
  - 创建`monitor_user`用户
  - 授予系统权限和对象权限
  - 配置Oracle数据库监控
- **使用**: `sqlplus sys/password@database as sysdba @sql/setup_oracle_monitor_user.sql`

## 🚀 使用指南

### 1. 数据库初始化

#### PostgreSQL完整初始化
```bash
# 连接到PostgreSQL数据库
psql -U postgres -d postgres

# 执行初始化脚本
\i sql/init_postgresql.sql
```


### 2. 监控用户设置

#### 设置所有数据库的监控用户
```bash
# MySQL
mysql -u root -p < sql/setup_mysql_monitor_user.sql

# PostgreSQL
psql -U postgres -d postgres -f sql/setup_postgresql_monitor_user.sql

# SQL Server (基础)
sqlcmd -S server -U sa -P password -i sql/setup_sqlserver_monitor_user.sql

# SQL Server (高级)
sqlcmd -S server -U sa -P password -i sql/setup_sqlserver_monitor_user_advanced.sql

# SQL Server (跨数据库)
sqlcmd -S server -U sa -P password -i sql/setup_sqlserver_monitor_user_cross_db.sql

# Oracle
sqlplus sys/password@database as sysdba @sql/setup_oracle_monitor_user.sql
```

### 3. 验证设置

执行相应的监控用户设置脚本后，可以通过以下方式验证：

```bash
# 测试MySQL连接
mysql -u monitor_user -p -e "SHOW DATABASES;"

# 测试PostgreSQL连接
psql -U monitor_user -d postgres -c "\l"

# 测试SQL Server连接
sqlcmd -S server -U monitor_user -P password -Q "SELECT name FROM sys.databases"

# 测试Oracle连接
sqlplus monitor_user/password@database
```

## ⚠️ 注意事项

1. **权限要求**: 执行监控用户设置脚本需要数据库管理员权限
2. **密码安全**: 请修改脚本中的默认密码
3. **网络访问**: 确保泰摸鱼吧服务器能够访问目标数据库
4. **防火墙**: 检查数据库端口是否开放
5. **SSL配置**: 生产环境建议启用SSL连接

## 📚 相关文档

- [数据库权限总览](../docs/database/DATABASE_PERMISSIONS_OVERVIEW.md)
- [MySQL权限管理](../docs/database/MYSQL_PERMISSIONS.md)
- [PostgreSQL权限管理](../docs/database/POSTGRESQL_PERMISSIONS.md)
- [SQL Server权限管理](../docs/database/SQL_SERVER_PERMISSIONS.md)
- [Oracle权限管理](../docs/database/ORACLE_PERMISSIONS.md)

---

**最后更新**: 2025年9月18日  
**维护者**: 泰摸鱼吧开发团队
