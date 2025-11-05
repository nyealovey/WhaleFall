# Oracle 系统视图兼容性说明（11g+）

## 概述

本文档说明系统中使用的 Oracle 系统视图，确保与 Oracle 11g 及以上版本兼容。

## 使用的系统视图清单

### 1. 账户同步相关视图

| 视图名称 | 用途 | Oracle 11g 支持 | 所需权限 |
|---------|------|----------------|---------|
| `dba_users` | 查询所有数据库用户 | ✅ 是 | `SELECT ANY DICTIONARY` 或 DBA 角色 |
| `dba_role_privs` | 查询用户的角色权限 | ✅ 是 | `SELECT ANY DICTIONARY` 或 DBA 角色 |
| `dba_sys_privs` | 查询用户的系统权限 | ✅ 是 | `SELECT ANY DICTIONARY` 或 DBA 角色 |
| `dba_ts_quotas` | 查询用户的表空间配额 | ✅ 是 | `SELECT ANY DICTIONARY` 或 DBA 角色 |

### 2. 容量同步相关视图

| 视图名称 | 用途 | Oracle 11g 支持 | 所需权限 |
|---------|------|----------------|---------|
| `dba_data_files` | 查询数据文件信息 | ✅ 是 | `SELECT ANY DICTIONARY` 或 DBA 角色 |
| `dba_tablespaces` | 查询表空间信息 | ✅ 是 | `SELECT ANY DICTIONARY` 或 DBA 角色 |

### 3. 已修复的错误视图

| 错误视图名称 | 问题 | 正确视图 | 修复状态 |
|------------|------|---------|---------|
| ~~`dba_ts_privs`~~ | **不存在** | `dba_ts_quotas` | ✅ 已修复 |

## 详细说明

### dba_users
**用途**：查询所有数据库用户及其状态

**查询示例**：
```sql
SELECT username, account_status, default_tablespace 
FROM dba_users 
WHERE username NOT IN ('SYS', 'SYSTEM');
```

**字段说明**：
- `username`: 用户名（大写）
- `account_status`: 账户状态（OPEN, LOCKED, EXPIRED 等）
- `default_tablespace`: 默认表空间
- `created`: 创建时间
- `profile`: 使用的配置文件

**Oracle 版本支持**：
- ✅ Oracle 11g (11.1+)
- ✅ Oracle 12c
- ✅ Oracle 18c
- ✅ Oracle 19c
- ✅ Oracle 21c

---

### dba_role_privs
**用途**：查询授予用户或角色的角色

**查询示例**：
```sql
SELECT granted_role 
FROM dba_role_privs 
WHERE grantee = 'MYUSER';
```

**字段说明**：
- `grantee`: 被授予者（用户或角色）
- `granted_role`: 授予的角色
- `admin_option`: 是否有管理权限（YES/NO）
- `default_role`: 是否为默认角色（YES/NO）

**Oracle 版本支持**：
- ✅ Oracle 11g (11.1+)
- ✅ Oracle 12c+

---

### dba_sys_privs
**用途**：查询授予用户或角色的系统权限

**查询示例**：
```sql
SELECT privilege 
FROM dba_sys_privs 
WHERE grantee = 'MYUSER';
```

**字段说明**：
- `grantee`: 被授予者（用户或角色）
- `privilege`: 系统权限名称
- `admin_option`: 是否有管理权限（YES/NO）

**常见系统权限**：
- `CREATE SESSION`: 连接数据库
- `CREATE TABLE`: 创建表
- `CREATE VIEW`: 创建视图
- `SELECT ANY DICTIONARY`: 查询数据字典
- `SELECT ANY TABLE`: 查询任意表

**Oracle 版本支持**：
- ✅ Oracle 11g (11.1+)
- ✅ Oracle 12c+

---

### dba_ts_quotas
**用途**：查询用户在表空间上的配额

**查询示例**：
```sql
SELECT 
    tablespace_name, 
    CASE 
        WHEN max_bytes = -1 THEN 'UNLIMITED'
        ELSE TO_CHAR(max_bytes / 1024 / 1024) || ' MB'
    END AS quota,
    bytes / 1024 / 1024 AS used_mb
FROM dba_ts_quotas 
WHERE username = 'MYUSER';
```

**字段说明**：
- `username`: 用户名
- `tablespace_name`: 表空间名称
- `bytes`: 已使用字节数
- `max_bytes`: 最大配额字节数（-1 表示无限制）
- `blocks`: 已使用块数
- `max_blocks`: 最大配额块数

**Oracle 版本支持**：
- ✅ Oracle 11g (11.1+)
- ✅ Oracle 12c+

**注意事项**：
- ⚠️ **不要使用 `dba_ts_privs`**（此视图不存在）
- 配额为 -1 表示 UNLIMITED
- 配额为 0 表示无配额（无法在该表空间创建对象）

---

### dba_data_files
**用途**：查询数据文件信息，用于计算表空间大小

**查询示例**：
```sql
SELECT 
    tablespace_name,
    SUM(bytes) / 1024 / 1024 AS size_mb
FROM dba_data_files
GROUP BY tablespace_name;
```

**字段说明**：
- `file_name`: 数据文件路径
- `file_id`: 文件ID
- `tablespace_name`: 所属表空间
- `bytes`: 文件大小（字节）
- `blocks`: 文件块数
- `status`: 状态（AVAILABLE, INVALID）
- `autoextensible`: 是否自动扩展（YES/NO）

**Oracle 版本支持**：
- ✅ Oracle 11g (11.1+)
- ✅ Oracle 12c+

---

### dba_tablespaces
**用途**：查询表空间信息

**查询示例**：
```sql
SELECT 
    tablespace_name,
    status,
    contents,
    extent_management
FROM dba_tablespaces;
```

**字段说明**：
- `tablespace_name`: 表空间名称
- `block_size`: 块大小
- `status`: 状态（ONLINE, OFFLINE, READ ONLY）
- `contents`: 内容类型（PERMANENT, TEMPORARY, UNDO）
- `extent_management`: 区管理方式（LOCAL, DICTIONARY）

**Oracle 版本支持**：
- ✅ Oracle 11g (11.1+)
- ✅ Oracle 12c+

## 权限要求

### 最小权限（推荐）

```sql
-- 基础连接权限
GRANT CREATE SESSION TO myuser;

-- 查询数据字典权限（推荐方式）
GRANT SELECT ANY DICTIONARY TO myuser;
```

### 或者授予特定视图权限

```sql
-- 基础连接权限
GRANT CREATE SESSION TO myuser;

-- 账户同步所需权限
GRANT SELECT ON dba_users TO myuser;
GRANT SELECT ON dba_role_privs TO myuser;
GRANT SELECT ON dba_sys_privs TO myuser;
GRANT SELECT ON dba_ts_quotas TO myuser;

-- 容量同步所需权限
GRANT SELECT ON dba_data_files TO myuser;
GRANT SELECT ON dba_tablespaces TO myuser;
```

### 或者授予 DBA 角色（不推荐生产环境）

```sql
GRANT DBA TO myuser;
```

## 降级查询方案

如果无法获得 DBA 权限，可以使用以下降级视图：

| DBA 视图 | 降级视图 | 说明 |
|---------|---------|------|
| `dba_users` | `all_users` | 只能查询可访问的用户，无账户状态信息 |
| `dba_role_privs` | `user_role_privs` | 只能查询当前用户的角色 |
| `dba_sys_privs` | `user_sys_privs` | 只能查询当前用户的系统权限 |
| `dba_ts_quotas` | `user_ts_quotas` | 只能查询当前用户的表空间配额 |
| `dba_data_files` | `dba_segments` | 使用段信息估算大小（需要 SELECT_CATALOG_ROLE） |
| `dba_tablespaces` | `all_tablespaces` | 可查询可访问的表空间 |

### 降级查询示例

```sql
-- 降级查询用户列表
SELECT username 
FROM all_users 
WHERE username NOT IN ('SYS', 'SYSTEM');

-- 降级查询当前用户角色
SELECT granted_role 
FROM user_role_privs;

-- 降级查询当前用户系统权限
SELECT privilege 
FROM user_sys_privs;

-- 降级查询当前用户表空间配额
SELECT tablespace_name, max_bytes 
FROM user_ts_quotas;

-- 降级查询表空间大小（使用段信息）
SELECT 
    tablespace_name,
    SUM(bytes) / 1024 / 1024 AS size_mb
FROM dba_segments
GROUP BY tablespace_name;
```

## 常见错误及解决方案

### 错误 1: ORA-00942: table or view does not exist

**原因**：
- 连接用户没有查询该视图的权限
- 视图名称拼写错误
- 使用了不存在的视图（如 `dba_ts_privs`）

**解决方案**：
```sql
-- 检查用户权限
SELECT * FROM user_sys_privs;
SELECT * FROM user_role_privs;

-- 授予权限
GRANT SELECT ANY DICTIONARY TO myuser;
```

### 错误 2: ORA-01017: invalid username/password

**原因**：
- 用户名大小写问题
- 密码错误
- 账户被锁定

**解决方案**：
```sql
-- 检查用户状态
SELECT username, account_status 
FROM dba_users 
WHERE username = 'MYUSER';

-- 解锁用户
ALTER USER myuser ACCOUNT UNLOCK;

-- 重置密码
ALTER USER myuser IDENTIFIED BY newpassword;
```

### 错误 3: ORA-01031: insufficient privileges

**原因**：
- 用户有连接权限但没有查询权限

**解决方案**：
```sql
-- 授予必要权限
GRANT SELECT ANY DICTIONARY TO myuser;
```

## 测试脚本

### 测试所有视图访问权限

```sql
-- 以应用用户登录
sqlplus myuser/password@ORCL

-- 测试账户同步视图
SELECT COUNT(*) FROM dba_users;
SELECT COUNT(*) FROM dba_role_privs;
SELECT COUNT(*) FROM dba_sys_privs;
SELECT COUNT(*) FROM dba_ts_quotas;

-- 测试容量同步视图
SELECT COUNT(*) FROM dba_data_files;
SELECT COUNT(*) FROM dba_tablespaces;

-- 如果以上查询都成功，说明权限配置正确
```

### 测试降级查询

```sql
-- 测试降级视图
SELECT COUNT(*) FROM all_users;
SELECT COUNT(*) FROM user_role_privs;
SELECT COUNT(*) FROM user_sys_privs;
SELECT COUNT(*) FROM user_ts_quotas;
SELECT COUNT(*) FROM all_tablespaces;
```

## 版本兼容性矩阵

| 功能 | Oracle 11g | Oracle 12c | Oracle 18c | Oracle 19c | Oracle 21c |
|-----|-----------|-----------|-----------|-----------|-----------|
| 账户同步 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 容量同步 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 表空间配额 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 降级查询 | ✅ | ✅ | ✅ | ✅ | ✅ |

## 相关文档

- [Oracle 用户名大小写问题](./oracle_lowercase_username_fix.md)
- [Oracle 表视图不存在问题分析](./oracle_table_not_found_analysis.md)
- [Oracle 官方文档 - Database Reference](https://docs.oracle.com/cd/E11882_01/server.112/e40402/toc.htm)

## 修改记录

| 日期 | 修改内容 | 修改人 |
|-----|---------|-------|
| 2025-11-05 | 修复 `dba_ts_privs` 错误，改用 `dba_ts_quotas` | Kiro |
| 2025-11-05 | 添加 Oracle 11g+ 兼容性说明 | Kiro |
| 2025-11-05 | 添加降级查询方案 | Kiro |
