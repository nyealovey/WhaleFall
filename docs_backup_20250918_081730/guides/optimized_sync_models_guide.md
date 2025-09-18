# 优化同步模型使用指南

## 概述

泰摸鱼吧V4.0引入了全新的优化同步模型，用于统一管理多数据库类型的账户权限同步。新模型支持MySQL、PostgreSQL、SQL Server和Oracle的复杂权限结构，提供更高效的存储和查询性能。

## 核心特性

### 1. 统一存储模型
- **当前状态表** (`current_account_sync_data`): 存储账户的当前权限状态
- **变更日志表** (`account_change_log`): 记录所有权限变更历史
- **支持删除标记**: 标记已删除账户，但不支持恢复功能

### 2. 复杂权限结构支持
- **MySQL**: 全局权限 + 数据库权限
- **PostgreSQL**: 预定义角色 + 角色属性 + 数据库权限 + 表空间权限
- **SQL Server**: 服务器角色 + 服务器权限 + 数据库角色 + 数据库权限
- **Oracle**: 角色 + 系统权限 + 表空间权限（移除表空间配额）

### 3. 智能变更检测
- 自动检测权限变更
- 计算变更差异
- 记录变更历史

## 数据模型

### CurrentAccountSyncData (账户当前状态表)

```python
class CurrentAccountSyncData(BaseSyncData):
    # 基本信息
    username = db.Column(db.String(255), nullable=False)
    is_superuser = db.Column(db.Boolean, default=False)

    # MySQL权限
    global_privileges = db.Column(db.JSON, nullable=True)
    database_privileges = db.Column(db.JSON, nullable=True)

    # PostgreSQL权限
    predefined_roles = db.Column(db.JSON, nullable=True)
    role_attributes = db.Column(db.JSON, nullable=True)
    database_privileges_pg = db.Column(db.JSON, nullable=True)
    tablespace_privileges = db.Column(db.JSON, nullable=True)

    # SQL Server权限
    server_roles = db.Column(db.JSON, nullable=True)
    server_permissions = db.Column(db.JSON, nullable=True)
    database_roles = db.Column(db.JSON, nullable=True)
    database_permissions = db.Column(db.JSON, nullable=True)

    # Oracle权限
    oracle_roles = db.Column(db.JSON, nullable=True)
    system_privileges = db.Column(db.JSON, nullable=True)
    tablespace_privileges_oracle = db.Column(db.JSON, nullable=True)

    # 状态字段
    is_deleted = db.Column(db.Boolean, default=False)
    last_sync_time = db.Column(db.DateTime, default=datetime.utcnow)
    last_change_type = db.Column(db.String(20), default="add")
```

### AccountChangeLog (变更日志表)

```python
class AccountChangeLog(db.Model):
    # 基本信息
    instance_id = db.Column(db.Integer, nullable=False)
    db_type = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    change_type = db.Column(db.String(50), nullable=False)
    change_time = db.Column(db.DateTime, default=datetime.utcnow)

    # 变更差异
    privilege_diff = db.Column(db.JSON, nullable=True)
    other_diff = db.Column(db.JSON, nullable=True)
```

## API接口

### 1. 获取实例账户列表

```http
GET /instance_accounts/{instance_id}/accounts
```

**查询参数:**
- `db_type`: 数据库类型过滤 (mysql, postgresql, sqlserver, oracle)
- `include_deleted`: 是否包含已删除账户 (true/false)

**响应示例:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "username": "test_user",
            "db_type": "mysql",
            "is_superuser": false,
            "global_privileges": ["SELECT", "INSERT"],
            "database_privileges": {"testdb": ["SELECT"]},
            "is_deleted": false,
            "last_sync_time": "2025-01-14T12:00:00Z"
        }
    ],
    "count": 1
}
```

### 2. 查看账户权限详情

```http
GET /instance_accounts/{instance_id}/accounts/{username}/permissions?db_type={db_type}
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "username": "test_user",
        "db_type": "mysql",
        "is_superuser": false,
        "permissions": {
            "global_privileges": ["SELECT", "INSERT"],
            "database_privileges": {"testdb": ["SELECT"]},
            "type_specific": {"host": "%", "plugin": "caching_sha2_password"}
        }
    }
}
```

### 3. 查看账户变更历史

```http
GET /instance_accounts/{instance_id}/accounts/{username}/history?db_type={db_type}
```

**响应示例:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "change_type": "modify_privilege",
            "change_time": "2025-01-14T12:00:00Z",
            "privilege_diff": {
                "global_privileges": {
                    "added": ["UPDATE"],
                    "removed": []
                }
            }
        }
    ]
}
```

### 4. 标记账户为已删除

```http
POST /instance_accounts/{instance_id}/accounts/{username}/delete?db_type={db_type}
```

### 5. 获取账户统计信息

```http
GET /instance_accounts/{instance_id}/accounts/statistics
```

## 服务层使用

### SyncDataManager

```python
from app.services.sync_data_manager import SyncDataManager

# 获取账户最新状态
account = SyncDataManager.get_account_latest("mysql", instance_id, "username")

# 获取实例所有账户
accounts = SyncDataManager.get_accounts_by_instance(instance_id)

# 更新账户权限
SyncDataManager.upsert_account(
    instance_id=1,
    db_type="mysql",
    username="test_user",
    permissions_data={
        "global_privileges": ["SELECT", "INSERT"],
        "database_privileges": {"testdb": ["SELECT"]}
    }
)

# 标记账户为已删除
SyncDataManager.mark_account_deleted(instance_id, "mysql", "test_user")
```

## UI集成

### 实例详情页面

在实例详情页面新增了"优化账户列表"部分，提供以下功能：

1. **账户列表展示**: 显示所有账户的基本信息
2. **权限查看**: 点击"权限"按钮查看详细权限信息
3. **历史查看**: 点击"历史"按钮查看变更历史
4. **删除操作**: 标记账户为已删除
5. **过滤功能**: 按数据库类型和删除状态过滤

### 权限查看模态框

- 显示账户基本信息
- 展示权限详情（JSON格式）
- 支持不同数据库类型的权限结构

### 变更历史模态框

- 按时间倒序显示变更记录
- 显示变更类型和描述
- 展示权限变更差异

## 数据库迁移

### 创建新表

```sql
-- 执行迁移脚本
-- PostgreSQL
\i sql/create_optimized_sync_tables.sql

-- SQLite
\i sql/create_optimized_sync_tables_sqlite.sql
```

### 索引优化

新表包含以下索引以优化查询性能：

- `idx_current_account_instance_dbtype`: 实例+数据库类型复合索引
- `idx_current_account_deleted`: 删除状态索引
- `idx_current_account_username`: 用户名索引
- `idx_change_log_instance_dbtype_username_time`: 变更日志复合索引

## 性能优化

### 存储空间优化

- 使用JSON字段存储复杂权限结构
- 避免重复存储相同数据
- 预计减少80%存储空间

### 查询性能优化

- 合理的索引设计
- 复合索引支持多条件查询
- 预计提升3倍查询性能

## 最佳实践

### 1. 权限同步

```python
# 推荐：使用SyncDataManager进行权限同步
permissions_data = {
    "global_privileges": ["SELECT", "INSERT"],
    "database_privileges": {"testdb": ["SELECT"]},
    "type_specific": {"host": "%"}
}

SyncDataManager.upsert_account(
    instance_id=instance_id,
    db_type="mysql",
    username=username,
    permissions_data=permissions_data
)
```

### 2. 变更检测

系统会自动检测权限变更并记录差异，无需手动处理。

### 3. 错误处理

```python
try:
    account = SyncDataManager.get_account_latest("mysql", instance_id, username)
    if not account:
        # 处理账户不存在的情况
        pass
except Exception as e:
    # 记录错误并处理
    logger.error(f"获取账户失败: {e}")
```

## 注意事项

1. **删除操作不可恢复**: 标记为已删除的账户无法恢复
2. **权限结构差异**: 不同数据库类型的权限结构不同，需要正确映射
3. **JSON字段限制**: 某些数据库对JSON字段有大小限制
4. **索引维护**: 定期检查索引使用情况，必要时重建

## 故障排除

### 常见问题

1. **权限同步失败**
   - 检查数据库连接
   - 验证权限数据格式
   - 查看错误日志

2. **查询性能慢**
   - 检查索引是否创建
   - 分析查询执行计划
   - 考虑添加复合索引

3. **UI显示异常**
   - 检查JavaScript控制台错误
   - 验证API响应格式
   - 确认CSRF令牌

### 调试工具

```python
# 启用调试日志
import logging
logging.getLogger('app.services.sync_data_manager').setLevel(logging.DEBUG)

# 查看权限变更检测
changes = SyncDataManager._detect_mysql_changes(old_account, new_permissions)
print(f"检测到变更: {changes}")
```

## 更新日志

### v4.0.0 (2025-01-14)
- 新增优化同步模型
- 支持复杂权限结构
- 实现智能变更检测
- 添加UI集成功能
- 提供完整的API接口

---

**作者**: AI Assistant
**更新时间**: 2025-01-14
**版本**: 4.0.0
