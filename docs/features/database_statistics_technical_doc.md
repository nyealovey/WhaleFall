# 数据库统计功能技术文档

## 1. 功能概述

### 1.1 模块职责
- 提供数据库容量统计和分析功能，包括容量趋势、增长分析、性能指标等。
- 实现数据库大小数据的采集、存储、聚合和可视化展示。
- 支持多种数据库类型（MySQL、SQL Server、PostgreSQL、Oracle）的容量监控。
- 提供统计聚合、分区管理、趋势分析等高级功能。

### 1.2 代码定位
- 路由：`app/routes/storage_sync.py`（容量同步相关接口）
- 服务：`app/services/database_size_collector_service.py`、`app/services/database_size_aggregation_service.py`
- 模型：`app/models/database_size_stat.py`、`app/models/instance_size_stat.py`
- 任务：`app/tasks/database_size_collection_tasks.py`、`app/tasks/database_size_aggregation_tasks.py`

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────────────────────┐
│ 前端统计界面                 │
│  - 容量趋势图表            │
│  - 统计概览卡片            │
│  - 筛选和搜索功能          │
└───────▲───────────┬──────┘
        │AJAX        │
┌───────┴───────────▼──────┐
│ Flask 路由 (storage_sync) │
│  - /instances/<id>/database-sizes │
│  - /instances/<id>/database-sizes/summary │
│  - /instances/<id>/sync-capacity │
└───────▲───────────┬──────┘
        │SQLAlchemy │服务调用
┌───────┴───────────▼──────┐
│ 数据层与服务              │
│  - DatabaseSizeStat       │
│  - InstanceSizeStat       │
│  - DatabaseSizeCollectorService│
└────────────────────────────┘
```

### 2.2 权限控制
- 所有接口使用 `@login_required` 和 `@view_required`。

## 3. 路由实现（`storage_sync.py`）

### 3.1 实例容量管理接口
- `GET /instances/<id>/database-sizes`（319-508）：
  - 获取指定实例的数据库大小历史数据。
  - 支持分页、筛选、最新记录查询。
  - 使用窗口函数获取每个数据库的最新记录（353-364）。
  - 支持按数据库名称、日期范围筛选。

- `GET /instances/<id>/database-sizes/summary`（513-609）：
  - 获取指定实例的数据库大小汇总信息。
  - 计算最近30天的统计指标。
  - 包括总数据库数、总大小、平均大小、最大数据库、增长率等。

- `POST /instances/<id>/sync-capacity`（647-762）：
  - 同步指定实例的容量信息。
  - 包含数据库列表同步和大小信息同步。
  - 使用共享数据库连接优化性能。

### 3.2 实例管理接口
- `GET /instances`（230-264）：获取活跃实例列表。
- `GET /instances/<id>/database-sizes/total`（266-316）：获取指定实例的数据库总大小。

## 4. 数据采集服务（`database_size_collector_service.py`）

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
- 按数据库类型分组统计。

## 7. 定时任务

### 7.1 数据采集任务
- `collect_database_sizes`：采集所有实例的数据库大小数据。
- `collect_specific_instance_database_sizes`：采集指定实例的数据库大小数据。
- `collect_database_sizes_by_type`：按数据库类型采集数据。

### 7.2 数据聚合任务
- `calculate_database_size_aggregations`：计算数据库大小聚合统计。
- 支持日、周、月、季度等不同周期的聚合。

## 8. 前端实现

### 8.1 容量趋势图表
- 使用Chart.js绘制数据库容量趋势图。
- 支持按数据库和按实例两种聚合模式。
- 支持折线图和柱状图两种显示方式。

### 8.2 统计概览卡片
- 显示总实例数、总数据库数、平均大小、最大大小等统计信息。
- 支持实时数据更新和刷新。

### 8.3 筛选和搜索功能
- 支持按实例、数据库类型、时间范围等筛选。
- 支持实时搜索数据库名称。
- 支持联动筛选和动态更新。

## 9. 性能优化

### 9.1 查询优化
- 使用索引优化统计查询性能。
- 避免N+1查询问题。
- 使用聚合查询减少数据传输。

### 9.2 数据采集优化
- 支持连接复用，避免重复连接。
- 使用上下文管理器确保连接正确关闭。
- 批量保存数据，减少数据库操作次数。

### 9.3 前端优化
- 图表数据按需加载。
- 支持防抖技术优化用户操作。
- 使用缓存减少重复请求。

## 10. 错误处理

### 10.1 后端错误处理
- 所有数据库操作都有异常处理。
- 连接失败、权限不足、数据格式错误等都有相应处理。
- 返回详细的错误信息和状态码。

### 10.2 前端错误处理
- AJAX请求失败时显示错误提示。
- 图表渲染失败时显示备用内容。

## 11. 测试建议

### 11.1 功能测试
- 各数据库类型的容量采集准确性。
- 数据保存和更新的正确性。
- 统计计算的准确性。

### 11.2 性能测试
- 大量数据库的采集性能。
- 历史数据查询的响应时间。
- 并发采集的稳定性。

## 12. 后续优化方向

### 12.1 功能增强
- 添加容量趋势预测功能。
- 实现容量告警机制。
- 支持容量数据的导出和报表。

### 12.2 性能优化
- 实现增量采集机制。
- 添加数据压缩和归档功能。
- 优化大量历史数据的查询性能。

### 12.3 监控告警
- 集成容量监控系统。
- 添加容量异常告警。
- 提供容量使用率分析。
