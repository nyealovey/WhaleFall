# SQL Server 表权限显示错误修复方案

## 🔍 问题分析

### 当前问题
从用户截图可以看出，`receivable_sync` 用户在 `CreditManage` 数据库中有3个 `SELECT` 权限，这些实际上是**表级别的权限**，但系统显示为**数据库级别的权限**。

### 根本原因
当前的权限查询SQL只获取了权限名称，没有获取权限作用的对象信息：

```sql
SELECT '{db}' AS db_name,
       permission_name COLLATE SQL_Latin1_General_CP1_CI_AS AS permission_name,
       grantee_principal_id
FROM {quoted_db}.sys.database_permissions WHERE state = 'G'
```

**问题**: 缺少 `major_id` 和 `minor_id` 字段，无法区分权限是作用在数据库级别还是表级别。

## 🔧 解决方案

### 1. 修改权限查询SQL

需要获取完整的权限信息，包括权限作用的对象：

```sql
SELECT '{db}' AS db_name,
       permission_name COLLATE SQL_Latin1_General_CP1_CI_AS AS permission_name,
       grantee_principal_id,
       major_id,
       minor_id,
       CASE 
           WHEN major_id = 0 THEN 'DATABASE'
           WHEN major_id > 0 AND minor_id = 0 THEN 'SCHEMA'
           WHEN major_id > 0 AND minor_id > 0 THEN 'OBJECT'
       END AS permission_scope,
       CASE 
           WHEN major_id = 0 THEN 'DATABASE'
           WHEN major_id > 0 AND minor_id = 0 THEN 
               (SELECT name FROM {quoted_db}.sys.schemas WHERE schema_id = major_id)
           WHEN major_id > 0 AND minor_id > 0 THEN 
               (SELECT name FROM {quoted_db}.sys.objects WHERE object_id = major_id)
       END AS object_name
FROM {quoted_db}.sys.database_permissions WHERE state = 'G'
```

### 2. 修改数据结构

需要将权限按作用范围分类存储：

```python
# 修改前
result[username]["permissions"][db_name] = [permission_name1, permission_name2, ...]

# 修改后
result[username]["permissions"][db_name] = {
    "database": [permission_name1, permission_name2, ...],
    "schema": {
        "dbo": [permission_name1, permission_name2, ...],
        "schema2": [permission_name1, permission_name2, ...]
    },
    "table": {
        "dbo.Receivable_Balance": [permission_name1, permission_name2, ...],
        "dbo.Receivable_Budget": [permission_name1, permission_name2, ...]
    }
}
```

### 3. 修改权限处理逻辑

```python
def _process_database_permissions(self, all_perms, result, usernames, db_principals, username_to_sid):
    """处理数据库权限，按作用范围分类"""
    for row in all_perms:
        db_name, permission_name, grantee_principal_id, major_id, minor_id, scope, object_name = row
        
        # 查找对应的用户名
        user_name = self._find_user_by_principal_id(grantee_principal_id, db_name, db_principals, usernames)
        
        if user_name:
            if db_name not in result[user_name]["permissions"]:
                result[user_name]["permissions"][db_name] = {
                    "database": [],
                    "schema": {},
                    "table": {}
                }
            
            # 根据权限作用范围分类存储
            if scope == "DATABASE":
                result[user_name]["permissions"][db_name]["database"].append(permission_name)
            elif scope == "SCHEMA":
                schema_name = object_name
                if schema_name not in result[user_name]["permissions"][db_name]["schema"]:
                    result[user_name]["permissions"][db_name]["schema"][schema_name] = []
                result[user_name]["permissions"][db_name]["schema"][schema_name].append(permission_name)
            elif scope == "OBJECT":
                table_name = f"{object_name}"  # 可以加上schema前缀
                if table_name not in result[user_name]["permissions"][db_name]["table"]:
                    result[user_name]["permissions"][db_name]["table"][table_name] = []
                result[user_name]["permissions"][db_name]["table"][table_name].append(permission_name)
```

### 4. 修改前端显示逻辑

需要修改 `get_permissions_by_db_type` 方法，支持按权限作用范围显示：

```python
def get_permissions_by_db_type(self) -> dict:
    """根据数据库类型获取权限信息"""
    if self.db_type == "sqlserver":
        return {
            "server_roles": self.server_roles,
            "server_permissions": self.server_permissions,
            "database_roles": self.database_roles,
            "database_permissions": self.database_permissions,  # 现在包含分类的权限
            "type_specific": self.type_specific,
        }
```

### 5. 修改前端模板

需要修改权限显示模板，支持按权限作用范围显示：

```html
<!-- 数据库权限 -->
<div class="permission-section">
    <h6>数据库权限</h6>
    <div class="permission-category">
        <strong>数据库级别:</strong>
        <span class="badge bg-primary" v-for="perm in account.permissions.database" :key="perm">
            {{ perm }}
        </span>
    </div>
    
    <div class="permission-category" v-if="Object.keys(account.permissions.schema).length > 0">
        <strong>架构级别:</strong>
        <div v-for="(perms, schema) in account.permissions.schema" :key="schema" class="schema-perms">
            <span class="schema-name">{{ schema }}:</span>
            <span class="badge bg-info" v-for="perm in perms" :key="perm">
                {{ perm }}
            </span>
        </div>
    </div>
    
    <div class="permission-category" v-if="Object.keys(account.permissions.table).length > 0">
        <strong>表级别:</strong>
        <div v-for="(perms, table) in account.permissions.table" :key="table" class="table-perms">
            <span class="table-name">{{ table }}:</span>
            <span class="badge bg-warning" v-for="perm in perms" :key="perm">
                {{ perm }}
            </span>
        </div>
    </div>
</div>
```

## 🚀 实施步骤

### 第一步：修改权限查询SQL
1. 更新 `_get_all_users_database_permissions_batch` 方法中的权限查询SQL
2. 添加 `major_id`, `minor_id`, `permission_scope`, `object_name` 字段

### 第二步：修改数据结构
1. 更新权限存储结构，支持按作用范围分类
2. 修改权限处理逻辑

### 第三步：修改前端显示
1. 更新 `get_permissions_by_db_type` 方法
2. 修改前端模板，支持分类显示权限

### 第四步：测试验证
1. 测试权限查询是否准确
2. 验证前端显示是否正确
3. 确保权限分类清晰

## 📊 预期效果

修复后的权限显示应该如下：

```
数据库权限 (CreditManage):
├── 数据库级别: CONNECT
├── 架构级别: 
│   └── dbo: SELECT
└── 表级别:
    ├── dbo.Receivable_Balance: SELECT
    ├── dbo.Receivable_Budget: SELECT
    └── dbo.Receivable_Budget_Hy: SELECT
```

## 🔗 相关文件

- `app/services/sync_adapters/sqlserver_sync_adapter.py` - 权限查询逻辑
- `app/models/current_account_sync_data.py` - 数据模型
- `app/templates/accounts/` - 前端模板
- `app/static/js/account_classification.js` - 前端JavaScript

## 🔧 已实施的修复

### 1. 修改权限查询SQL ✅
- **修改位置**: 两个权限查询方法
- **修改内容**: 添加 `major_id`, `minor_id`, `permission_scope`, `object_name` 字段
- **影响**: 现在可以区分权限是作用在数据库级别、架构级别还是表级别

### 2. 修改权限存储结构 ✅
- **修改位置**: 权限处理逻辑
- **修改内容**: 将权限按作用范围分类存储
- **影响**: 权限现在按 `database`, `schema`, `table` 分类存储

### 3. 修改权限处理逻辑 ✅
- **修改位置**: 两个权限处理方法
- **修改内容**: 根据权限作用范围分类存储权限
- **影响**: 表权限现在正确显示为表级别权限

### 4. 修改排序和统计逻辑 ✅
- **修改位置**: 排序和统计代码
- **修改内容**: 支持新的权限结构排序和统计
- **影响**: 权限显示更加清晰和准确

## 📝 更新历史

- 2025-01-22 - 初始分析，识别表权限显示错误问题
- 2025-01-22 - 创建详细修复方案
- 2025-01-22 - 实施修复：修改权限查询和存储逻辑
