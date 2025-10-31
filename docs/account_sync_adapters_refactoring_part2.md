# 账户同步适配器重构文档（续）

## 3.2 重构策略（续）

### 字段映射配置完整示例

```python
# app/services/account_sync_adapters/field_mappings.py

# MySQL 字段映射
MYSQL_FIELD_MAPPING = {
    "global_privileges": {
        "type": "list",
        "model_field": "global_privileges",
        "permission_field": "global_privileges",
        "display_name": "全局权限"
    },
    "database_privileges": {
        "type": "dict",
        "model_field": "database_privileges",
        "permission_field": "database_privileges",
        "display_name": "数据库权限"
    }
}

# PostgreSQL 字段映射
POSTGRESQL_FIELD_MAPPING = {
    "predefined_roles": {
        "type": "list",
        "model_field": "predefined_roles",
        "permission_field": "predefined_roles",
        "display_name": "预定义角色"
    },
    "role_attributes": {
        "type": "dict",
        "model_field": "role_attributes",
        "permission_field": "role_attributes",
        "display_name": "角色属性"
    },
    "database_privileges_pg": {
        "type": "dict",
        "model_field": "database_privileges_pg",
        "permission_field": "database_privileges",
        "display_name": "数据库权限"
    },
    "tablespace_privileges": {
        "type": "dict",
        "model_field": "tablespace_privileges",
        "permission_field": "tablespace_privileges",
        "display_name": "表空间权限"
    },
    "system_privileges": {
        "type": "list",
        "model_field": "system_privileges",
        "permission_field": "system_privileges",
        "display_name": "系统权限"
    }
}

# Oracle 字段映射
ORACLE_FIELD_MAPPING = {
    "oracle_roles": {
        "type": "list",
        "model_field": "oracle_roles",
        "permission_field": "roles",
        "display_name": "Oracle角色"
    },
    "system_privileges": {
        "type": "list",
        "model_field": "system_privileges",
        "permission_field": "system_privileges",
        "display_name": "系统权限"
    },
    "tablespace_privileges_oracle": {
        "type": "dict",
        "model_field": "tablespace_privileges_oracle",
        "permission_field": "tablespace_privileges",
        "display_name": "表空间权限"
    }
}

# SQL Server 字段映射
SQLSERVER_FIELD_MAPPING = {
    "server_roles": {
        "type": "list",
        "model_field": "server_roles",
        "permission_field": "server_roles",
        "display_name": "服务器角色"
    },
    "server_permissions": {
        "type": "list",
        "model_field": "server_permissions",
        "permission_field": "server_permissions",
        "display_name": "服务器权限"
    },
    "database_roles": {
        "type": "dict",
        "model_field": "database_roles",
        "permission_field": "database_roles",
        "display_name": "数据库角色"
    },
    "database_permissions": {
        "type": "dict",
        "model_field": "database_permissions",
        "permission_field": "database_permissions",
        "display_name": "数据库权限"
    }
}

# 统一映射字典
FIELD_MAPPINGS = {
    "mysql": MYSQL_FIELD_MAPPING,
    "postgresql": POSTGRESQL_FIELD_MAPPING,
    "oracle": ORACLE_FIELD_MAPPING,
    "sqlserver": SQLSERVER_FIELD_MAPPING
}
```

#### 策略 2: 提取通用变更描述生成器

```python
# app/services/account_sync_adapters/change_description_generator.py

class ChangeDescriptionGenerator:
    """通用变更描述生成器"""
    
    @staticmethod
    def generate_descriptions(db_type: str, changes: dict, field_mapping: dict) -> list[str]:
        """
        生成变更描述
        
        Args:
            db_type: 数据库类型
            changes: 变更数据
            field_mapping: 字段映射配置
            
        Returns:
            变更描述列表
        """
        descriptions = []
        
        # 1. 超级用户状态变更
        if "is_superuser" in changes:
            new_value = changes["is_superuser"]["new"]
            descriptions.append("提升为超级用户" if new_value else "取消超级用户权限")
        
        # 2. is_active 状态变更
        if "is_active" in changes:
            new_value = changes["is_active"]["new"]
            descriptions.append("账户状态变更为活跃" if new_value else "账户状态变更为锁定")
        
        # 3. 根据字段映射生成权限变更描述
        for field_name, field_config in field_mapping.items():
            if field_name in changes:
                display_name = field_config.get("display_name", field_name)
                field_type = field_config.get("type", "list")
                
                if field_type == "list":
                    descriptions.extend(
                        ChangeDescriptionGenerator._generate_list_descriptions(
                            display_name, changes[field_name]
                        )
                    )
                elif field_type == "dict":
                    descriptions.extend(
                        ChangeDescriptionGenerator._generate_dict_descriptions(
                            display_name, changes[field_name]
                        )
                    )
        
        # 4. type_specific 变更
        if "type_specific" in changes:
            added = changes["type_specific"]["added"]
            removed = changes["type_specific"]["removed"]
            if added:
                descriptions.append(f"更新类型特定信息: {', '.join(added.keys())}")
            if removed:
                descriptions.append(f"移除类型特定信息: {', '.join(removed.keys())}")
        
        return descriptions
    
    @staticmethod
    def _generate_list_descriptions(display_name: str, change_data: dict) -> list[str]:
        """生成列表类型字段的变更描述"""
        descriptions = []
        added = change_data.get("added", [])
        removed = change_data.get("removed", [])
        
        if added:
            descriptions.append(f"新增{display_name}: {', '.join(added)}")
        if removed:
            descriptions.append(f"移除{display_name}: {', '.join(removed)}")
        
        return descriptions
    
    @staticmethod
    def _generate_dict_descriptions(display_name: str, change_data: dict) -> list[str]:
        """生成字典类型字段的变更描述"""
        descriptions = []
        added = change_data.get("added", {})
        removed = change_data.get("removed", {})
        
        if added:
            for key, values in added.items():
                descriptions.append(f"{key} 新增{display_name}: {', '.join(values)}")
        if removed:
            for key, values in removed.items():
                descriptions.append(f"{key} 移除{display_name}: {', '.join(values)}")
        
        return descriptions
```

#### 策略 3: 提取通用过滤条件构建器

```python
# 在 BaseSyncAdapter 中添加通用方法

class BaseSyncAdapter(ABC):
    """数据库同步适配器基类"""
    
    def __init__(self) -> None:
        self.sync_logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()
    
    def _build_filter_conditions(self, db_type: str, field_name: str) -> tuple[str, list]:
        """
        构建过滤条件 - 通用实现
        
        Args:
            db_type: 数据库类型
            field_name: 字段名称
            
        Returns:
            (where_clause, params)
        """
        filter_rules = self.filter_manager.get_filter_rules(db_type)
        builder = SafeQueryBuilder(db_type=db_type)
        
        exclude_users = filter_rules.get("exclude_users", [])
        exclude_patterns = filter_rules.get("exclude_patterns", [])
        
        builder.add_database_specific_condition(field_name, exclude_users, exclude_patterns)
        
        return builder.build_where_clause()
    
    # 子类只需调用：
    # return self._build_filter_conditions(self.db_type, "username")
```

#### 策略 4: 提取通用账户更新器

```python
# app/services/account_sync_adapters/account_updater.py

class AccountUpdater:
    """通用账户更新器"""
    
    @staticmethod
    def update_permissions(
        account: CurrentAccountSyncData,
        permissions_data: dict,
        field_mapping: dict,
        *,
        is_superuser: bool
    ) -> None:
        """
        更新账户权限 - 通用实现
        
        Args:
            account: 账户对象
            permissions_data: 权限数据
            field_mapping: 字段映射配置
            is_superuser: 是否超级用户
        """
        # 更新基础字段
        account.is_superuser = is_superuser
        account.is_active = permissions_data.get("type_specific", {}).get("is_active", False)
        account.type_specific = permissions_data.get("type_specific", {})
        
        # 根据字段映射更新权限字段
        for field_name, field_config in field_mapping.items():
            model_field = field_config["model_field"]
            permission_field = field_config["permission_field"]
            
            setattr(account, model_field, permissions_data.get(permission_field, [] if field_config["type"] == "list" else {}))
        
        # 更新变更信息
        account.is_deleted = False
        account.deleted_time = None
        account.last_change_type = "modify_privilege"
        account.last_change_time = time_utils.now()
        account.last_sync_time = time_utils.now()
    
    @staticmethod
    def create_new_account(
        instance_id: int,
        db_type: str,
        username: str,
        permissions_data: dict,
        field_mapping: dict,
        *,
        is_superuser: bool,
        session_id: str
    ) -> CurrentAccountSyncData:
        """
        创建新账户 - 通用实现
        """
        # 构建账户数据
        account_data = {
            "instance_id": instance_id,
            "db_type": db_type,
            "username": username,
            "is_superuser": is_superuser,
            "is_active": permissions_data.get("type_specific", {}).get("is_active", False),
            "type_specific": permissions_data.get("type_specific", {}),
            "last_change_type": "add",
            "session_id": session_id
        }
        
        # 根据字段映射添加权限字段
        for field_name, field_config in field_mapping.items():
            model_field = field_config["model_field"]
            permission_field = field_config["permission_field"]
            default_value = [] if field_config["type"] == "list" else {}
            
            account_data[model_field] = permissions_data.get(permission_field, default_value)
        
        return CurrentAccountSyncData(**account_data)
```

### 3.3 重构后的适配器示例

```python
# app/services/account_sync_adapters/mysql_sync_adapter.py (重构后)

from .base_sync_adapter import BaseSyncAdapter
from .permission_comparator import PermissionComparator
from .change_description_generator import ChangeDescriptionGenerator
from .account_updater import AccountUpdater
from .field_mappings import MYSQL_FIELD_MAPPING

class MySQLSyncAdapter(BaseSyncAdapter):
    """MySQL数据库同步适配器 - 重构版"""
    
    def __init__(self) -> None:
        super().__init__()
        self.db_type = "mysql"
        self.field_mapping = MYSQL_FIELD_MAPPING
    
    def get_database_accounts(self, instance, connection):
        """获取MySQL数据库中的所有账户信息 - 数据库特定实现"""
        # 只保留MySQL特定的查询逻辑
        filter_conditions = self._build_filter_conditions(self.db_type, "User")
        where_clause, params = filter_conditions
        
        user_sql = f"""
            SELECT User, Host, Super_priv
            FROM mysql.user
            WHERE User != '' AND {where_clause}
            ORDER BY User, Host
        """
        # ... MySQL特定的查询和数据处理逻辑
    
    def _detect_changes(self, existing_account, new_permissions, *, is_superuser):
        """检测变更 - 使用通用比较器"""
        return PermissionComparator.detect_changes(
            existing_account,
            new_permissions,
            self.field_mapping,
            is_superuser=is_superuser
        )
    
    def _update_account_permissions(self, account, permissions_data, *, is_superuser):
        """更新权限 - 使用通用更新器"""
        AccountUpdater.update_permissions(
            account,
            permissions_data,
            self.field_mapping,
            is_superuser=is_superuser
        )
    
    def _create_new_account(self, instance_id, db_type, username, 
                           permissions_data, is_superuser, session_id):
        """创建账户 - 使用通用创建器"""
        return AccountUpdater.create_new_account(
            instance_id,
            db_type,
            username,
            permissions_data,
            self.field_mapping,
            is_superuser=is_superuser,
            session_id=session_id
        )
    
    def _generate_change_description(self, db_type, changes):
        """生成变更描述 - 使用通用生成器"""
        return ChangeDescriptionGenerator.generate_descriptions(
            db_type,
            changes,
            self.field_mapping
        )
    
    # 其他MySQL特定方法保持不变
    def _get_user_permissions(self, connection, username, host):
        """MySQL特定的权限获取逻辑"""
        # ...
```

## 4. 重构实施计划

### 4.1 阶段划分

#### 阶段 1: 准备阶段（1-2天）

1. **创建新的通用组件**
   - [ ] 创建 `permission_comparator.py`
   - [ ] 创建 `change_description_generator.py`
   - [ ] 创建 `account_updater.py`
   - [ ] 创建 `field_mappings.py`

2. **编写单元测试**
   - [ ] 为 `PermissionComparator` 编写测试
   - [ ] 为 `ChangeDescriptionGenerator` 编写测试
   - [ ] 为 `AccountUpdater` 编写测试

#### 阶段 2: 重构适配器（3-4天）

1. **逐个重构适配器**
   - [ ] 重构 `MySQLSyncAdapter`
   - [ ] 重构 `PostgreSQLSyncAdapter`
   - [ ] 重构 `OracleSyncAdapter`
   - [ ] 重构 `SQLServerSyncAdapter`

2. **运行集成测试**
   - [ ] 测试每个适配器的同步功能
   - [ ] 验证变更检测的准确性
   - [ ] 确认向后兼容性

#### 阶段 3: 优化和清理（1-2天）

1. **代码优化**
   - [ ] 移除重复代码
   - [ ] 优化性能
   - [ ] 改进错误处理

2. **文档更新**
   - [ ] 更新API文档
   - [ ] 添加使用示例
   - [ ] 更新开发指南

### 4.2 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 破坏现有功能 | 高 | 中 | 完善的单元测试和集成测试 |
| 性能下降 | 中 | 低 | 性能基准测试和优化 |
| 字段映射错误 | 高 | 中 | 详细的映射配置验证 |
| 向后兼容性问题 | 高 | 低 | 保持API接口不变 |

### 4.3 回滚计划

1. **版本控制**: 在独立分支进行重构
2. **功能开关**: 使用配置控制新旧实现切换
3. **数据备份**: 重构前备份关键数据
4. **快速回滚**: 保留旧代码，确保可以快速回滚

## 5. 预期收益

### 5.1 代码质量提升

- **重复代码减少**: 从 800+ 行减少到 < 100 行
- **代码行数减少**: 总代码量减少约 30%
- **圈复杂度降低**: 平均圈复杂度从 15 降到 8

### 5.2 维护成本降低

- **修改点减少**: 通用逻辑修改从 4 处减少到 1 处
- **测试用例减少**: 重复测试用例减少 60%
- **Bug修复时间**: 预计减少 40%

### 5.3 扩展性提升

- **新增数据库类型**: 从需要 500+ 行代码减少到 < 200 行
- **新增功能**: 只需修改通用组件，自动应用到所有适配器
- **配置驱动**: 通过配置文件即可调整行为

## 6. 后续优化建议

### 6.1 进一步抽象

1. **权限模型统一化**
   - 定义统一的权限抽象模型
   - 各数据库权限映射到统一模型
   - 支持跨数据库权限比较

2. **查询构建器增强**
   - 提取批量查询模式
   - 统一查询优化策略
   - 支持查询性能监控

### 6.2 性能优化

1. **缓存机制**
   - 缓存字段映射配置
   - 缓存权限比较结果
   - 实现增量同步

2. **并发处理**
   - 支持多实例并发同步
   - 优化批量操作性能
   - 实现异步权限检测

### 6.3 监控和告警

1. **同步监控**
   - 记录同步耗时
   - 监控变更频率
   - 检测异常模式

2. **质量指标**
   - 代码覆盖率 > 80%
   - 圈复杂度 < 10
   - 重复代码率 < 5%

## 7. 总结

通过本次重构，我们将：

1. **消除 800+ 行重复代码**，提高代码质量
2. **建立配置驱动的架构**，增强可扩展性
3. **统一权限处理逻辑**，降低维护成本
4. **保持向后兼容**，确保平滑过渡

重构后的代码将更加清晰、可维护，为后续功能扩展奠定坚实基础。
