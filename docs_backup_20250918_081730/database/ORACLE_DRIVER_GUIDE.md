# Oracle数据库驱动指南

## 概述

泰摸鱼吧已从 `cx_Oracle` 升级到 `python-oracledb`，提供更好的性能和兼容性，特别是对Apple Silicon Mac的支持。

## 驱动信息

| 项目 | 信息 |
|------|------|
| **当前驱动** | python-oracledb |
| **版本** | 2.0.0+ |
| **Python版本** | 3.8+ |
| **Oracle版本** | 11.2+ |
| **架构支持** | x86_64, ARM64 (Apple Silicon) |

## 安装说明

### 1. 基本安装

```bash
# 安装python-oracledb
pip install python-oracledb

# 或从requirements.txt安装
pip install -r requirements.txt
```

### 2. Oracle客户端安装

#### macOS (Apple Silicon)

```bash
# 使用Homebrew安装Oracle Instant Client
brew install instantclient-basic
brew install instantclient-sdk

# 设置环境变量
export ORACLE_HOME=/opt/homebrew/lib/instantclient_21_8
export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
export PATH=$ORACLE_HOME:$PATH
```

#### macOS (Intel)

```bash
# 使用Homebrew安装Oracle Instant Client
brew install instantclient-basic
brew install instantclient-sdk

# 设置环境变量
export ORACLE_HOME=/usr/local/lib/instantclient_21_8
export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
export PATH=$ORACLE_HOME:$PATH
```

#### Linux (Ubuntu/Debian)

```bash
# 下载Oracle Instant Client
wget https://download.oracle.com/otn_software/linux/instantclient/2118000/instantclient-basic-linux.x64-21.18.0.0.0dbru.zip
wget https://download.oracle.com/otn_software/linux/instantclient/2118000/instantclient-sdk-linux.x64-21.18.0.0.0dbru.zip

# 解压到/opt/oracle
sudo mkdir -p /opt/oracle
sudo unzip instantclient-basic-linux.x64-21.18.0.0.0dbru.zip -d /opt/oracle
sudo unzip instantclient-sdk-linux.x64-21.18.0.0.0dbru.zip -d /opt/oracle

# 设置环境变量
export ORACLE_HOME=/opt/oracle/instantclient_21_8
export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
export PATH=$ORACLE_HOME:$PATH
```

#### Windows

1. 下载Oracle Instant Client Basic和SDK
2. 解压到 `C:\oracle\instantclient_21_8`
3. 将 `C:\oracle\instantclient_21_8` 添加到系统PATH
4. 设置环境变量 `ORACLE_HOME=C:\oracle\instantclient_21_8`

## 连接配置

### 1. 基本连接

```python
import oracledb

# 基本连接
conn = oracledb.connect(
    user="username",
    password="password",
    host="localhost",
    port=1521,
    service_name="ORCL"
)

# 使用SID连接
conn = oracledb.connect(
    user="username",
    password="password",
    host="localhost",
    port=1521,
    sid="ORCL"
)
```

### 2. 连接池

```python
# 创建连接池
pool = oracledb.create_pool(
    user="username",
    password="password",
    host="localhost",
    port=1521,
    service_name="ORCL",
    min=1,
    max=10,
    increment=1
)

# 从连接池获取连接
conn = pool.acquire()
```

### 3. 环境变量配置

```bash
# .env文件
ORACLE_USER=username
ORACLE_PASSWORD=password
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=ORCL
ORACLE_SID=ORCL
```

## 权限查询

### 1. 系统权限查询

```sql
-- 查询用户系统权限
SELECT privilege, admin_option
FROM dba_sys_privs
WHERE grantee = 'USERNAME'
ORDER BY privilege;
```

### 2. 角色权限查询

```sql
-- 查询用户角色
SELECT granted_role, admin_option
FROM dba_role_privs
WHERE grantee = 'USERNAME'
ORDER BY granted_role;
```

### 3. 表空间权限查询

```sql
-- 查询表空间权限
SELECT privilege
FROM dba_tab_privs
WHERE grantee = 'USERNAME'
AND table_name IN (SELECT tablespace_name FROM dba_tablespaces)
ORDER BY privilege;
```

### 4. 表空间配额查询

```sql
-- 查询表空间配额
SELECT 
    tablespace_name,
    CASE 
        WHEN max_bytes = -1 THEN 'UNLIMITED'
        WHEN max_bytes = 0 THEN 'NO QUOTA'
        ELSE 'QUOTA'
    END as quota_type
FROM dba_ts_quotas
WHERE username = 'USERNAME'
ORDER BY tablespace_name;
```

## 常见问题

### 1. ORA-00942: 表或视图不存在

**原因**: 当前用户没有访问DBA视图的权限

**解决方案**:
- 确保使用具有DBA权限的用户连接
- 或者使用用户级别的视图（如user_sys_privs）

### 2. 连接超时

**原因**: 网络问题或Oracle服务未启动

**解决方案**:
- 检查Oracle服务状态
- 检查网络连接
- 调整连接超时参数

### 3. 字符编码问题

**原因**: 字符集不匹配

**解决方案**:
```python
# 设置字符集
conn = oracledb.connect(
    user="username",
    password="password",
    host="localhost",
    port=1521,
    service_name="ORCL",
    encoding="UTF-8"
)
```

### 4. ARM64 Mac支持

**原因**: Oracle Instant Client版本问题

**解决方案**:
- 使用最新版本的Oracle Instant Client
- 确保下载ARM64版本
- 使用Homebrew安装（推荐）

## 性能优化

### 1. 连接池配置

```python
# 优化连接池参数
pool = oracledb.create_pool(
    user="username",
    password="password",
    host="localhost",
    port=1521,
    service_name="ORCL",
    min=2,          # 最小连接数
    max=20,         # 最大连接数
    increment=2,    # 连接增量
    timeout=60,     # 连接超时
    wait_timeout=60 # 等待超时
)
```

### 2. 查询优化

```python
# 使用预编译语句
cursor = conn.cursor()
cursor.prepare("SELECT * FROM users WHERE id = :id")
cursor.execute(None, id=user_id)
```

### 3. 批量操作

```python
# 批量插入
data = [(1, 'user1'), (2, 'user2'), (3, 'user3')]
cursor.executemany("INSERT INTO users (id, name) VALUES (:1, :2)", data)
conn.commit()
```

## 安全注意事项

### 1. 密码安全

- 不要在代码中硬编码密码
- 使用环境变量或配置文件
- 定期更换密码

### 2. 连接安全

- 使用SSL/TLS加密连接
- 限制数据库访问IP
- 使用最小权限原则

### 3. 权限管理

- 定期审查用户权限
- 及时撤销不必要的权限
- 监控异常访问

## 监控和日志

### 1. 连接监控

```python
# 监控连接状态
def check_connection(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM dual")
        return True
    except Exception as e:
        print(f"连接检查失败: {e}")
        return False
```

### 2. 性能监控

```python
# 监控查询性能
import time

start_time = time.time()
cursor.execute("SELECT * FROM large_table")
end_time = time.time()
print(f"查询耗时: {end_time - start_time:.2f}秒")
```

## 版本兼容性

| Oracle版本 | python-oracledb版本 | 支持状态 |
|------------|-------------------|----------|
| 11.2 | 1.0.0+ | ✅ 完全支持 |
| 12.1 | 1.0.0+ | ✅ 完全支持 |
| 12.2 | 1.0.0+ | ✅ 完全支持 |
| 18c | 1.0.0+ | ✅ 完全支持 |
| 19c | 1.0.0+ | ✅ 完全支持 |
| 21c | 1.0.0+ | ✅ 完全支持 |
| 23c | 2.0.0+ | ✅ 完全支持 |

## 参考资料

- [python-oracledb官方文档](https://python-oracledb.readthedocs.io/)
- [Oracle Instant Client下载](https://www.oracle.com/database/technologies/instant-client.html)
- [Oracle数据库文档](https://docs.oracle.com/en/database/)

---

**最后更新**: 2025-09-10  
**维护状态**: 活跃维护中
