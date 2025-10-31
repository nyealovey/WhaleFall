# 账户同步适配器重构文档

## 1. 代码重复分析

### 1.1 重复代码概览

经过分析 `app/services/account_sync_adapters` 目录，发现以下严重的代码重复问题：

#### 高度重复的代码模式（80%+ 相似度）

1. **过滤条件构建** - 所有适配器中的 `_build_filter_conditions()` 方法
2. **变更检测逻辑** - `_detect_changes()` 方法的结构完全一致
3. **权限更新逻辑** - `_update_account_permissions()` 方法的模式相同
4. **变更描述生成** - `_generate_change_description()` 方法的逻辑重复
5. **账户数据格式化** - `format_account_data()` 和 `extract_permissions()` 方法

#### 中度重复的代码模式（50-80% 相似度）

1. **批量查询优化** - Oracle 和 SQL Server 的批量查询模式相似
2. **权限数据结构** - 各数据库的权限数据结构有共同模式
3. **错误处理** - 异常捕获和日志记录的模式重复
4. **is_active 状态推导** - 从 type_specific 中提取 is_active 的逻辑重复

### 1.2 具体重复代码示例

#### 示例 1: 过滤条件构建（4个文件完全重复）

```python
# mysql_sync_adapter.py, postgresql_sync_adapter.py, 
# oracle_sync_adapter.py, sqlserver_sync_adapter.py
def _build_filter_conditions(self) -> tuple[str, list]:
    """构建过滤条件"""
    filter_rules = self.filter_manager.get_filter_rules("数据库类型")
    builder = SafeQueryBuilder(db_type="数据库类型")
    exclude_users = filter_rules.get("exclude_users", [])
    exclude_patterns = filter_rules.get("exclude_patterns", [])
    builder.add_database_specific_condition("字段名", exclude_users, exclude_patterns)
    return builder.build_where_clause()
```

**重复次数**: 4次（每个适配器一次）
**差异**: 仅数据库类型和字段名不同


#### 示例 2: 变更检测逻辑（结构完全一致）

```python
# 所有适配器中的 _detect_changes() 方法都遵循相同模式：
def _detect_changes(self, existing_account, new_permissions, *, is_superuser):
    changes = {}
    
    # 1. 检测超级用户状态变更（完全相同）
    if existing_account.is_superuser != is_superuser:
        changes["is_superuser"] = {"old": existing_account.is_superuser, "new": is_superuser}
    
    # 2. 检测 is_active 状态变更（完全相同）
    new_is_active = new_permissions.get("type_specific", {}).get("is_active", False)
    if existing_account.is_active != new_is_active:
        changes["is_active"] = {"old": existing_account.is_active, "new": new_is_active}
    
    # 3. 检测各种权限变更（模式相同，字段名不同）
    # MySQL: global_privileges, database_privileges
    # PostgreSQL: predefined_roles, role_attributes, database_privileges_pg
    # Oracle: oracle_roles, system_privileges, tablespace_privileges_oracle
    # SQL Server: server_roles, server_permissions, database_roles, database_permissions
    
    # 4. 检测 type_specific 变更（完全相同）
    old_type_specific = existing_account.type_specific or {}
    new_type_specific = new_permissions.get("type_specific", {})
    if old_type_specific != new_type_specific:
        changes["type_specific"] = {
            "added": {...},
            "removed": {...}
        }
    
    return changes
```

**重复次数**: 4次
**差异**: 仅权限字段名称不同，逻辑完全一致

#### 示例 3: 变更描述生成（模式重复）

```python
# 所有适配器的 _generate_change_description() 都遵循相同模式
def _generate_change_description(self, db_type, changes):
    descriptions = []
    
    # 1. 超级用户状态变更描述（完全相同）
    if "is_superuser" in changes:
        new_value = changes["is_superuser"]["new"]
        if new_value:
            descriptions.append("提升为超级用户")
        else:
            descriptions.append("取消超级用户权限")
    
    # 2. 各种权限变更描述（模式相同）
    # 遍历 added/removed，生成描述字符串
    
    return descriptions
```

**重复次数**: 4次
**差异**: 权限字段名称和描述文本略有不同

### 1.3 重复代码统计

| 方法名 | 重复次数 | 代码行数 | 相似度 | 维护成本 |
|--------|---------|---------|--------|---------|
| `_build_filter_conditions()` | 4 | ~10行/次 | 95% | 高 |
| `_detect_changes()` | 4 | ~80行/次 | 85% | 极高 |
| `_update_account_permissions()` | 4 | ~20行/次 | 90% | 高 |
| `_create_new_account()` | 4 | ~20行/次 | 90% | 高 |
| `_generate_change_description()` | 4 | ~50行/次 | 80% | 高 |
| `format_account_data()` | 4 | ~10行/次 | 95% | 中 |
| `extract_permissions()` | 4 | ~3行/次 | 100% | 低 |

**总计重复代码**: 约 800+ 行（占总代码量的 40%）

## 2
. 问题分析

### 2.1 当前架构的问题

1. **维护成本高**
   - 修改一个通用逻辑需要在4个文件中重复修改
   - 容易出现不一致的实现
   - 增加新数据库类型需要复制大量代码

2. **测试覆盖困难**
   - 相同逻辑需要在4个适配器中分别测试
   - 测试用例重复度高
   - 难以保证所有适配器行为一致

3. **代码可读性差**
   - 大量重复代码干扰核心逻辑
   - 难以快速定位数据库特定的实现
   - 新开发者学习成本高

4. **扩展性差**
   - 添加新功能需要修改所有适配器
   - 难以实现跨数据库的通用优化
   - 缺乏统一的权限模型抽象

### 2.2 根本原因

1. **缺乏抽象层**
   - 没有提取通用的权限变更检测逻辑
   - 没有统一的权限字段映射机制
   - 缺少配置驱动的实现方式

2. **职责划分不清**
   - 适配器既负责数据库查询，又负责通用逻辑
   - 基类 `BaseSyncAdapter` 只定义接口，没有提供通用实现
   - 缺少专门的权限比较和变更检测组件

3. **过度依赖继承**
   - 所有通用逻辑都在基类中，但实现在子类
   - 无法灵活组合不同的功能模块
   - 难以实现代码复用

## 3. 重构方案

### 3.1 重构目标

1. **消除重复代码**: 将重复代码减少到 10% 以下
2. **提高可维护性**: 通用逻辑修改只需改一处
3. **增强可扩展性**: 新增数据库类型只需实现核心查询逻辑
4. **保持向后兼容**: 不影响现有功能和API

### 3.2 重构策略

#### 策略 1: 提取通用权限比较器（推荐）

**核心思想**: 将权限变更检测逻辑提取为独立的通用组件

```python
# 新增文件: app/services/account_sync_adapters/permission_comparator.py
class PermissionComparator:
    """通用权限比较器"""
    
    @staticmethod
    def detect_changes(existing_account, new_permissions, field_mapping, *, is_superuser):
        """
        通用的变更检测逻辑
        
        Args:
            existing_account: 现有账户对象
            new_permissions: 新权限数据
            field_mapping: 字段映射配置
            is_superuser: 是否超级用户
        """
        changes = {}
        
        # 1. 检测超级用户状态变更
        if existing_account.is_superuser != is_superuser:
            changes["is_superuser"] = {
                "old": existing_account.is_superuser, 
                "new": is_superuser
            }
        
        # 2. 检测 is_active 状态变更
        new_is_active = new_permissions.get("type_specific", {}).get("is_active", False)
        if existing_account.is_active != new_is_active:
            changes["is_active"] = {
                "old": existing_account.is_active, 
                "new": new_is_active
            }
        
        # 3. 根据字段映射检测各种权限变更
        for field_name, field_config in field_mapping.items():
            field_type = field_config.get("type", "list")
            
            if field_type == "list":
                changes.update(
                    PermissionComparator._detect_list_changes(
                        existing_account, new_permissions, field_name, field_config
                    )
                )
            elif field_type == "dict":
                changes.update(
                    PermissionComparator._detect_dict_changes(
                        existing_account, new_permissions, field_name, field_config
                    )
                )
        
        # 4. 检测 type_specific 变更
        old_type_specific = existing_account.type_specific or {}
        new_type_specific = new_permissions.get("type_specific", {})
        if old_type_specific != new_type_specific:
            changes["type_specific"] = {
                "added": {k: v for k, v in new_type_specific.items() 
                         if k not in old_type_specific or old_type_specific[k] != v},
                "removed": {k: v for k, v in old_type_specific.items() 
                           if k not in new_type_specific or new_type_specific[k] != v}
            }
        
        return changes
```

**字段映射配置示例**:

```python
# MySQL 字段映射
MYSQL_FIELD_MAPPING = {
    "global_privileges": {
        "type": "list",
        "model_field": "global_privileges",
        "permission_field": "global_privileges"
    },
    "database_privileges": {
        "type": "dict",
        "model_field": "database_privileges",
        "permission_field": "database_privileges"
    }
}

# PostgreSQL 字段映射
POSTGRESQL_FIELD_MAPPING = {
    "predefined_roles": {
        "type": "list",
        "model_field": "predefined_roles",
        "permission_field": "pred