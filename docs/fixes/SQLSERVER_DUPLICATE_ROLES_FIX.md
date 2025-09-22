# SQL Server 重复角色权限修复

## 🔍 问题描述

SQL Server 账户同步时出现重复的角色和权限显示问题，例如：
- **CRM 数据库**: `db_datareader`, `db_datareader`, `db_owner` (重复的 `db_datareader`)
- **CreditManage 数据库**: `db_datareader`, `db_owner` (正常)
- **ECDATA 数据库**: `db_backupoperator`, `db_datareader`, `db_datawriter`, `db_owner`, `db_owner` (重复的 `db_owner`)

## 🔍 根本原因分析

### 1. **角色处理逻辑缺陷**

#### 问题代码：
```python
# 处理角色时没有去重检查
if user_name == username or (login_sid and ...):
    if db_name not in database_roles:
        database_roles[db_name] = []
    database_roles[db_name].append(role_name)  # 直接添加，可能重复
```

#### 问题原因：
- **SQL 查询结果重复**: 同一个用户可能在多个角色成员关系表中出现
- **SID 匹配重复**: 通过用户名和 SID 两种方式都可能匹配到同一个角色
- **缺少去重逻辑**: 没有检查角色是否已经存在就直接添加

### 2. **权限处理逻辑缺陷**

#### 问题代码：
```python
# 处理权限时没有去重检查
if scope == "DATABASE":
    database_permissions[db_name]["database"].append(permission_name)  # 直接添加，可能重复
```

#### 问题原因：
- **权限查询重复**: 同一个权限可能通过不同的查询路径获取
- **缺少去重逻辑**: 没有检查权限是否已经存在就直接添加

## 🔧 修复方案

### 1. **角色去重修复**

#### 修复前：
```python
if user_name == username or (login_sid and ...):
    if db_name not in database_roles:
        database_roles[db_name] = []
    database_roles[db_name].append(role_name)  # 可能重复
```

#### 修复后：
```python
if user_name == username or (login_sid and ...):
    if db_name not in database_roles:
        database_roles[db_name] = []
    # 避免重复添加相同的角色
    if role_name not in database_roles[db_name]:
        database_roles[db_name].append(role_name)
```

### 2. **权限去重修复**

#### 修复前：
```python
if scope == "DATABASE":
    database_permissions[db_name]["database"].append(permission_name)  # 可能重复
```

#### 修复后：
```python
if scope == "DATABASE":
    if permission_name not in database_permissions[db_name]["database"]:
        database_permissions[db_name]["database"].append(permission_name)
```

### 3. **批量处理修复**

#### 角色处理：
```python
# 用户名匹配
if user_name in usernames:
    if db_name not in result[user_name]["roles"]:
        result[user_name]["roles"][db_name] = []
    # 避免重复添加相同的角色
    if role_name not in result[user_name]["roles"][db_name]:
        result[user_name]["roles"][db_name].append(role_name)

# SID匹配
for username, sid in username_to_sid.items():
    if sid and any(...):
        if db_name not in result[username]["roles"]:
            result[username]["roles"][db_name] = []
        # 避免重复添加相同的角色
        if role_name not in result[username]["roles"][db_name]:
            result[username]["roles"][db_name].append(role_name)
```

#### 权限处理：
```python
# 数据库级别权限
if scope == "DATABASE":
    if permission_name not in result[user_name]["permissions"][db_name]["database"]:
        result[user_name]["permissions"][db_name]["database"].append(permission_name)

# 架构级别权限
elif scope == "SCHEMA":
    schema_name = object_name
    if schema_name not in result[user_name]["permissions"][db_name]["schema"]:
        result[user_name]["permissions"][db_name]["schema"][schema_name] = []
    if permission_name not in result[user_name]["permissions"][db_name]["schema"][schema_name]:
        result[user_name]["permissions"][db_name]["schema"][schema_name].append(permission_name)

# 表级别权限
elif scope == "OBJECT":
    table_name = object_name
    if table_name not in result[user_name]["permissions"][db_name]["table"]:
        result[user_name]["permissions"][db_name]["table"][table_name] = []
    if permission_name not in result[user_name]["permissions"][db_name]["table"][table_name]:
        result[user_name]["permissions"][db_name]["table"][table_name].append(permission_name)
```

## 📊 修复效果

### 修复前：
```
CRM 数据库角色: db_datareader, db_datareader, db_owner
CreditManage 数据库角色: db_datareader, db_owner
ECDATA 数据库角色: db_backupoperator, db_datareader, db_datawriter, db_owner, db_owner
```

### 修复后：
```
CRM 数据库角色: db_datareader, db_owner
CreditManage 数据库角色: db_datareader, db_owner
ECDATA 数据库角色: db_backupoperator, db_datareader, db_datawriter, db_owner
```

## 🔍 技术细节

### 1. **去重策略**

#### 角色去重：
- 使用 `if role_name not in database_roles[db_name]` 检查
- 在添加前验证角色是否已存在
- 适用于所有角色类型（数据库角色、服务器角色）

#### 权限去重：
- 使用 `if permission_name not in permissions_list` 检查
- 按权限作用范围分别去重
- 适用于所有权限类型（数据库、架构、表级别）

### 2. **性能影响**

#### 时间复杂度：
- **去重检查**: O(n) 线性搜索
- **总体影响**: 轻微增加，但避免重复数据
- **内存优化**: 减少重复数据存储

#### 空间复杂度：
- **存储优化**: 避免重复角色和权限存储
- **内存节省**: 减少不必要的数据冗余

### 3. **兼容性**

#### 向后兼容：
- 不影响现有数据结构
- 保持 API 接口不变
- 只影响数据去重逻辑

#### 数据一致性：
- 确保角色和权限的唯一性
- 保持排序和分类逻辑
- 维护权限作用范围分类

## 🚀 实施步骤

### 1. **代码修改**
- ✅ 修复单个用户权限获取方法
- ✅ 修复批量用户权限获取方法
- ✅ 添加角色去重逻辑
- ✅ 添加权限去重逻辑

### 2. **测试验证**
- 测试重复角色场景
- 验证权限去重效果
- 检查性能影响
- 确认数据一致性

### 3. **部署更新**
- 更新生产环境代码
- 监控权限同步效果
- 验证用户界面显示
- 确认问题解决

## 📝 总结

### 问题根源：
SQL Server 权限同步逻辑中缺少去重检查，导致相同的角色和权限被重复添加。

### 修复方案：
在所有角色和权限添加操作前添加存在性检查，确保不会重复添加相同的项目。

### 预期效果：
- 消除重复的角色和权限显示
- 提高数据准确性和一致性
- 改善用户体验和界面显示
- 保持系统性能和稳定性

### 注意事项：
- 去重检查会增加轻微的性能开销
- 需要确保所有相关方法都应用了去重逻辑
- 建议在测试环境中充分验证修复效果
