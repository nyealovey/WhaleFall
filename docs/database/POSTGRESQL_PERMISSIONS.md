# PostgreSQL 权限要求

## 概述

本文档详细说明了鲸落系统在PostgreSQL中读取账户信息、数据库信息和统计信息所需的最低权限要求。

## 功能模块权限要求

### 1. 连接测试功能

**所需权限：**
- `CONNECT` - 连接到PostgreSQL服务器

**查询的系统表：**
- `SELECT version()` - 获取数据库版本信息

**最低权限：**
```sql
-- 授予连接权限
GRANT CONNECT ON DATABASE postgres TO monitor_user;
```

### 2. 账户同步功能

**所需权限：**
- `SELECT` on `pg_roles` - 查询角色信息
- `SELECT` on `pg_database` - 查询数据库信息
- `SELECT` on `pg_authid` - 查询认证信息（需要超级用户权限）

**查询的系统表：**
- `pg_roles` - 角色和用户信息
- `pg_database` - 数据库列表
- `pg_authid` - 认证信息（可选）

**最低权限：**
```sql
-- 授予系统表查询权限
GRANT SELECT ON pg_roles TO monitor_user;
GRANT SELECT ON pg_database TO monitor_user;
```

### 3. 权限查询功能

**所需权限：**
- `SELECT` on `pg_roles` - 查询角色信息
- `SELECT` on `pg_database` - 查询数据库信息
- `SELECT` on `pg_namespace` - 查询模式信息
- `SELECT` on `pg_class` - 查询表信息
- `SELECT` on `pg_proc` - 查询函数信息
- `SELECT` on `information_schema.*` - 查询信息模式

**查询的系统表：**
- `pg_roles` - 角色和用户信息
- `pg_database` - 数据库列表
- `pg_namespace` - 模式信息
- `pg_class` - 表信息
- `pg_proc` - 函数信息
- `information_schema.role_table_grants` - 表权限信息
- `information_schema.role_usage_grants` - 使用权限信息
- `information_schema.role_routine_grants` - 例程权限信息

**最低权限：**
```sql
-- 授予系统表查询权限
GRANT SELECT ON pg_roles TO monitor_user;
GRANT SELECT ON pg_database TO monitor_user;
GRANT SELECT ON pg_namespace TO monitor_user;
GRANT SELECT ON pg_class TO monitor_user;
GRANT SELECT ON pg_proc TO monitor_user;

-- 授予information_schema查询权限
GRANT SELECT ON ALL TABLES IN SCHEMA information_schema TO monitor_user;
```

## 权限级别说明

### 最低权限级别

**仅连接测试：**
```sql
-- 只需要连接权限
GRANT CONNECT ON DATABASE postgres TO monitor_user;
```

**基本账户同步：**
```sql
-- 需要系统表查询权限
GRANT SELECT ON pg_roles TO monitor_user;
GRANT SELECT ON pg_database TO monitor_user;
```

**完整功能（推荐）：**
```sql
-- 完整权限，支持所有功能
GRANT CONNECT ON DATABASE postgres TO monitor_user;
GRANT SELECT ON pg_roles TO monitor_user;
GRANT SELECT ON pg_database TO monitor_user;
GRANT SELECT ON pg_namespace TO monitor_user;
GRANT SELECT ON pg_class TO monitor_user;
GRANT SELECT ON pg_proc TO monitor_user;
GRANT SELECT ON ALL TABLES IN SCHEMA information_schema TO monitor_user;
```

### 权限说明

| 权限 | 用途 | 必需性 |
|------|------|--------|
| `CONNECT` | 连接到PostgreSQL服务器 | 必需 |
| `SELECT ON pg_roles` | 查询角色和用户信息 | 必需 |
| `SELECT ON pg_database` | 查询数据库信息 | 必需 |
| `SELECT ON pg_namespace` | 查询模式信息 | 必需 |
| `SELECT ON pg_class` | 查询表信息 | 必需 |
| `SELECT ON pg_proc` | 查询函数信息 | 必需 |
| `SELECT ON information_schema.*` | 查询权限详细信息 | 必需 |

## 创建专用监控用户

### 1. 创建用户账户

```sql
-- 创建PostgreSQL用户账户
CREATE USER monitor_user WITH PASSWORD 'StrongPassword123!';

-- 或者创建角色（推荐）
CREATE ROLE monitor_user WITH LOGIN PASSWORD 'StrongPassword123!';
```

### 2. 授予最低权限

```sql
-- 授予连接权限
GRANT CONNECT ON DATABASE postgres TO monitor_user;

-- 授予系统表查询权限
GRANT SELECT ON pg_roles TO monitor_user;
GRANT SELECT ON pg_database TO monitor_user;
GRANT SELECT ON pg_namespace TO monitor_user;
GRANT SELECT ON pg_class TO monitor_user;
GRANT SELECT ON pg_proc TO monitor_user;

-- 授予information_schema查询权限
GRANT SELECT ON ALL TABLES IN SCHEMA information_schema TO monitor_user;
```

### 3. 为所有数据库授予权限

```sql
-- 为所有现有数据库授予连接权限
DO $$
DECLARE
    db_name TEXT;
BEGIN
    FOR db_name IN SELECT datname FROM pg_database WHERE datistemplate = false
    LOOP
        EXECUTE 'GRANT CONNECT ON DATABASE ' || quote_ident(db_name) || ' TO monitor_user';
    END LOOP;
END $$;
```

## 安全考虑

### 1. 最小权限原则

- 只授予系统运行所需的最小权限
- 定期审查和更新权限
- 使用专用监控账户，避免使用postgres超级用户

### 2. 密码安全

- 使用强密码策略
- 定期更换密码
- 启用密码过期策略

### 3. 网络安全

- 限制监控账户的登录来源IP
- 使用SSL/TLS加密连接
- 启用PostgreSQL审计

### 4. 行级安全

- 考虑启用行级安全策略
- 限制敏感数据的访问

## 故障排除

### 常见权限错误

**错误：`permission denied for table pg_roles`**

**解决方案：**
```sql
-- 授予pg_roles表查询权限
GRANT SELECT ON pg_roles TO monitor_user;
```

**错误：`permission denied for table pg_database`**

**解决方案：**
```sql
-- 授予pg_database表查询权限
GRANT SELECT ON pg_database TO monitor_user;
```

**错误：`permission denied for schema information_schema`**

**解决方案：**
```sql
-- 授予information_schema查询权限
GRANT SELECT ON ALL TABLES IN SCHEMA information_schema TO monitor_user;
```

**错误：`permission denied for database`**

**解决方案：**
```sql
-- 授予数据库连接权限
GRANT CONNECT ON DATABASE database_name TO monitor_user;
```

## 测试权限

### 权限测试脚本

```sql
-- 测试连接
SELECT version();

-- 测试pg_roles表访问
SELECT COUNT(*) FROM pg_roles;

-- 测试pg_database表访问
SELECT COUNT(*) FROM pg_database;

-- 测试pg_namespace表访问
SELECT COUNT(*) FROM pg_namespace;

-- 测试pg_class表访问
SELECT COUNT(*) FROM pg_class;

-- 测试pg_proc表访问
SELECT COUNT(*) FROM pg_proc;

-- 测试information_schema访问
SELECT COUNT(*) FROM information_schema.role_table_grants;
```

## 不同PostgreSQL版本的注意事项

### PostgreSQL 9.6+

- 支持所有基本功能
- 支持角色管理
- 支持行级安全

### PostgreSQL 10+

- 支持声明式分区
- 支持逻辑复制
- 改进的并行查询

### PostgreSQL 11+

- 支持存储过程
- 支持事务中的DDL
- 改进的并行查询

### PostgreSQL 12+

- 支持SQL/JSON路径
- 改进的索引和统计信息
- 支持生成列

## 高级配置

### 1. 创建监控专用数据库

```sql
-- 创建监控数据库
CREATE DATABASE monitoring;

-- 授予监控用户访问权限
GRANT CONNECT ON DATABASE monitoring TO monitor_user;
GRANT USAGE ON SCHEMA public TO monitor_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monitor_user;
```

### 2. 配置连接限制

```sql
-- 限制连接数
ALTER USER monitor_user CONNECTION LIMIT 5;

-- 设置会话超时
ALTER USER monitor_user VALID UNTIL '2024-12-31';
```

### 3. 启用审计

```sql
-- 安装pg_audit扩展（需要超级用户权限）
CREATE EXTENSION IF NOT EXISTS pgaudit;

-- 配置审计策略
ALTER SYSTEM SET pgaudit.log = 'read,write';
ALTER SYSTEM SET pgaudit.log_relation = on;
SELECT pg_reload_conf();
```

## 总结

**最低权限要求：**
1. `CONNECT` - 连接权限
2. `SELECT ON pg_roles` - 查询角色信息
3. `SELECT ON pg_database` - 查询数据库信息
4. `SELECT ON information_schema.*` - 查询权限详细信息

**推荐权限：**
- 在上述基础上添加所有系统表的查询权限

**安全建议：**
- 使用专用监控账户
- 遵循最小权限原则
- 定期审查权限设置
- 启用审计和监控
