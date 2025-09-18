# MySQL 权限要求

## 概述

本文档详细说明了泰摸鱼吧系统在MySQL中读取账户信息、数据库信息和统计信息所需的最低权限要求。

## 功能模块权限要求

### 1. 连接测试功能

**所需权限：**
- `CONNECT` - 连接到MySQL服务器

**查询的系统表：**
- `SELECT @@VERSION` - 获取数据库版本信息

**最低权限：**
```sql
-- 授予连接权限
GRANT USAGE ON *.* TO 'monitor_user'@'%';
```

### 2. 账户同步功能

**所需权限：**
- `SELECT` on `mysql.user` - 查询用户表
- `SELECT` on `mysql.db` - 查询数据库权限表
- `SELECT` on `mysql.tables_priv` - 查询表权限表
- `SELECT` on `mysql.columns_priv` - 查询列权限表
- `SELECT` on `mysql.procs_priv` - 查询存储过程权限表

**查询的系统表：**
- `mysql.user` - 用户账户信息
- `mysql.db` - 数据库级权限
- `mysql.tables_priv` - 表级权限
- `mysql.columns_priv` - 列级权限
- `mysql.procs_priv` - 存储过程权限

**最低权限：**
```sql
-- 授予mysql系统数据库的查询权限
GRANT SELECT ON mysql.* TO 'monitor_user'@'%';
```

### 3. 权限查询功能

**所需权限：**
- `SELECT` on `mysql.user` - 查询用户表
- `SELECT` on `mysql.db` - 查询数据库权限表
- `SELECT` on `mysql.tables_priv` - 查询表权限表
- `SELECT` on `mysql.columns_priv` - 查询列权限表
- `SELECT` on `mysql.procs_priv` - 查询存储过程权限表
- `SELECT` on `INFORMATION_SCHEMA.*` - 查询信息模式

**查询的系统表：**
- `mysql.user` - 用户账户信息
- `mysql.db` - 数据库级权限
- `mysql.tables_priv` - 表级权限
- `mysql.columns_priv` - 列级权限
- `mysql.procs_priv` - 存储过程权限
- `INFORMATION_SCHEMA.USER_PRIVILEGES` - 用户权限信息
- `INFORMATION_SCHEMA.SCHEMA_PRIVILEGES` - 数据库权限信息
- `INFORMATION_SCHEMA.TABLE_PRIVILEGES` - 表权限信息
- `INFORMATION_SCHEMA.COLUMN_PRIVILEGES` - 列权限信息

**最低权限：**
```sql
-- 授予mysql系统数据库的查询权限
GRANT SELECT ON mysql.* TO 'monitor_user'@'%';

-- 授予INFORMATION_SCHEMA的查询权限
GRANT SELECT ON INFORMATION_SCHEMA.* TO 'monitor_user'@'%';
```

## 权限级别说明

### 最低权限级别

**仅连接测试：**
```sql
-- 只需要连接权限
GRANT USAGE ON *.* TO 'monitor_user'@'%';
```

**基本账户同步：**
```sql
-- 需要mysql系统数据库查询权限
GRANT SELECT ON mysql.* TO 'monitor_user'@'%';
```

**完整功能（推荐）：**
```sql
-- 完整权限，支持所有功能
GRANT USAGE ON *.* TO 'monitor_user'@'%';
GRANT SELECT ON mysql.* TO 'monitor_user'@'%';
GRANT SELECT ON INFORMATION_SCHEMA.* TO 'monitor_user'@'%';
```

### 权限说明

| 权限 | 用途 | 必需性 |
|------|------|--------|
| `USAGE` | 连接到MySQL服务器 | 必需 |
| `SELECT ON mysql.*` | 查询用户和权限信息 | 必需 |
| `SELECT ON INFORMATION_SCHEMA.*` | 查询权限详细信息 | 必需 |

## 创建专用监控用户

### 1. 创建用户账户

```sql
-- 创建MySQL用户账户
CREATE USER 'monitor_user'@'%' IDENTIFIED BY 'StrongPassword123!';

-- 或者限制特定IP访问
CREATE USER 'monitor_user'@'192.168.1.100' IDENTIFIED BY 'StrongPassword123!';
```

### 2. 授予最低权限

```sql
-- 授予连接权限
GRANT USAGE ON *.* TO 'monitor_user'@'%';

-- 授予mysql系统数据库查询权限
GRANT SELECT ON mysql.* TO 'monitor_user'@'%';

-- 授予INFORMATION_SCHEMA查询权限
GRANT SELECT ON INFORMATION_SCHEMA.* TO 'monitor_user'@'%';
```

### 3. 刷新权限

```sql
-- 刷新权限表
FLUSH PRIVILEGES;
```

## 安全考虑

### 1. 最小权限原则

- 只授予系统运行所需的最小权限
- 定期审查和更新权限
- 使用专用监控账户，避免使用root账户

### 2. 密码安全

- 使用强密码策略
- 定期更换密码
- 启用密码过期策略

### 3. 网络安全

- 限制监控账户的登录来源IP
- 使用SSL/TLS加密连接
- 启用MySQL审计

## 故障排除

### 常见权限错误

**错误：`Access denied for user 'monitor_user'@'%' to database 'mysql'`**

**解决方案：**
```sql
-- 授予mysql数据库访问权限
GRANT SELECT ON mysql.* TO 'monitor_user'@'%';
FLUSH PRIVILEGES;
```

**错误：`Access denied for user 'monitor_user'@'%' to database 'information_schema'`**

**解决方案：**
```sql
-- 授予INFORMATION_SCHEMA访问权限
GRANT SELECT ON INFORMATION_SCHEMA.* TO 'monitor_user'@'%';
FLUSH PRIVILEGES;
```

**错误：`Table 'mysql.user' doesn't exist`**

**解决方案：**
- 检查MySQL版本是否支持该表
- 确保用户有访问mysql数据库的权限

## 测试权限

### 权限测试脚本

```sql
-- 测试连接
SELECT @@VERSION;

-- 测试mysql.user表访问
SELECT COUNT(*) FROM mysql.user;

-- 测试mysql.db表访问
SELECT COUNT(*) FROM mysql.db;

-- 测试INFORMATION_SCHEMA访问
SELECT COUNT(*) FROM INFORMATION_SCHEMA.USER_PRIVILEGES;

-- 测试权限查询
SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMA_PRIVILEGES;
```

## 不同MySQL版本的注意事项

### MySQL 5.7+

- 支持 `mysql.user` 表的所有字段
- 支持 `account_locked` 字段
- 支持 `password_expired` 字段

### MySQL 8.0+

- 默认使用 `caching_sha2_password` 认证插件
- 支持角色管理
- 支持动态权限

### MariaDB

- 与MySQL 5.7类似
- 支持 `mysql.user` 表的所有字段
- 兼容MySQL权限系统

## 总结

**最低权限要求：**
1. `USAGE` - 连接权限
2. `SELECT ON mysql.*` - 查询用户和权限信息
3. `SELECT ON INFORMATION_SCHEMA.*` - 查询权限详细信息

**推荐权限：**
- 在上述基础上添加SSL连接要求

**安全建议：**
- 使用专用监控账户
- 遵循最小权限原则
- 定期审查权限设置
- 启用审计和监控
