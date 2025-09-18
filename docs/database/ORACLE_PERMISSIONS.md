# Oracle 权限要求

## 概述

本文档详细说明了鲸落系统在Oracle中读取账户信息、数据库信息和统计信息所需的最低权限要求。

## 功能模块权限要求

### 1. 连接测试功能

**所需权限：**
- `CREATE SESSION` - 连接到Oracle数据库

**查询的系统表：**
- `SELECT * FROM v$version` - 获取数据库版本信息

**最低权限：**
```sql
-- 授予连接权限
GRANT CREATE SESSION TO monitor_user;
```

### 2. 账户同步功能

**所需权限：**
- `SELECT` on `DBA_USERS` - 查询用户信息
- `SELECT` on `DBA_ROLES` - 查询角色信息
- `SELECT` on `DBA_ROLE_PRIVS` - 查询角色权限
- `SELECT` on `DBA_SYS_PRIVS` - 查询系统权限
- `SELECT` on `DBA_TAB_PRIVS` - 查询表权限

**查询的系统表：**
- `DBA_USERS` - 用户账户信息
- `DBA_ROLES` - 角色信息
- `DBA_ROLE_PRIVS` - 角色权限信息
- `DBA_SYS_PRIVS` - 系统权限信息
- `DBA_TAB_PRIVS` - 表权限信息

**最低权限：**
```sql
-- 授予DBA视图查询权限
GRANT SELECT ON DBA_USERS TO monitor_user;
GRANT SELECT ON DBA_ROLES TO monitor_user;
GRANT SELECT ON DBA_ROLE_PRIVS TO monitor_user;
GRANT SELECT ON DBA_SYS_PRIVS TO monitor_user;
GRANT SELECT ON DBA_TAB_PRIVS TO monitor_user;
```

### 3. 权限查询功能

**所需权限：**
- `SELECT` on `DBA_USERS` - 查询用户信息
- `SELECT` on `DBA_ROLES` - 查询角色信息
- `SELECT` on `DBA_ROLE_PRIVS` - 查询角色权限
- `SELECT` on `DBA_SYS_PRIVS` - 查询系统权限
- `SELECT` on `DBA_TAB_PRIVS` - 查询表权限
- `SELECT` on `DBA_COL_PRIVS` - 查询列权限
- `SELECT` on `DBA_PROXY_USERS` - 查询代理用户
- `SELECT` on `V$SESSION` - 查询会话信息（可选）

**查询的系统表：**
- `DBA_USERS` - 用户账户信息
- `DBA_ROLES` - 角色信息
- `DBA_ROLE_PRIVS` - 角色权限信息
- `DBA_SYS_PRIVS` - 系统权限信息
- `DBA_TAB_PRIVS` - 表权限信息
- `DBA_COL_PRIVS` - 列权限信息
- `DBA_PROXY_USERS` - 代理用户信息
- `V$SESSION` - 会话信息（可选）

**最低权限：**
```sql
-- 授予DBA视图查询权限
GRANT SELECT ON DBA_USERS TO monitor_user;
GRANT SELECT ON DBA_ROLES TO monitor_user;
GRANT SELECT ON DBA_ROLE_PRIVS TO monitor_user;
GRANT SELECT ON DBA_SYS_PRIVS TO monitor_user;
GRANT SELECT ON DBA_TAB_PRIVS TO monitor_user;
GRANT SELECT ON DBA_COL_PRIVS TO monitor_user;
GRANT SELECT ON DBA_PROXY_USERS TO monitor_user;

-- 可选：授予V$视图查询权限
GRANT SELECT ON V$SESSION TO monitor_user;
```

## 权限级别说明

### 最低权限级别

**仅连接测试：**
```sql
-- 只需要连接权限
GRANT CREATE SESSION TO monitor_user;
```

**基本账户同步：**
```sql
-- 需要DBA视图查询权限
GRANT CREATE SESSION TO monitor_user;
GRANT SELECT ON DBA_USERS TO monitor_user;
GRANT SELECT ON DBA_ROLES TO monitor_user;
```

**完整功能（推荐）：**
```sql
-- 完整权限，支持所有功能
GRANT CREATE SESSION TO monitor_user;
GRANT SELECT ON DBA_USERS TO monitor_user;
GRANT SELECT ON DBA_ROLES TO monitor_user;
GRANT SELECT ON DBA_ROLE_PRIVS TO monitor_user;
GRANT SELECT ON DBA_SYS_PRIVS TO monitor_user;
GRANT SELECT ON DBA_TAB_PRIVS TO monitor_user;
GRANT SELECT ON DBA_COL_PRIVS TO monitor_user;
GRANT SELECT ON DBA_PROXY_USERS TO monitor_user;
```

### 权限说明

| 权限 | 用途 | 必需性 |
|------|------|--------|
| `CREATE SESSION` | 连接到Oracle数据库 | 必需 |
| `SELECT ON DBA_USERS` | 查询用户信息 | 必需 |
| `SELECT ON DBA_ROLES` | 查询角色信息 | 必需 |
| `SELECT ON DBA_ROLE_PRIVS` | 查询角色权限 | 必需 |
| `SELECT ON DBA_SYS_PRIVS` | 查询系统权限 | 必需 |
| `SELECT ON DBA_TAB_PRIVS` | 查询表权限 | 必需 |
| `SELECT ON DBA_COL_PRIVS` | 查询列权限 | 必需 |
| `SELECT ON DBA_PROXY_USERS` | 查询代理用户 | 必需 |

## 创建专用监控用户

### 1. 创建用户账户

```sql
-- 创建Oracle用户账户
CREATE USER monitor_user IDENTIFIED BY "StrongPassword123!";

-- 设置默认表空间
ALTER USER monitor_user DEFAULT TABLESPACE USERS;

-- 设置临时表空间
ALTER USER monitor_user TEMPORARY TABLESPACE TEMP;

-- 设置配额
ALTER USER monitor_user QUOTA UNLIMITED ON USERS;
```

### 2. 授予最低权限

```sql
-- 授予连接权限
GRANT CREATE SESSION TO monitor_user;

-- 授予DBA视图查询权限
GRANT SELECT ON DBA_USERS TO monitor_user;
GRANT SELECT ON DBA_ROLES TO monitor_user;
GRANT SELECT ON DBA_ROLE_PRIVS TO monitor_user;
GRANT SELECT ON DBA_SYS_PRIVS TO monitor_user;
GRANT SELECT ON DBA_TAB_PRIVS TO monitor_user;
GRANT SELECT ON DBA_COL_PRIVS TO monitor_user;
GRANT SELECT ON DBA_PROXY_USERS TO monitor_user;

-- 可选：授予V$视图查询权限
GRANT SELECT ON V$SESSION TO monitor_user;
GRANT SELECT ON V$INSTANCE TO monitor_user;
```

### 3. 创建同义词（可选）

```sql
-- 为DBA视图创建同义词
CREATE SYNONYM monitor_user.dba_users FOR SYS.DBA_USERS;
CREATE SYNONYM monitor_user.dba_roles FOR SYS.DBA_ROLES;
CREATE SYNONYM monitor_user.dba_role_privs FOR SYS.DBA_ROLE_PRIVS;
CREATE SYNONYM monitor_user.dba_sys_privs FOR SYS.DBA_SYS_PRIVS;
CREATE SYNONYM monitor_user.dba_tab_privs FOR SYS.DBA_TAB_PRIVS;
CREATE SYNONYM monitor_user.dba_col_privs FOR SYS.DBA_COL_PRIVS;
CREATE SYNONYM monitor_user.dba_proxy_users FOR SYS.DBA_PROXY_USERS;
```

## 安全考虑

### 1. 最小权限原则

- 只授予系统运行所需的最小权限
- 定期审查和更新权限
- 使用专用监控账户，避免使用SYS或SYSTEM账户

### 2. 密码安全

- 使用强密码策略
- 定期更换密码
- 启用密码过期策略
- 使用密码复杂度验证

### 3. 网络安全

- 限制监控账户的登录来源IP
- 使用SSL/TLS加密连接
- 启用Oracle审计

### 4. 行级安全

- 考虑启用虚拟专用数据库(VPD)
- 限制敏感数据的访问

## 故障排除

### 常见权限错误

**错误：`ORA-00942: table or view does not exist`**

**解决方案：**
```sql
-- 授予DBA视图查询权限
GRANT SELECT ON DBA_USERS TO monitor_user;
```

**错误：`ORA-00942: table or view does not exist` (DBA视图)**

**解决方案：**
- 确保用户有访问DBA视图的权限
- 检查Oracle版本是否支持该视图

**错误：`ORA-01031: insufficient privileges`**

**解决方案：**
```sql
-- 授予必要的系统权限
GRANT CREATE SESSION TO monitor_user;
GRANT SELECT ON DBA_USERS TO monitor_user;
```

**错误：`ORA-00942: table or view does not exist` (V$视图)**

**解决方案：**
```sql
-- 授予V$视图查询权限
GRANT SELECT ON V$SESSION TO monitor_user;
```

## 测试权限

### 权限测试脚本

```sql
-- 测试连接
SELECT * FROM v$version;

-- 测试DBA_USERS表访问
SELECT COUNT(*) FROM dba_users;

-- 测试DBA_ROLES表访问
SELECT COUNT(*) FROM dba_roles;

-- 测试DBA_ROLE_PRIVS表访问
SELECT COUNT(*) FROM dba_role_privs;

-- 测试DBA_SYS_PRIVS表访问
SELECT COUNT(*) FROM dba_sys_privs;

-- 测试DBA_TAB_PRIVS表访问
SELECT COUNT(*) FROM dba_tab_privs;

-- 测试DBA_COL_PRIVS表访问
SELECT COUNT(*) FROM dba_col_privs;

-- 测试DBA_PROXY_USERS表访问
SELECT COUNT(*) FROM dba_proxy_users;
```

## 不同Oracle版本的注意事项

### Oracle 11g+

- 支持所有基本功能
- 支持角色管理
- 支持虚拟专用数据库(VPD)

### Oracle 12c+

- 支持多租户架构
- 支持可插拔数据库(PDB)
- 支持统一审计

### Oracle 18c+

- 支持自动索引
- 支持机器学习
- 改进的统计信息

### Oracle 19c+

- 支持自动调优
- 支持JSON支持
- 改进的云集成

## 高级配置

### 1. 创建监控专用表空间

```sql
-- 创建监控表空间
CREATE TABLESPACE monitoring
DATAFILE '/u01/oracle/oradata/monitoring01.dbf'
SIZE 100M
AUTOEXTEND ON
NEXT 10M
MAXSIZE 1G;

-- 授予监控用户访问权限
ALTER USER monitor_user DEFAULT TABLESPACE monitoring;
ALTER USER monitor_user QUOTA UNLIMITED ON monitoring;
```

### 2. 配置连接限制

```sql
-- 限制连接数
ALTER USER monitor_user CONNECT 5;

-- 设置会话超时
ALTER USER monitor_user IDLE_TIME 30;

-- 设置密码过期
ALTER USER monitor_user PASSWORD EXPIRE;
```

### 3. 启用审计

```sql
-- 启用标准审计
AUDIT SELECT ON DBA_USERS BY monitor_user;
AUDIT SELECT ON DBA_ROLES BY monitor_user;
AUDIT SELECT ON DBA_ROLE_PRIVS BY monitor_user;

-- 启用统一审计（Oracle 12c+）
AUDIT POLICY audit_policy BY monitor_user;
```

## 多租户环境配置

### 1. 可插拔数据库(PDB)配置

```sql
-- 连接到PDB
ALTER SESSION SET CONTAINER = pdb_name;

-- 创建监控用户
CREATE USER monitor_user IDENTIFIED BY "StrongPassword123!";

-- 授予权限
GRANT CREATE SESSION TO monitor_user;
GRANT SELECT ON DBA_USERS TO monitor_user;
-- ... 其他权限
```

### 2. 根容器(CDB)配置

```sql
-- 连接到CDB
ALTER SESSION SET CONTAINER = CDB$ROOT;

-- 创建通用用户
CREATE USER C##monitor_user IDENTIFIED BY "StrongPassword123!";

-- 授予权限
GRANT CREATE SESSION TO C##monitor_user;
GRANT SELECT ON DBA_USERS TO C##monitor_user;
-- ... 其他权限
```

## 总结

**最低权限要求：**
1. `CREATE SESSION` - 连接权限
2. `SELECT ON DBA_USERS` - 查询用户信息
3. `SELECT ON DBA_ROLES` - 查询角色信息
4. `SELECT ON DBA_ROLE_PRIVS` - 查询角色权限
5. `SELECT ON DBA_SYS_PRIVS` - 查询系统权限
6. `SELECT ON DBA_TAB_PRIVS` - 查询表权限
7. `SELECT ON DBA_COL_PRIVS` - 查询列权限
8. `SELECT ON DBA_PROXY_USERS` - 查询代理用户

**推荐权限：**
- 在上述基础上添加V$视图查询权限用于性能监控

**安全建议：**
- 使用专用监控账户
- 遵循最小权限原则
- 定期审查权限设置
- 启用审计和监控
