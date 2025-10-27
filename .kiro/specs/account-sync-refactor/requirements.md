# Requirements Document

## Introduction

本项目的账户同步功能存在大量重复代码，需要进行重构以提高代码可维护性和可扩展性。当前有一个基类 `BaseSyncAdapter` 和四个数据库特定的适配器（MySQL、Oracle、PostgreSQL、SQL Server），它们之间存在以下问题：

1. **权限检测逻辑重复**：每个适配器都实现了相似的 `_detect_changes` 方法
2. **权限更新逻辑重复**：每个适配器都实现了相似的 `_update_account_permissions` 方法
3. **账户创建逻辑重复**：每个适配器都实现了相似的 `_create_new_account` 方法
4. **变更描述生成重复**：每个适配器都实现了相似的 `_generate_change_description` 方法
5. **过滤条件构建重复**：每个适配器都有相似的 `_build_filter_conditions` 方法
6. **缺乏统一的权限字段映射**：不同数据库的权限字段映射逻辑分散在各个适配器中

## Glossary

- **BaseSyncAdapter**: 账户同步适配器的抽象基类，定义了同步流程和通用接口
- **Adapter**: 数据库特定的同步适配器，继承自 BaseSyncAdapter
- **CurrentAccountSyncData**: 存储当前账户同步数据的数据模型
- **Permission Field**: 权限字段，如 global_privileges、database_privileges 等
- **Type-Specific Field**: 数据库特定字段，存储在 type_specific JSON 字段中
- **Change Detection**: 变更检测，比较新旧权限数据以识别变化
- **Permission Mapping**: 权限映射，将数据库特定的权限数据映射到统一的数据模型字段

## Requirements

### Requirement 1: 统一权限字段映射配置

**User Story:** 作为开发者，我希望有一个统一的权限字段映射配置，这样我可以轻松地为不同数据库定义权限字段映射关系，而不需要在每个适配器中重复编写映射逻辑。

#### Acceptance Criteria

1. THE System SHALL provide a centralized permission field mapping configuration for each database type
2. WHEN a new database type is added, THE System SHALL allow developers to define permission field mappings through configuration
3. THE System SHALL support mapping between database-specific permission data and CurrentAccountSyncData model fields
4. THE System SHALL validate that all required permission fields are mapped for each database type

### Requirement 2: 提取通用变更检测逻辑

**User Story:** 作为开发者，我希望变更检测逻辑被提取到基类中，这样我不需要在每个适配器中重复实现相同的比较逻辑。

#### Acceptance Criteria

1. THE BaseSyncAdapter SHALL implement a generic change detection method that works for all database types
2. WHEN comparing old and new permissions, THE System SHALL use the permission field mapping configuration to identify which fields to compare
3. THE System SHALL detect changes in superuser status, active status, and all permission-related fields
4. THE System SHALL return a structured change dictionary with added and removed items for list/set fields
5. THE System SHALL handle nested dictionary comparisons for database-level and object-level permissions

### Requirement 3: 提取通用权限更新逻辑

**User Story:** 作为开发者，我希望权限更新逻辑被提取到基类中，这样我不需要在每个适配器中重复实现相同的更新逻辑。

#### Acceptance Criteria

1. THE BaseSyncAdapter SHALL implement a generic permission update method that works for all database types
2. WHEN updating account permissions, THE System SHALL use the permission field mapping configuration to update the correct model fields
3. THE System SHALL update is_superuser, is_active, and all permission-related fields based on the mapping
4. THE System SHALL set last_change_type, last_change_time, and last_sync_time automatically
5. THE System SHALL clear account cache after updating permissions

### Requirement 4: 提取通用账户创建逻辑

**User Story:** 作为开发者，我希望账户创建逻辑被提取到基类中，这样我不需要在每个适配器中重复实现相同的创建逻辑。

#### Acceptance Criteria

1. THE BaseSyncAdapter SHALL implement a generic account creation method that works for all database types
2. WHEN creating a new account, THE System SHALL use the permission field mapping configuration to populate the correct model fields
3. THE System SHALL set instance_id, db_type, username, is_superuser, is_active, and session_id
4. THE System SHALL populate all permission-related fields based on the mapping configuration
5. THE System SHALL set last_change_type to "add" for new accounts

### Requirement 5: 提取通用变更描述生成逻辑

**User Story:** 作为开发者，我希望变更描述生成逻辑被提取到基类中，这样我不需要在每个适配器中重复实现相同的描述生成逻辑。

#### Acceptance Criteria

1. THE BaseSyncAdapter SHALL implement a generic change description generation method
2. WHEN generating change descriptions, THE System SHALL use the permission field mapping configuration to identify field names
3. THE System SHALL generate human-readable descriptions for superuser status changes
4. THE System SHALL generate descriptions for permission additions and removals
5. THE System SHALL handle nested permission structures (e.g., database-level permissions)

### Requirement 6: 简化过滤条件构建

**User Story:** 作为开发者，我希望过滤条件构建逻辑更加简洁，这样我不需要在每个适配器中重复相似的代码。

#### Acceptance Criteria

1. THE BaseSyncAdapter SHALL provide a helper method for building filter conditions
2. WHEN building filter conditions, THE System SHALL use SafeQueryBuilder with database-specific settings
3. THE System SHALL accept database type, field name, exclude users, and exclude patterns as parameters
4. THE System SHALL return a tuple of (where_clause, params) ready for use in SQL queries

### Requirement 7: 清理未使用的代码

**User Story:** 作为开发者，我希望删除所有未使用的代码，这样代码库更加清晰，减少维护负担和潜在的混淆。

#### Acceptance Criteria

1. THE System SHALL remove all non-batch methods from BaseSyncAdapter that are no longer called
2. THE System SHALL remove deprecated parsing methods from MySQLSyncAdapter
3. THE System SHALL remove single-user query methods from OracleSyncAdapter that have been replaced by batch methods
4. THE System SHALL remove unused permission query methods from SQLServerSyncAdapter
5. WHEN removing dead code, THE System SHALL ensure no functionality is lost

### Requirement 8: 保持向后兼容性

**User Story:** 作为系统管理员，我希望重构后的代码保持向后兼容，这样现有的同步功能不会受到影响。

#### Acceptance Criteria

1. THE System SHALL maintain the same public API for all adapter classes
2. WHEN refactoring is complete, THE System SHALL produce the same sync results as before
3. THE System SHALL not break existing database connections or queries
4. THE System SHALL maintain the same logging behavior
5. THE System SHALL not introduce performance regressions
