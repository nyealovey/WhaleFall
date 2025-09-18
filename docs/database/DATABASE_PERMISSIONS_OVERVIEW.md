# 数据库权限要求总览

## 概述

本文档提供了鲸落系统支持的所有数据库类型的权限要求总览，包括MySQL、PostgreSQL、SQL Server和Oracle。

## 权限要求对比

| 数据库 | 最低权限 | 连接权限 | 系统表权限 | 信息模式权限 | 特殊权限 |
|--------|----------|----------|------------|--------------|----------|
| **MySQL** | `USAGE` | `CONNECT` | `SELECT ON mysql.*` | `SELECT ON INFORMATION_SCHEMA.*` | - |
| **PostgreSQL** | `CONNECT` | `CONNECT` | `SELECT ON pg_*` | `SELECT ON information_schema.*` | - |
| **SQL Server** | `CONNECT SQL` | `CONNECT SQL` | `VIEW ANY DEFINITION` | `VIEW DEFINITION` | `VIEW SERVER STATE` |
| **Oracle** | `CREATE SESSION` | `CREATE SESSION` | `SELECT ON DBA_*` | - | `SELECT ON V$*` |

## 详细文档

### 1. MySQL 权限要求
- **文档**: [MYSQL_PERMISSIONS.md](MYSQL_PERMISSIONS.md)
- **设置脚本**: [setup_mysql_monitor_user.sql](../sql/setup_mysql_monitor_user.sql)
- **测试脚本**: [test_mysql_permissions.sql](../scripts/test_mysql_permissions.sql)

**最低权限：**
```sql
GRANT USAGE ON *.* TO 'monitor_user'@'%';
GRANT SELECT ON mysql.* TO 'monitor_user'@'%';
GRANT SELECT ON INFORMATION_SCHEMA.* TO 'monitor_user'@'%';
```

### 2. PostgreSQL 权限要求
- **文档**: [POSTGRESQL_PERMISSIONS.md](POSTGRESQL_PERMISSIONS.md)
- **设置脚本**: [setup_postgresql_monitor_user.sql](../sql/setup_postgresql_monitor_user.sql)
- **测试脚本**: [test_postgresql_permissions.sql](../scripts/test_postgresql_permissions.sql)

**最低权限：**
```sql
GRANT CONNECT ON DATABASE postgres TO monitor_user;
GRANT SELECT ON pg_roles TO monitor_user;
GRANT SELECT ON pg_database TO monitor_user;
GRANT SELECT ON ALL TABLES IN SCHEMA information_schema TO monitor_user;
```

### 3. SQL Server 权限要求
- **文档**: [SQL_SERVER_PERMISSIONS.md](SQL_SERVER_PERMISSIONS.md)
- **设置脚本**: [setup_sqlserver_monitor_user.sql](../sql/setup_sqlserver_monitor_user.sql)
- **测试脚本**: [test_sqlserver_permissions.sql](../scripts/test_sqlserver_permissions.sql)

**最低权限：**
```sql
GRANT CONNECT SQL TO monitor_user;
GRANT VIEW ANY DEFINITION TO monitor_user;
GRANT VIEW DEFINITION TO monitor_user;
```

### 4. Oracle 权限要求
- **文档**: [ORACLE_PERMISSIONS.md](ORACLE_PERMISSIONS.md)
- **设置脚本**: [setup_oracle_monitor_user.sql](../sql/setup_oracle_monitor_user.sql)
- **测试脚本**: [test_oracle_permissions.sql](../scripts/test_oracle_permissions.sql)

**最低权限：**
```sql
GRANT CREATE SESSION TO monitor_user;
GRANT SELECT ON DBA_USERS TO monitor_user;
GRANT SELECT ON DBA_ROLES TO monitor_user;
GRANT SELECT ON DBA_ROLE_PRIVS TO monitor_user;
GRANT SELECT ON DBA_SYS_PRIVS TO monitor_user;
GRANT SELECT ON DBA_TAB_PRIVS TO monitor_user;
GRANT SELECT ON DBA_COL_PRIVS TO monitor_user;
GRANT SELECT ON DBA_PROXY_USERS TO monitor_user;
```

## 功能模块权限需求

### 1. 连接测试功能

| 数据库 | 权限 | 查询 |
|--------|------|------|
| MySQL | `USAGE` | `SELECT @@VERSION` |
| PostgreSQL | `CONNECT` | `SELECT version()` |
| SQL Server | `CONNECT SQL` | `SELECT @@VERSION` |
| Oracle | `CREATE SESSION` | `SELECT * FROM v$version` |

### 2. 账户同步功能

| 数据库 | 权限 | 查询的表/视图 |
|--------|------|---------------|
| MySQL | `SELECT ON mysql.*` | `mysql.user` |
| PostgreSQL | `SELECT ON pg_roles` | `pg_roles` |
| SQL Server | `VIEW ANY DEFINITION` | `sys.server_principals` |
| Oracle | `SELECT ON DBA_USERS` | `dba_users` |

### 3. 权限查询功能

| 数据库 | 权限 | 查询的表/视图 |
|--------|------|---------------|
| MySQL | `SELECT ON INFORMATION_SCHEMA.*` | `INFORMATION_SCHEMA.*` |
| PostgreSQL | `SELECT ON information_schema.*` | `information_schema.*` |
| SQL Server | `VIEW DEFINITION` | `sys.*` |
| Oracle | `SELECT ON DBA_*` | `dba_*` |

## 安全建议

### 1. 通用安全原则

- **最小权限原则**: 只授予系统运行所需的最小权限
- **专用监控账户**: 使用专用监控账户，避免使用高权限账户
- **定期审查**: 定期审查和更新权限设置
- **密码安全**: 使用强密码并定期更换

### 2. 网络安全

- **IP限制**: 限制监控账户的登录来源IP
- **加密连接**: 使用SSL/TLS加密连接
- **审计日志**: 启用数据库审计日志

### 3. 权限管理

- **角色分离**: 使用角色分离权限管理
- **定期检查**: 定期检查权限设置
- **最小化权限**: 避免授予不必要的权限

## 快速设置指南

### 1. 选择数据库类型

根据您的数据库类型，选择相应的文档和脚本。

### 2. 运行权限测试

首先运行测试脚本，检查当前用户权限：
```bash
# MySQL
mysql -u current_user -p < scripts/test_mysql_permissions.sql

# PostgreSQL
psql -U current_user -d database_name -f scripts/test_postgresql_permissions.sql

# SQL Server
sqlcmd -S server -U current_user -P password -i scripts/test_sqlserver_permissions.sql

# Oracle
sqlplus current_user/password@database @scripts/test_oracle_permissions.sql
```

### 3. 创建监控用户

运行相应的设置脚本：
```bash
# MySQL
mysql -u root -p < sql/setup_mysql_monitor_user.sql

# PostgreSQL
psql -U postgres -d postgres -f sql/setup_postgresql_monitor_user.sql

# SQL Server
sqlcmd -S server -U sa -P password -i sql/setup_sqlserver_monitor_user.sql

# Oracle
sqlplus sys/password@database as sysdba @sql/setup_oracle_monitor_user.sql
```

### 4. 配置鲸落

在鲸落系统中添加数据库实例：
- 用户名: `monitor_user`
- 密码: `YourStrongPassword123!`（请修改为强密码）
- 主机: 数据库服务器IP
- 端口: 数据库默认端口

## 故障排除

### 常见问题

1. **权限不足**: 检查用户是否具有所需的权限
2. **连接失败**: 检查网络连接和认证信息
3. **表不存在**: 检查数据库版本和权限设置
4. **查询失败**: 检查SQL语法和权限设置

### 解决方案

1. **查看详细文档**: 参考各数据库的详细权限文档
2. **运行测试脚本**: 使用测试脚本诊断问题
3. **检查日志**: 查看数据库和应用程序日志
4. **联系支持**: 如问题持续存在，请联系技术支持

## 总结

鲸落系统支持四种主流数据库，每种数据库都有其特定的权限要求。通过遵循最小权限原则和使用专用监控账户，可以确保系统的安全性和稳定性。

**推荐做法：**
1. 使用专用监控账户
2. 遵循最小权限原则
3. 定期审查权限设置
4. 启用审计和监控
5. 使用强密码和加密连接
