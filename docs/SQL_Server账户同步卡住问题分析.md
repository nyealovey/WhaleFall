# SQL Server 账户同步卡住问题分析

## 问题描述

在执行账户同步任务时，SQL Server 实例的同步会卡住，无法正常完成。

## 根因分析

### 🔴 核心问题：`_get_database_permissions()` 方法存在严重性能问题

位置：`app/services/account_sync/adapters/sqlserver_adapter.py` 第 177-207 行

```python
def _get_database_permissions(self, connection: Any, login_name: str) -> Dict[str, List[str]]:
    rows: List[tuple[Any, Any]] = []
    # 1. 获取所有在线数据库
    databases = connection.execute_query(
        "SELECT name FROM sys.databases WHERE state_desc = 'ONLINE'"
    )
    # 2. 遍历每个数据库
    for db_name_tuple in databases:
        database = db_name_tuple[0]
        if not database:
            continue
        safe_db_name = database.replace("]", "]]")
        quoted_db = f"[{safe_db_name}]"
        # 3. 对每个数据库执行查询
        sql = f"""
            SELECT '{database}' AS database_name, perm.permission_name
            FROM {quoted_db}.sys.database_permissions perm
            JOIN {quoted_db}.sys.database_principals dp ON perm.grantee_principal_id = dp.principal_id
            WHERE dp.name = %s
        """
        try:
            db_rows = connection.execute_query(sql, (login_name,))
            rows.extend(db_rows)
        except Exception as exc:
            self.logger.warning(...)
    ...
```

### 问题分析

#### 1. **N+1 查询问题**

- 首先查询所有在线数据库（1次查询）
- 然后对每个数据库执行一次查询（N次查询）
- 如果实例有 100 个数据库，就会执行 101 次查询

#### 2. **跨数据库查询性能差**

```sql
FROM {quoted_db}.sys.database_permissions perm
JOIN {quoted_db}.sys.database_principals dp ON ...
```

- 每次查询都需要切换数据库上下文
- 跨数据库的 JOIN 操作性能较差
- 如果数据库很大，每次查询都可能很慢

#### 3. **累积效应导致卡住**

假设场景：
- 实例有 50 个数据库
- 每个数据库查询耗时 2 秒
- 单个账户的权限查询就需要：50 × 2 = 100 秒

如果有 10 个账户需要同步：
- 总耗时：10 × 100 = 1000 秒 ≈ 16.7 分钟

如果有 100 个账户：
- 总耗时：100 × 100 = 10000 秒 ≈ 2.8 小时

**这就是为什么会"卡住"！**

#### 4. **其他性能问题**

`_get_database_roles()` 方法也有类似问题（第 167-175 行）：

```python
def _get_database_roles(self, connection: Any, login_name: str) -> Dict[str, List[str]]:
    sql = """
        SELECT dp.name AS database_name, mp.name AS role_name
        FROM sys.server_principals sp
        JOIN sys.database_principals mp ON mp.sid = sp.sid
        JOIN sys.databases dp ON dp.owner_sid = mp.sid
        WHERE sp.name = %s
    """
    rows = connection.execute_query(sql, (login_name,))
    ...
```

这个 SQL 的 JOIN 逻辑有问题：
- `sys.databases.owner_sid` 是数据库的所有者 SID
- 不应该用来关联用户的数据库角色
- 这个查询可能返回错误的结果或者空结果

## 解决方案

### 方案 1：优化 SQL 查询（推荐）

#### 1.1 优化 `_get_database_permissions()`

使用动态 SQL 一次性查询所有数据库的权限：

```python
def _get_database_permissions(self, connection: Any, login_name: str) -> Dict[str, List[str]]:
    """获取用户在所有数据库的权限（优化版）"""
    
    # 构建动态 SQL，一次性查询所有数据库
    sql = """
    DECLARE @sql NVARCHAR(MAX) = N'';
    
    SELECT @sql = @sql + N'
    SELECT ''' + name + ''' AS database_name, perm.permission_name
    FROM [' + name + '].sys.database_permissions perm
    JOIN [' + name + '].sys.database_principals dp ON perm.grantee_principal_id = dp.principal_id
    WHERE dp.name = @login_name
    UNION ALL '
    FROM sys.databases
    WHERE state_desc = 'ONLINE'
      AND name NOT IN ('master', 'tempdb', 'model', 'msdb');  -- 可选：排除系统数据库
    
    -- 移除最后的 UNION ALL
    SET @sql = LEFT(@sql, LEN(@sql) - 10);
    
    -- 执行动态 SQL
    EXEC sp_executesql @sql, N'@login_name NVARCHAR(128)', @login_name = @login_name;
    """
    
    try:
        rows = connection.execute_query(sql, (login_name,))
        db_perms: Dict[str, List[str]] = {}
        for row in rows:
            database = row[0]
            permission = row[1]
            if database and permission:
                db_perms.setdefault(database, []).append(permission)
        return db_perms
    except Exception as exc:
        self.logger.error(
            "fetch_sqlserver_db_permissions_failed",
            login=login_name,
            error=str(exc),
            exc_info=True,
        )
        return {}
```

**优点**：
- 只执行 1 次查询，而不是 N+1 次
- 性能提升 N 倍（N = 数据库数量）
- 减少网络往返次数

**预期效果**：
- 原来 100 秒的查询 → 优化后 2-5 秒
- 原来 16 分钟的同步 → 优化后 1-2 分钟

#### 1.2 修复 `_get_database_roles()`

正确的查询应该是：

```python
def _get_database_roles(self, connection: Any, login_name: str) -> Dict[str, List[str]]:
    """获取用户在所有数据库的角色（修复版）"""
    
    sql = """
    DECLARE @sql NVARCHAR(MAX) = N'';
    
    SELECT @sql = @sql + N'
    SELECT ''' + name + ''' AS database_name, role.name AS role_name
    FROM [' + name + '].sys.database_role_members rm
    JOIN [' + name + '].sys.database_principals role ON rm.role_principal_id = role.principal_id
    JOIN [' + name + '].sys.database_principals member ON rm.member_principal_id = member.principal_id
    WHERE member.name = @login_name
    UNION ALL '
    FROM sys.databases
    WHERE state_desc = 'ONLINE'
      AND name NOT IN ('master', 'tempdb', 'model', 'msdb');
    
    SET @sql = LEFT(@sql, LEN(@sql) - 10);
    
    EXEC sp_executesql @sql, N'@login_name NVARCHAR(128)', @login_name = @login_name;
    """
    
    try:
        rows = connection.execute_query(sql, (login_name,))
        db_roles: Dict[str, List[str]] = {}
        for row in rows:
            database = row[0]
            role = row[1]
            if database and role:
                db_roles.setdefault(database, []).append(role)
        return db_roles
    except Exception as exc:
        self.logger.error(
            "fetch_sqlserver_db_roles_failed",
            login=login_name,
            error=str(exc),
            exc_info=True,
        )
        return {}
```

### 方案 2：添加超时和限制（临时缓解）

如果不能立即修改 SQL，可以先添加超时机制：

```python
def _get_database_permissions(self, connection: Any, login_name: str) -> Dict[str, List[str]]:
    """获取用户在所有数据库的权限（带超时版）"""
    import time
    
    rows: List[tuple[Any, Any]] = []
    databases = connection.execute_query(
        "SELECT name FROM sys.databases WHERE state_desc = 'ONLINE'"
    )
    
    # 添加超时控制
    start_time = time.time()
    timeout = 60  # 60秒超时
    max_databases = 50  # 最多查询50个数据库
    
    processed = 0
    for db_name_tuple in databases:
        # 检查超时
        if time.time() - start_time > timeout:
            self.logger.warning(
                "fetch_sqlserver_db_permissions_timeout",
                login=login_name,
                processed_databases=processed,
                timeout=timeout
            )
            break
        
        # 检查数量限制
        if processed >= max_databases:
            self.logger.warning(
                "fetch_sqlserver_db_permissions_limit_reached",
                login=login_name,
                max_databases=max_databases
            )
            break
        
        database = db_name_tuple[0]
        if not database:
            continue
        
        safe_db_name = database.replace("]", "]]")
        quoted_db = f"[{safe_db_name}]"
        sql = f"""
            SELECT '{database}' AS database_name, perm.permission_name
            FROM {quoted_db}.sys.database_permissions perm
            JOIN {quoted_db}.sys.database_principals dp ON perm.grantee_principal_id = dp.principal_id
            WHERE dp.name = %s
        """
        try:
            db_rows = connection.execute_query(sql, (login_name,))
            rows.extend(db_rows)
            processed += 1
        except Exception as exc:
            self.logger.warning(
                "fetch_sqlserver_db_permissions_failed",
                database=database,
                login=login_name,
                error=str(exc),
            )
    
    db_perms: Dict[str, List[str]] = {}
    for row in rows:
        database = row[0]
        permission = row[1]
        if database and permission:
            db_perms.setdefault(database, []).append(permission)
    
    return db_perms
```

### 方案 3：异步批量查询（高级方案）

如果数据库数量特别多，可以考虑：

1. **分批查询**：每次查询 10 个数据库
2. **并行查询**：使用多线程/协程并行查询
3. **缓存结果**：缓存权限信息，避免重复查询

```python
def _get_database_permissions_batch(
    self, 
    connection: Any, 
    login_name: str,
    batch_size: int = 10
) -> Dict[str, List[str]]:
    """分批查询数据库权限"""
    
    databases = connection.execute_query(
        "SELECT name FROM sys.databases WHERE state_desc = 'ONLINE'"
    )
    
    db_names = [db[0] for db in databases if db[0]]
    db_perms: Dict[str, List[str]] = {}
    
    # 分批处理
    for i in range(0, len(db_names), batch_size):
        batch = db_names[i:i + batch_size]
        
        # 构建批量查询 SQL
        union_parts = []
        for db_name in batch:
            safe_db_name = db_name.replace("]", "]]")
            union_parts.append(f"""
                SELECT '{db_name}' AS database_name, perm.permission_name
                FROM [{safe_db_name}].sys.database_permissions perm
                JOIN [{safe_db_name}].sys.database_principals dp 
                  ON perm.grantee_principal_id = dp.principal_id
                WHERE dp.name = %s
            """)
        
        sql = " UNION ALL ".join(union_parts)
        
        try:
            rows = connection.execute_query(sql, (login_name,))
            for row in rows:
                database = row[0]
                permission = row[1]
                if database and permission:
                    db_perms.setdefault(database, []).append(permission)
        except Exception as exc:
            self.logger.error(
                "fetch_sqlserver_db_permissions_batch_failed",
                login=login_name,
                batch=batch,
                error=str(exc),
            )
    
    return db_perms
```

## 推荐实施步骤

### 第一步：立即实施（紧急修复）

1. **添加超时机制**（方案 2）
   - 防止无限期卡住
   - 快速缓解问题
   - 不改变核心逻辑

### 第二步：性能优化（根本解决）

1. **实施方案 1**：优化 SQL 查询
   - 修改 `_get_database_permissions()`
   - 修改 `_get_database_roles()`
   - 进行充分测试

### 第三步：监控和调优

1. **添加性能监控**
   ```python
   import time
   
   def _get_database_permissions(self, connection: Any, login_name: str) -> Dict[str, List[str]]:
       start_time = time.time()
       try:
           result = # ... 执行查询
           duration = time.time() - start_time
           self.logger.info(
               "fetch_sqlserver_db_permissions_completed",
               login=login_name,
               duration=duration,
               database_count=len(result)
           )
           return result
       except Exception as exc:
           duration = time.time() - start_time
           self.logger.error(
               "fetch_sqlserver_db_permissions_failed",
               login=login_name,
               duration=duration,
               error=str(exc)
           )
           raise
   ```

2. **添加告警**
   - 如果单个账户查询超过 30 秒，发出告警
   - 如果总同步时间超过 10 分钟，发出告警

## 测试建议

### 1. 性能测试

```python
# 测试脚本
def test_sqlserver_permission_query_performance():
    """测试 SQL Server 权限查询性能"""
    from app.services.account_sync.adapters.sqlserver_adapter import SQLServerAccountAdapter
    from app.models.instance import Instance
    import time
    
    instance = Instance.query.filter_by(db_type='sqlserver').first()
    adapter = SQLServerAccountAdapter()
    
    with adapter.connect(instance) as connection:
        # 获取一个测试账户
        logins = adapter._fetch_logins(connection)
        test_login = logins[0]['name'] if logins else None
        
        if not test_login:
            print("没有找到测试账户")
            return
        
        print(f"测试账户: {test_login}")
        
        # 测试旧方法
        start = time.time()
        old_result = adapter._get_database_permissions(connection, test_login)
        old_duration = time.time() - start
        
        print(f"旧方法耗时: {old_duration:.2f} 秒")
        print(f"查询到 {len(old_result)} 个数据库的权限")
        
        # 测试新方法（如果已实现）
        # start = time.time()
        # new_result = adapter._get_database_permissions_optimized(connection, test_login)
        # new_duration = time.time() - start
        # print(f"新方法耗时: {new_duration:.2f} 秒")
        # print(f"性能提升: {old_duration / new_duration:.2f}x")
```

### 2. 功能测试

确保优化后的查询返回相同的结果：

```python
def test_query_result_consistency():
    """测试查询结果一致性"""
    # 对比旧方法和新方法的结果
    old_result = adapter._get_database_permissions(connection, login_name)
    new_result = adapter._get_database_permissions_optimized(connection, login_name)
    
    assert old_result == new_result, "查询结果不一致"
```

## 其他建议

### 1. 考虑是否需要所有数据库的权限

如果业务上不需要查询所有数据库的权限，可以：

- 只查询用户数据库（排除系统数据库）
- 只查询有权限的数据库
- 提供配置选项让用户选择

### 2. 添加数据库过滤配置

```python
# 在配置文件中添加
SQLSERVER_PERMISSION_SYNC_CONFIG = {
    'exclude_system_databases': True,  # 排除系统数据库
    'exclude_databases': ['tempdb', 'model'],  # 排除特定数据库
    'max_databases': 100,  # 最多查询的数据库数量
    'timeout': 60,  # 查询超时时间（秒）
}
```

### 3. 考虑权限同步的必要性

评估是否真的需要同步所有数据库的详细权限：

- 如果只是为了展示，可以只同步服务器级别的权限
- 数据库级别的权限可以按需查询（用户点击时再查）
- 或者只同步用户有权限的数据库

## 总结

SQL Server 账户同步卡住的根本原因是 **N+1 查询问题**，导致性能呈线性下降。

**立即行动**：
1. 添加超时机制（临时缓解）
2. 优化 SQL 查询（根本解决）
3. 添加性能监控（持续改进）

**预期效果**：
- 同步时间从 10+ 分钟降低到 1-2 分钟
- 不再出现"卡住"的现象
- 提升用户体验
