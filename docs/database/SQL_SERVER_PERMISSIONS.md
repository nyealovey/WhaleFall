# SQL Server 权限要求

## 概述

本文档详细说明了鲸落系统在SQL Server中读取账户信息、数据库信息和统计信息所需的最低权限要求。

## 功能模块权限要求

### 1. 连接测试功能

**所需权限：**
- `CONNECT SQL` - 连接到SQL Server实例

**查询的系统视图：**
- `SELECT @@VERSION` - 获取数据库版本信息

**最低权限：**
```sql
-- 授予连接权限
GRANT CONNECT SQL TO [username];
```

### 2. 账户同步功能

**所需权限：**
- `VIEW ANY DEFINITION` - 查看服务器级安全对象定义
- `VIEW DEFINITION` - 查看数据库级对象定义

**查询的系统视图：**
- `sys.server_principals` - 服务器级主体信息
- `sys.server_permissions` - 服务器级权限信息
- `sys.databases` - 数据库列表
- `sys.database_permissions` - 数据库级权限信息
- `sys.database_principals` - 数据库级主体信息

**最低权限：**
```sql
-- 授予查看服务器级定义权限
GRANT VIEW ANY DEFINITION TO [username];

-- 授予查看数据库定义权限
GRANT VIEW DEFINITION TO [username];
```

### 3. 权限查询功能

**所需权限：**
- `VIEW ANY DEFINITION` - 查看服务器级安全对象定义
- `VIEW DEFINITION` - 查看数据库级对象定义
- `VIEW SERVER STATE` - 查看服务器状态信息（可选，用于性能统计）

**查询的系统视图：**
- `sys.server_permissions` - 服务器级权限
- `sys.database_permissions` - 数据库级权限
- `sys.databases` - 数据库信息
- `sys.database_principals` - 数据库主体

**最低权限：**
```sql
-- 授予查看服务器级定义权限
GRANT VIEW ANY DEFINITION TO [username];

-- 授予查看数据库定义权限
GRANT VIEW DEFINITION TO [username];

-- 可选：授予查看服务器状态权限（用于性能统计）
GRANT VIEW SERVER STATE TO [username];
```

## 权限级别说明

### 最低权限级别

**仅连接测试：**
```sql
-- 只需要连接权限
GRANT CONNECT SQL TO [username];
```

**基本账户同步：**
```sql
-- 需要查看定义权限
GRANT VIEW ANY DEFINITION TO [username];
GRANT VIEW DEFINITION TO [username];
```

**完整功能（推荐）：**
```sql
-- 完整权限，支持所有功能
GRANT CONNECT SQL TO [username];
GRANT VIEW ANY DEFINITION TO [username];
GRANT VIEW DEFINITION TO [username];
GRANT VIEW SERVER STATE TO [username];
```

### 权限说明

| 权限 | 用途 | 必需性 |
|------|------|--------|
| `CONNECT SQL` | 连接到SQL Server | 必需 |
| `VIEW ANY DEFINITION` | 查看服务器级安全对象 | 必需 |
| `VIEW DEFINITION` | 查看数据库级对象 | 必需 |
| `VIEW SERVER STATE` | 查看服务器状态和性能信息 | 可选 |

## 创建专用监控用户

### 1. 创建登录账户

```sql
-- 创建SQL Server登录账户
CREATE LOGIN [monitor_user] WITH PASSWORD = 'StrongPassword123!';
```

### 2. 授予最低权限

```sql
-- 授予连接权限
GRANT CONNECT SQL TO [monitor_user];

-- 授予查看定义权限
GRANT VIEW ANY DEFINITION TO [monitor_user];
GRANT VIEW DEFINITION TO [monitor_user];

-- 可选：授予查看服务器状态权限
GRANT VIEW SERVER STATE TO [monitor_user];
```

### 3. 数据库级权限（如果需要）

```sql
-- 为特定数据库授予权限
USE [YourDatabase];
CREATE USER [monitor_user] FOR LOGIN [monitor_user];
GRANT VIEW DEFINITION TO [monitor_user];
```

## 安全考虑

### 1. 最小权限原则

- 只授予系统运行所需的最小权限
- 定期审查和更新权限
- 使用专用监控账户，避免使用高权限账户

### 2. 密码安全

- 使用强密码策略
- 定期更换密码
- 启用密码过期策略

### 3. 网络安全

- 限制监控账户的登录来源IP
- 使用加密连接
- 启用SQL Server审计

## 故障排除

### 常见权限错误

**错误：`The server principal "monitor_user" is not able to access the database "master" under the current security context.`**

**解决方案：**
```sql
-- 为master数据库创建用户
USE master;
CREATE USER [monitor_user] FOR LOGIN [monitor_user];
GRANT VIEW DEFINITION TO [monitor_user];
```

**错误：`The SELECT permission was denied on the object 'sys.server_principals'`**

**解决方案：**
```sql
-- 授予查看服务器定义权限
GRANT VIEW ANY DEFINITION TO [monitor_user];
```

**错误：`The SELECT permission was denied on the object 'sys.databases'`**

**解决方案：**
```sql
-- 授予查看数据库定义权限
GRANT VIEW DEFINITION TO [monitor_user];
```

## 测试权限

### 权限测试脚本

```sql
-- 测试连接
SELECT @@VERSION;

-- 测试服务器级权限
SELECT COUNT(*) FROM sys.server_principals;

-- 测试数据库级权限
SELECT COUNT(*) FROM sys.databases;

-- 测试权限查询
SELECT COUNT(*) FROM sys.server_permissions;

-- 测试数据库权限查询
SELECT COUNT(*) FROM sys.database_permissions;
```

## 总结

**最低权限要求：**
1. `CONNECT SQL` - 连接权限
2. `VIEW ANY DEFINITION` - 查看服务器级定义
3. `VIEW DEFINITION` - 查看数据库级定义

**推荐权限：**
- 在上述基础上添加 `VIEW SERVER STATE` 用于性能监控

**安全建议：**
- 使用专用监控账户
- 遵循最小权限原则
- 定期审查权限设置
- 启用审计和监控
