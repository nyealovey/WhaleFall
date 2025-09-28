# 缓存管理功能技术文档

## 1. 功能概述

### 1.1 模块职责
- 提供统一的缓存管理接口，支持多种缓存类型的操作和统计。
- 实现数据库权限缓存、账户权限缓存、规则评估缓存、分类规则缓存等。
- 提供缓存健康检查、统计信息查询、批量清理等功能。
- 支持按数据库类型、用户、实例等维度的缓存管理。

### 1.2 代码定位
- 路由：`app/routes/cache.py`
- 服务：`app/services/cache_manager.py`
- 模型：`app/models/instance.py`
- 适配器：`app/services/sync_adapters/sqlserver_sync_adapter.py`
- 分类服务：`app/services/account_classification_service.py`

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────────────────────┐
│ 路由层 (cache.py)           │
│  - 缓存统计/健康检查        │
│  - 用户/实例缓存清理        │
│  - 分类缓存管理            │
└───────▲───────────┬──────┘
        │调用        │
┌───────┴───────────▼──────┐
│ 缓存管理器 (cache_manager.py)│
│  - 缓存键生成            │
│  - 缓存操作封装          │
│  - 统计信息收集          │
└───────▲───────────┬──────┘
        │依赖        │
┌───────┴───────────▼──────┐
│ 底层缓存 (Flask-Caching)  │
│  - Redis/Memory 后端     │
│  - 缓存存储与检索        │
└────────────────────────────┘
```

### 2.2 权限控制
- 统计和健康检查：`@login_required`（路由 25、35）。
- 缓存清理：`@admin_required`（路由 48、79、109）。
- 分类缓存：`@update_required`（路由 133、153）。

## 3. 缓存管理器实现（`cache_manager.py`）

### 3.1 核心类：`CacheManager`
- 初始化：接收 `Flask-Caching` 实例，设置默认 TTL 为 7 天（21-24）。
- 缓存键生成：`_generate_cache_key()`（25-31）使用 SHA-256 哈希确保键名安全。

### 3.2 数据库权限缓存
- `get_database_permissions_cache()`（33-55）：获取用户数据库权限缓存。
- `set_database_permissions_cache()`（57-82）：设置权限缓存，包含角色和权限列表。
- 缓存键格式：`whalefall:{hash(db_perms:instance_id:username:db_name)}`。

### 3.3 账户权限缓存
- `get_account_permissions_cache()`（119-137）：获取账户权限缓存。
- `set_account_permissions_cache()`（139-159）：设置账户权限缓存。
- 缓存键格式：`whalefall:{hash(account_perms:account_id:)}`。

### 3.4 规则评估缓存
- `get_rule_evaluation_cache()`（161-179）：获取规则评估结果缓存。
- `set_rule_evaluation_cache()`（181-202）：设置规则评估缓存，TTL 1 天。
- 缓存键格式：`whalefall:{hash(rule_eval:rule_id:account_id:)}`。

### 3.5 分类规则缓存
- `get_classification_rules_cache()`（204-222）：获取所有分类规则缓存。
- `set_classification_rules_cache()`（224-244）：设置规则缓存，TTL 2 小时。
- `get_classification_rules_by_db_type_cache()`（315-341）：按数据库类型获取规则缓存。
- `set_classification_rules_by_db_type_cache()`（343-364）：按数据库类型设置规则缓存。

### 3.6 账户缓存
- `get_accounts_by_db_type_cache()`（366-392）：获取按数据库类型分组的账户缓存。
- `set_accounts_by_db_type_cache()`（394-415）：设置账户缓存，TTL 1 小时。

### 3.7 缓存清理方法
- `invalidate_user_cache()`（92-97）：清除用户缓存（简化实现）。
- `invalidate_instance_cache()`（99-104）：清除实例缓存（简化实现）。
- `invalidate_account_cache()`（246-263）：清除账户相关缓存。
- `invalidate_classification_cache()`（265-283）：清除分类相关缓存。
- `invalidate_db_type_cache()`（417-436）：清除特定数据库类型缓存。
- `invalidate_all_db_type_cache()`（438-454）：清除所有数据库类型缓存。

### 3.8 统计与健康检查
- `get_cache_stats()`（106-117）：获取缓存统计信息。
- `health_check()`（456-471）：缓存健康检查，通过测试键验证。

## 4. 路由实现（`cache.py`）

### 4.1 基础缓存接口
- `GET /stats`（24-32）：获取缓存统计信息。
- `GET /health`（35-43）：检查缓存健康状态。

### 4.2 用户缓存清理
- `POST /clear/user`（46-74）：
  - 参数：`instance_id`、`username`。
  - SQL Server 使用 `SQLServerSyncAdapter.clear_user_cache()`（65-66）。
  - 其他数据库类型调用 `cache_manager.invalidate_user_cache()`（69）。

### 4.3 实例缓存清理
- `POST /clear/instance`（77-104）：
  - 参数：`instance_id`。
  - SQL Server 使用 `SQLServerSyncAdapter.clear_instance_cache()`（95-96）。
  - 其他数据库类型调用 `cache_manager.invalidate_instance_cache()`（99）。

### 4.4 全局缓存清理
- `POST /clear/all`（107-126）：
  - 遍历所有活跃实例，仅支持 SQL Server 缓存清理。
  - 统计清理成功的实例数量。

### 4.5 分类缓存管理
- `POST /classification/clear`（131-148）：清除所有分类缓存。
- `POST /classification/clear/<db_type>`（151-173）：清除特定数据库类型缓存。
- `GET /classification/stats`（176-223）：获取分类缓存统计信息。

## 5. 缓存策略

### 5.1 TTL 设置
- 数据库权限：7 天（默认）。
- 规则评估：1 天。
- 分类规则：2 小时。
- 账户缓存：1 小时。

### 5.2 缓存键设计
- 使用 SHA-256 哈希确保键名长度合理且安全。
- 前缀区分缓存类型：`db_perms`、`account_perms`、`rule_eval`、`classification_rules`。
- 包含实例ID、用户名、数据库名等标识信息。

### 5.3 数据格式
- 所有缓存数据包含 `cached_at` 时间戳。
- 分类规则缓存支持新旧格式兼容（327-335、377-386）。
- 使用 JSON 序列化存储复杂数据结构。

## 6. 错误处理与日志

### 6.1 异常处理
- 所有缓存操作都有 try-catch 包装。
- 缓存失败时记录警告日志，不影响主业务流程。
- 返回 None 或 False 表示缓存操作失败。

### 6.2 日志记录
- 使用结构化日志记录缓存操作。
- 包含缓存键、TTL、数据量等关键信息。
- 区分 debug、warning、info 等不同级别。

## 7. 性能优化

### 7.1 缓存命中优化
- 合理的 TTL 设置平衡数据新鲜度和性能。
- 按数据库类型分组缓存，减少缓存键冲突。
- 使用哈希键名避免键名过长问题。

### 7.2 清理策略
- 提供多种清理粒度：用户、实例、数据库类型、全局。
- 支持按需清理和批量清理。
- 简化实现避免复杂的模式匹配。

## 8. 限制与约束

### 8.1 Flask-Caching 限制
- 不支持模式匹配的键查找。
- 部分清理方法使用简化实现。
- 依赖底层缓存后端的特性。

### 8.2 数据库适配器
- 仅 SQL Server 支持完整的缓存清理。
- 其他数据库类型使用通用清理方法。
- 需要适配器支持才能实现完整功能。

## 9. 测试建议

### 9.1 功能测试
- 缓存设置和获取的准确性。
- 不同 TTL 的过期行为。
- 缓存清理的完整性。

### 9.2 性能测试
- 大量缓存的读写性能。
- 缓存命中率统计。
- 并发访问的稳定性。

## 10. 后续优化方向

### 10.1 功能增强
- 实现缓存预热机制。
- 添加缓存使用率监控。
- 支持缓存数据的压缩存储。

### 10.2 性能优化
- 使用 Redis 集群提升缓存容量。
- 实现缓存数据的增量更新。
- 添加缓存数据的持久化备份。

### 10.3 监控告警
- 集成缓存监控系统。
- 添加缓存异常告警。
- 提供缓存性能分析报告。
