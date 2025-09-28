# 容量同步功能技术文档

## 1. 功能概述

### 1.1 模块职责
- 提供数据库容量信息的采集、存储、统计和分析功能。
- 支持多种数据库类型（MySQL、SQL Server、PostgreSQL、Oracle）的容量数据采集。
- 实现数据库大小历史记录、实例容量统计、趋势分析等功能。
- 提供手动采集、自动采集、分区管理等运维功能。

### 1.2 代码定位
- 路由：`app/routes/storage_sync.py`
- 服务：`app/services/database_size_collector_service.py`
- 模型：`app/models/database_size_stat.py`、`app/models/instance_size_stat.py`
- 任务：`app/tasks/database_size_collection_tasks.py`、`app/tasks/database_size_aggregation_tasks.py`

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────────────────────┐
│ 路由层 (storage_sync.py)    │
│  - 容量同步页面            │
│  - 采集状态/统计API        │
│  - 实例容量管理API         │
└───────▲───────────┬──────┘
        │调用        │
┌───────┴───────────▼──────┐
│ 采集服务 (collector_service)│
│  - 多数据库类型支持        │
│  - 数据采集与保存          │
│  - 实例统计计算            │
└───────▲───────────┬──────┘
        │依赖        │
┌───────┴───────────▼──────┐
│ 数据层 (models)           │
│  - DatabaseSizeStat       │
│  - InstanceSizeStat       │
│  - Instance               │
└────────────────────────────┘
```

### 2.2 权限控制
- 所有接口使用 `@login_required` 和 `@view_required`（路由 31、59、97、140等）。
- 手动操作需要相应的权限验证。

## 3. 路由实现（`storage_sync.py`）

### 3.1 页面路由
- `GET /`（30-48）：存储同步主页面，获取活跃实例列表用于筛选。

### 3.2 状态与统计接口
- `GET /status`（58-95）：获取采集、聚合、分区管理的状态信息。
- `GET /stats`（97-138）：获取基本统计信息，包括总记录数、实例数、最近采集时间、按数据库类型统计。

### 3.3 连接测试与手动操作
- `POST /test_connection`（140-175）：测试指定实例的数据库连接。
- `POST /manual_collect`（177-201）：手动触发数据采集任务。
- `POST /cleanup_partitions`（204-228）：手动清理分区。

### 3.4 实例管理接口
- `GET /instances`（230-264）：获取活跃实例列表。
- `GET /instances/<id>/database-sizes/total`（266-316）：获取指定实例的数据库总大小。
- `GET /instances/<id>/database-sizes`（319-508）：获取实例的数据库大小历史数据，支持分页、筛选、最新记录查询。
- `GET /instances/<id>/database-sizes/summary`（513-609）：获取实例的数据库大小汇总信息。

### 3.5 容量同步接口
- `POST /instances/<id>/sync-capacity`（647-762）：同步指定实例的容量信息，包括数据库列表和大小信息。
- `GET /instances/<id>/databases`（765-816）：获取指定实例的数据库列表。

## 4. 采集服务实现（`database_size_collector_service.py`）

### 4.1 核心类：`DatabaseSizeCollectorService`
- 初始化：接收 `Instance` 对象，支持上下文管理器（23-42）。
- 连接管理：`connect()`（43-72）和 `disconnect()`（74-80）方法。

### 4.2 多数据库类型支持
- `_collect_mysql_sizes()`（108-173）：
  - 使用 `information_schema.SCHEMATA` 和 `information_schema.tables` 查询。
  - 计算总大小、数据大小、索引大小。
  - 区分系统数据库和用户数据库。
- `_collect_sqlserver_sizes()`（175-214）：
  - 使用 `sys.master_files` 查询数据文件大小。
  - 只采集数据文件，不采集日志文件。
- `_collect_postgresql_sizes()`（216-251）：
  - 使用 `pg_database_size()` 函数查询数据库大小。
  - 过滤模板数据库。
- `_collect_oracle_sizes()`（253-288）：
  - 使用 `dba_data_files` 查询表空间大小。

### 4.3 数据保存方法
- `save_collected_data()`（290-349）：
  - 检查是否存在相同日期的记录，存在则更新，否则创建新记录。
  - 支持事务提交和回滚。
- `save_instance_size_stat()`（351-402）：
  - 计算实例总大小和数据库数量。
  - 保存或更新实例大小统计记录。

### 4.4 综合采集方法
- `collect_and_save()`（404-428）：采集数据并保存，同时更新实例统计。
- `update_instance_total_size()`（430-468）：根据已保存数据更新实例统计。

### 4.5 批量采集函数
- `collect_all_instances_database_sizes()`（471-523）：采集所有活跃实例的容量数据。

## 5. 数据模型

### 5.1 DatabaseSizeStat
- 字段：`instance_id`、`database_name`、`size_mb`、`data_size_mb`、`log_size_mb`、`collected_date`、`collected_at`、`is_deleted`。
- 用途：存储每个数据库的大小历史记录。

### 5.2 InstanceSizeStat
- 字段：`instance_id`、`total_size_mb`、`database_count`、`collected_date`、`collected_at`、`is_deleted`。
- 用途：存储实例级别的容量统计信息。

## 6. 查询优化

### 6.1 最新记录查询
- 使用窗口函数 `ROW_NUMBER() OVER (PARTITION BY database_name ORDER BY collected_date DESC)`（353-364）。
- 原生SQL查询避免SQLAlchemy窗口函数语法问题。

### 6.2 分页与筛选
- 支持按日期范围、数据库名称筛选。
- 支持 `latest_only` 参数获取最新记录。
- 实现分页查询，默认限制100条记录。

### 6.3 统计计算
- 汇总信息计算：总数据库数、总大小、平均大小、最大数据库、增长率（556-597）。
- 按数据库类型分组统计（113-125）。

## 7. 错误处理与日志

### 7.1 异常处理
- 所有数据库操作都有 try-catch 包装。
- 连接失败、权限不足、数据格式错误等都有相应处理。
- 返回详细的错误信息和状态码。

### 7.2 日志记录
- 使用结构化日志记录采集过程。
- 包含实例名称、数据库类型、采集数量等关键信息。
- 区分 info、warning、error 等不同级别。

## 8. 性能优化

### 8.1 连接管理
- 支持连接复用，避免重复连接。
- 使用上下文管理器确保连接正确关闭。
- 连接失败时及时清理资源。

### 8.2 数据采集
- 按数据库类型使用最优查询语句。
- 批量保存数据，减少数据库操作次数。
- 支持增量更新，避免重复数据。

## 9. 测试建议

### 9.1 功能测试
- 各数据库类型的容量采集准确性。
- 数据保存和更新的正确性。
- 统计计算的准确性。

### 9.2 性能测试
- 大量数据库的采集性能。
- 历史数据查询的响应时间。
- 并发采集的稳定性。

## 10. 后续优化方向

### 10.1 功能增强
- 添加容量趋势预测功能。
- 实现容量告警机制。
- 支持容量数据的导出和报表。

### 10.2 性能优化
- 实现增量采集机制。
- 添加数据压缩和归档功能。
- 优化大量历史数据的查询性能。

### 10.3 监控告警
- 集成容量监控系统。
- 添加容量异常告警。
- 提供容量使用率分析。
