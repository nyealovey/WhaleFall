# Oracle 数据库小写用户名连接问题解决方案

## 问题描述

在测试 Oracle 数据库连接时，提示"口令错误"（ORA-01017: invalid username/password）。经分析，数据库中保存的用户名是小写格式，但 Oracle 数据库默认会将用户名转换为大写，导致认证失败。

## 问题原因

### Oracle 用户名大小写规则

Oracle 数据库对用户名的处理有以下规则：

1. **不带引号的用户名**：自动转换为大写
   ```sql
   CREATE USER myuser IDENTIFIED BY password;
   -- 实际创建的用户名是：MYUSER
   ```

2. **带引号的用户名**：保持原样（大小写敏感）
   ```sql
   CREATE USER "myuser" IDENTIFIED BY password;
   -- 创建的用户名是：myuser（小写）
   ```

3. **连接时的规则**：
   - 如果用户名不带引号，Oracle 会转换为大写后查找
   - 如果用户名带引号，Oracle 会保持原样查找

### 当前代码问题

在 `app/services/connection_adapters/connection_factory.py` 的 `OracleConnection.connect()` 方法中：

```python
self.connection = oracledb.connect(
    user=(self.instance.credential.username if self.instance.credential else ""),
    password=password,
    dsn=dsn,
)
```

如果数据库中保存的用户名是 `myuser`（小写），但 Oracle 数据库中实际的用户名是 `MYUSER`（大写），连接时会因为用户名不匹配而失败。

## 解决方案

### 方案 1：自动转换为大写（推荐）⭐⭐⭐⭐⭐

这是最简单且最常用的方案，因为大多数 Oracle 用户名都是大写的。

#### 修改代码

修改 `app/services/connection_adapters/connection_factory.py` 中的 `OracleConnection.connect()` 方法：

```python
def connect(self) -> bool:
    """建立Oracle连接"""
    try:
        import oracledb

        # 获取连接信息
        password = self.instance.credential.get_plain_password() if self.instance.credential else ""
        username = self.instance.credential.username if self.instance.credential else ""
        
        # Oracle 用户名处理：默认转换为大写
        # 如果用户名包含引号，则保持原样（大小写敏感）
        if username and not username.startswith('"'):
            username_for_connection = username.upper()
            self.db_logger.debug(
                "Oracle用户名转换为大写",
                module="connection",
                instance_id=self.instance.id,
                original_username=username,
                converted_username=username_for_connection,
            )
        else:
            username_for_connection = username

        # 构建连接字符串
        database_name = self.instance.database_name or _get_default_schema("oracle") or "ORCL"

        # 使用 makedsn 构建 DSN（更可靠）
        try:
            # 优先尝试服务名格式
            dsn = oracledb.makedsn(
                host=self.instance.host,
                port=self.instance.port,
                service_name=database_name
            )
        except Exception:
            # 如果失败，尝试 SID 格式
            dsn = oracledb.makedsn(
                host=self.instance.host,
                port=self.instance.port,
                sid=database_name
            )

        self.db_logger.info(
            "尝试连接Oracle数据库",
            module="connection",
            instance_id=self.instance.id,
            host=self.instance.host,
            port=self.instance.port,
            username=username_for_connection,
            database_name=database_name,
        )

        # 初始化 Oracle 客户端
        try:
            import os

            candidate_paths: list[str] = []

            env_lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
            if env_lib_dir:
                candidate_paths.append(env_lib_dir)

            oracle_home = os.getenv("ORACLE_HOME")
            if oracle_home:
                candidate_paths.append(os.path.join(oracle_home, "lib"))

            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            candidate_paths.append(os.path.join(current_dir, "oracle_client", "lib"))

            lib_dir = next((path for path in candidate_paths if path and os.path.isdir(path)), None)

            if lib_dir:
                oracledb.init_oracle_client(lib_dir=lib_dir)
            else:
                oracledb.init_oracle_client()
                
        except Exception as init_error:
            # 如果已经初始化过，忽略错误
            if "already been initialized" not in str(init_error).lower():
                self.db_logger.warning(
                    "Oracle客户端初始化警告",
                    module="connection",
                    instance_id=self.instance.id,
                    error=str(init_error),
                )

        # 建立连接
        self.connection = oracledb.connect(
            user=username_for_connection,  # 使用转换后的用户名
            password=password,
            dsn=dsn,
        )
        
        self.is_connected = True
        
        self.db_logger.info(
            "Oracle连接成功",
            module="connection",
            instance_id=self.instance.id,
            username=username_for_connection,
        )
        
        return True

    except Exception as e:
        error_message = str(e)
        self.db_logger.error(
            "Oracle连接失败",
            module="connection",
            instance_id=self.instance.id,
            db_type="Oracle",
            host=self.instance.host,
            port=self.instance.port,
            username=username if 'username' in locals() else "unknown",
            error=error_message,
            error_type=type(e).__name__,
        )
        return False
```

### 方案 2：智能检测（备选）⭐⭐⭐

如果你的环境中既有大写用户名，也有小写用户名（带引号创建的），可以使用智能检测方案。

```python
def connect(self) -> bool:
    """建立Oracle连接 - 智能检测用户名大小写"""
    try:
        import oracledb

        password = self.instance.credential.get_plain_password() if self.instance.credential else ""
        username = self.instance.credential.username if self.instance.credential else ""
        database_name = self.instance.database_name or _get_default_schema("oracle") or "ORCL"

        # 构建 DSN
        try:
            dsn = oracledb.makedsn(
                host=self.instance.host,
                port=self.instance.port,
                service_name=database_name
            )
        except Exception:
            dsn = oracledb.makedsn(
                host=self.instance.host,
                port=self.instance.port,
                sid=database_name
            )

        # 初始化客户端（省略代码，同方案1）
        # ...

        # 尝试连接策略
        connection_attempts = []
        
        # 1. 如果用户名带引号，保持原样
        if username.startswith('"') and username.endswith('"'):
            connection_attempts.append(username)
        else:
            # 2. 先尝试大写（最常见）
            connection_attempts.append(username.upper())
            # 3. 再尝试原样（可能是小写敏感用户）
            if username != username.upper():
                connection_attempts.append(username)

        last_error = None
        for attempt_username in connection_attempts:
            try:
                self.db_logger.debug(
                    "尝试Oracle连接",
                    module="connection",
                    instance_id=self.instance.id,
                    username=attempt_username,
                )
                
                self.connection = oracledb.connect(
                    user=attempt_username,
                    password=password,
                    dsn=dsn,
                )
                
                self.is_connected = True
                
                self.db_logger.info(
                    "Oracle连接成功",
                    module="connection",
                    instance_id=self.instance.id,
                    username=attempt_username,
                    original_username=username,
                )
                
                return True
                
            except Exception as e:
                last_error = e
                error_message = str(e)
                
                # 如果是用户名/密码错误，继续尝试下一个
                if "ORA-01017" in error_message or "invalid username" in error_message.lower():
                    self.db_logger.debug(
                        "Oracle连接失败，尝试下一个用户名格式",
                        module="connection",
                        instance_id=self.instance.id,
                        username=attempt_username,
                        error=error_message,
                    )
                    continue
                else:
                    # 其他错误（如网络问题），直接抛出
                    raise

        # 所有尝试都失败
        if last_error:
            raise last_error
        
        return False

    except Exception as e:
        self.db_logger.error(
            "Oracle连接失败",
            module="connection",
            instance_id=self.instance.id,
            db_type="Oracle",
            error=str(e),
        )
        return False
```

### 方案 3：数据库层面统一（长期方案）⭐⭐⭐⭐

在数据库中统一用户名格式，推荐使用大写。

#### 数据迁移脚本

```python
# scripts/migrate_oracle_usernames_to_uppercase.py
"""
将数据库中的 Oracle 凭据用户名统一转换为大写
"""

from app import create_app, db
from app.models import Credential

def migrate_oracle_usernames():
    """迁移 Oracle 用户名为大写"""
    app = create_app()
    
    with app.app_context():
        # 查找所有 Oracle 类型的凭据
        oracle_credentials = Credential.query.filter_by(
            db_type='oracle',
            is_active=True
        ).all()
        
        updated_count = 0
        
        for credential in oracle_credentials:
            original_username = credential.username
            
            # 如果用户名不带引号且不是全大写，转换为大写
            if not original_username.startswith('"') and original_username != original_username.upper():
                credential.username = original_username.upper()
                updated_count += 1
                
                print(f"更新凭据 '{credential.name}': {original_username} -> {credential.username}")
        
        if updated_count > 0:
            db.session.commit()
            print(f"\n成功更新 {updated_count} 个 Oracle 凭据的用户名")
        else:
            print("没有需要更新的凭据")

if __name__ == "__main__":
    migrate_oracle_usernames()
```

运行迁移：
```bash
python scripts/migrate_oracle_usernames_to_uppercase.py
```

## 实施步骤

### 步骤 1：备份数据

```bash
# 备份凭据表
pg_dump -h localhost -U your_user -d your_database -t credentials > credentials_backup.sql
```

### 步骤 2：应用代码修改

选择方案 1（推荐）或方案 2，修改 `app/services/connection_adapters/connection_factory.py` 文件。

### 步骤 3：测试连接

```python
# 测试脚本
from app import create_app, db
from app.models import Instance
from app.services.connection_adapters.connection_factory import ConnectionFactory

app = create_app()

with app.app_context():
    # 替换为你的 Oracle 实例 ID
    instance = Instance.query.filter_by(db_type='oracle').first()
    
    if instance:
        print(f"测试实例: {instance.name}")
        print(f"主机: {instance.host}:{instance.port}")
        print(f"用户名: {instance.credential.username}")
        
        result = ConnectionFactory.test_connection(instance)
        
        if result['success']:
            print(f"✅ 连接成功: {result['message']}")
        else:
            print(f"❌ 连接失败: {result['error']}")
```

### 步骤 4：（可选）数据库迁移

如果选择方案 3，运行数据迁移脚本。

## 验证方法

### 1. 检查 Oracle 数据库中的实际用户名

在 Oracle 数据库中执行：

```sql
-- 查看所有用户名
SELECT username FROM dba_users ORDER BY username;

-- 查看特定用户
SELECT username, account_status, created 
FROM dba_users 
WHERE UPPER(username) = 'MYUSER';
```

### 2. 测试不同格式的用户名

```python
# 测试脚本
import oracledb

# 测试配置
host = "your_oracle_host"
port = 1521
service_name = "ORCL"
password = "your_password"

# 构建 DSN
dsn = oracledb.makedsn(host, port, service_name=service_name)

# 测试不同格式的用户名
test_usernames = [
    "myuser",      # 小写
    "MYUSER",      # 大写
    "MyUser",      # 混合
    '"myuser"',    # 带引号小写
]

for username in test_usernames:
    try:
        conn = oracledb.connect(user=username, password=password, dsn=dsn)
        print(f"✅ 用户名 '{username}' 连接成功")
        conn.close()
    except Exception as e:
        print(f"❌ 用户名 '{username}' 连接失败: {str(e)[:100]}")
```

## 常见问题

### Q1: 为什么 Oracle 要区分大小写？

A: Oracle 默认不区分大小写（自动转大写），但支持大小写敏感的用户名（使用引号创建）。这是为了兼容不同的命名规范。

### Q2: 如果我的用户名确实是小写的怎么办？

A: 如果你的 Oracle 用户是用引号创建的（如 `CREATE USER "myuser"`），那么在连接时也需要使用引号：
```python
username = '"myuser"'  # 注意外层是单引号，内层是双引号
```

### Q3: 修改后还是连接失败怎么办？

A: 检查以下几点：
1. 密码是否正确（使用 `credential.get_plain_password()` 验证）
2. 用户账户是否被锁定（`SELECT account_status FROM dba_users WHERE username='MYUSER'`）
3. 用户是否有 CREATE SESSION 权限（`GRANT CREATE SESSION TO myuser`）
4. 网络连接是否正常（`tnsping` 或 `telnet host port`）
5. Oracle 客户端是否正确安装

### Q4: 如何查看详细的连接日志？

A: 在日志配置中启用 DEBUG 级别：

```python
# 在 app/utils/structlog_config.py 中
import logging
logging.getLogger('app.services.connection_adapters').setLevel(logging.DEBUG)
```

然后查看日志文件：
```bash
tail -f logs/app.log | grep -i oracle
```

## 总结

**推荐方案：方案 1（自动转换为大写）**

这是最简单、最可靠的方案，因为：
1. 99% 的 Oracle 用户名都是大写的
2. 代码改动最小
3. 不需要数据迁移
4. 性能影响可忽略

如果你的环境中确实有小写敏感的用户名，可以考虑方案 2（智能检测）。

## 相关文件

- `app/services/connection_adapters/connection_factory.py` - 连接工厂
- `app/models/credential.py` - 凭据模型
- `app/routes/connections.py` - 连接测试路由
