# 数据库权限配置指南

## 概述

鲸落系统支持MySQL、PostgreSQL、SQL Server和Oracle四种数据库，本文档提供统一的权限配置指南。

## 权限要求对比

| 数据库 | 最低权限 | 连接权限 | 系统表权限 | 信息模式权限 |
|--------|----------|----------|------------|--------------|
| **MySQL** | `USAGE` | `CONNECT` | `SELECT ON mysql.*` | `SELECT ON INFORMATION_SCHEMA.*` |
| **PostgreSQL** | `CONNECT` | `CONNECT` | `SELECT ON pg_*` | `SELECT ON information_schema.*` |
| **SQL Server** | `CONNECT SQL` | `CONNECT SQL` | `VIEW ANY DEFINITION` | `VIEW DEFINITION` |
| **Oracle** | `CREATE SESSION` | `CREATE SESSION` | `SELECT ON DBA_*` | - |

## 快速配置

### MySQL
```sql
GRANT USAGE ON *.* TO 'monitor_user'@'%';
GRANT SELECT ON mysql.* TO 'monitor_user'@'%';
GRANT SELECT ON INFORMATION_SCHEMA.* TO 'monitor_user'@'%';
```

### PostgreSQL
```sql
GRANT CONNECT ON DATABASE postgres TO monitor_user;
GRANT SELECT ON pg_roles TO monitor_user;
GRANT SELECT ON pg_database TO monitor_user;
GRANT SELECT ON ALL TABLES IN SCHEMA information_schema TO monitor_user;
```

### SQL Server
```sql
GRANT CONNECT SQL TO monitor_user;
GRANT VIEW ANY DEFINITION TO monitor_user;
GRANT VIEW DEFINITION TO monitor_user;
```

### Oracle
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

## 安全建议

- **最小权限原则**: 只授予系统运行所需的最小权限
- **专用监控账户**: 使用专用监控账户，避免使用高权限账户
- **定期审查**: 定期审查和更新权限设置
- **密码安全**: 使用强密码并定期更换
- **IP限制**: 限制监控账户的登录来源IP
- **加密连接**: 使用SSL/TLS加密连接

## 快速设置

### 1. 创建监控用户
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

### 2. 配置鲸落
在鲸落系统中添加数据库实例：
- 用户名: `monitor_user`
- 密码: `YourStrongPassword123!`（请修改为强密码）
- 主机: 数据库服务器IP
- 端口: 数据库默认端口

## 故障排除

### 常见问题
1. **权限不足** - 检查用户是否具有所需的权限
2. **连接失败** - 检查网络连接和认证信息
3. **表不存在** - 检查数据库版本和权限设置

### 解决方案
1. 运行测试脚本诊断问题
2. 查看数据库和应用程序日志
3. 检查SQL语法和权限设置
