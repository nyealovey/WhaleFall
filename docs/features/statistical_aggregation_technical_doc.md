# 统计聚合功能技术文档

## 1. 功能概述

### 1.1 模块职责
- 提供数据库大小数据的多维度统计聚合分析功能。
- 支持日、周、月、季度等多种时间周期的聚合计算。
- 提供数据库级别和实例级别的聚合统计。
- 集成到同步会话管理系统，支持任务监控和进度跟踪。
- 提供趋势分析、容量监控和增长预测功能。

### 1.2 代码定位
- **聚合路由**：`app/routes/aggregations.py`
- **聚合服务**：`app/services/database_size_aggregation_service.py`
- **聚合任务**：`app/tasks/database_size_aggregation_tasks.py`
- **数据模型**：`app/models/database_size_aggregation.py`、`app/models/instance_size_aggregation.py`
- **前端页面**：`app/templates/database_sizes/database_aggregations.html`、`app/templates/database_sizes/instance_aggregations.html`
- **前端脚本**：`app/static/js/pages/database_sizes/database_aggregations.js`、`app/static/js/pages/database_sizes/instance_aggregations.js`
- **样式文件**：`app/static/css/pages/database_sizes/database_aggregations.css`、`app/static/css/pages/database_sizes/instance_aggregations.css`

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────────────────────────┐
│ 前端聚合页面                    │
│  - 数据库统计                   │
│  - 实例统计                     │
│  - 图表展示                     │
│  - 趋势分析                     │
└───────▲───────────┬─────────────┘
        │AJAX        │
┌───────┴───────────▼─────────────┐
│ Flask 路由 (aggregations)       │
│  - /aggregations/               │
│  - /aggregations/database       │
│  - /aggregations/instance       │
│  - /aggregations/summary        │
└───────▲───────────┬─────────────┘
        │服务调用    │
┌───────┴───────────▼─────────────┐
│ 统计聚合服务                    │
│  - DatabaseSizeAggregationService│
│  - 多周期聚合计算               │
│  - 趋势分析                     │
│  - 增长预测                     │
└───────▲───────────┬─────────────┘
        │数据访问    │
┌───────┴───────────▼─────────────┐
│ 聚合数据模型                    │
│  - DatabaseSizeAggregation      │
│  - InstanceSizeAggregation      │
│  - DatabaseSizeStat (原始数据)  │
└─────────────────────────────────┘
```

### 2.2 权限控制
- 所有聚合接口使用 `@login_required` 和 `@view_required` 装饰器。

## 3. 路由实现（`aggregations.py`）

### 3.1 聚合统计主页面
- `GET /aggregations/`（33-225）：
  - 支持两种模式：页面请求（返回HTML）和API请求（返回JSON）。
  - 根据 `table_type` 参数选择查询表：instance（实例聚合表）、database（数据库聚合表）。
  - 支持多维度筛选：实例ID、数据库类型、数据库名称、周期类型、时间范围。
  - 支持分页查询和图表数据（get_all=true时返回TOP 20数据）。
  - 返回HTML页面时提供实例列表、数据库类型、数据库列表等筛选选项。

### 3.2 聚合汇总统计
- `GET /aggregations/summary`（231-316）：
  - 统计总聚合记录数、总实例数、总数据库数。
  - 计算平均大小、最大大小等统计指标。
  - 按周期类型、实例、数据库维度统计记录数量。
  - 返回最近更新时间和TOP 10统计。

### 3.3 实例聚合页面
- `GET /aggregations/instance`（322-427）：
  - 查询 `InstanceSizeAggregation` 表，提供实例级别的聚合统计。
  - 支持按实例ID、数据库类型、周期类型、时间范围筛选。
  - 图表模式返回按总大小排序的TOP 20数据。
  - 表格模式支持分页查询，按时间排序。

### 3.4 数据库聚合页面
- `GET /aggregations/database`（433-546）：
  - 查询 `DatabaseSizeAggregation` 表，提供数据库级别的聚合统计。
  - 支持按实例ID、数据库类型、数据库名称、周期类型、时间范围筛选。
  - 图表模式返回按平均大小排序的TOP 20数据。
  - 包含实例信息和数据库名称，支持详细分析。

### 3.5 手动聚合计算
- `POST /aggregations/manual_aggregate`（697-719）：
  - 手动触发聚合计算任务，调用 `calculate_database_size_aggregations()`。
  - 支持手动执行，不依赖定时任务。

- `POST /aggregations/aggregate-today`（750-775）：
  - 手动触发今日数据聚合，分别计算数据库和实例聚合。
  - 调用 `calculate_today_aggregations()` 和 `calculate_today_instance_aggregations()`。

### 3.6 聚合状态监控
- `GET /aggregations/aggregate/status`（781-805）：
  - 获取聚合任务的执行状态。
  - 返回最近聚合时间、各周期类型统计、配置信息等。

## 4. 聚合服务实现（`database_size_aggregation_service.py`）

### 4.1 核心服务类
- `DatabaseSizeAggregationService`（20-84）：
  - 支持四种周期类型：daily、weekly、monthly、quarterly。
  - 提供全量聚合计算 `calculate_all_aggregations()`。
  - 包含数据库级别和实例级别的聚合计算。

### 4.2 周期聚合方法
- `calculate_daily_aggregations()`（85-98）：处理今天的数据，用于定时任务。
- `calculate_today_aggregations()`（100-113）：手动触发的今日聚合。
- `calculate_weekly_aggregations()`、`calculate_monthly_aggregations()`、`calculate_quarterly_aggregations()`：
  - 分别计算周、月、季度的聚合数据。
  - 调用 `_calculate_aggregations()` 核心方法。

### 4.3 聚合计算核心逻辑
- `_calculate_aggregations(period_type, start_date, end_date)`（503-573）：
  - 获取所有活跃实例，按实例和数据库分组统计。
  - 从 `DatabaseSizeStat` 表获取原始数据。
  - 调用 `_calculate_database_aggregation()` 计算每个数据库的聚合。
  - 返回处理结果统计（总处理数、错误数、记录数）。

### 4.4 数据库聚合计算
- `_calculate_database_aggregation()`：
  - 计算平均、最大、最小大小等统计指标。
  - 计算数据大小、日志大小的统计（如果可获取）。
  - 计算与上一周期相比的变化量和变化百分比。
  - 保存或更新 `DatabaseSizeAggregation` 记录。

### 4.5 变化统计计算
- `_calculate_change_statistics()`：
  - 获取上一周期的聚合数据进行比较。
  - 计算总大小、数据大小、日志大小的变化量和百分比。
  - 确定增长率和趋势方向（growing、shrinking、stable）。

### 4.6 实例聚合计算
- 提供对应的实例级别聚合方法：
  - `calculate_daily_instance_aggregations()`、`calculate_weekly_instance_aggregations()` 等。
  - 从 `InstanceSizeStat` 表获取实例级别的原始数据。
  - 计算实例总大小、数据库数量等统计指标。

## 5. 定时任务实现（`database_size_aggregation_tasks.py`）

### 5.1 主要聚合任务
- `calculate_database_size_aggregations(manual_run=False)`（17-319）：
  - 支持定时执行和手动执行两种模式。
  - 创建同步会话进行进度跟踪和监控。
  - 按四种周期类型依次计算聚合：daily、weekly、monthly、quarterly。
  - 分别计算数据库级别和实例级别的聚合。
  - 根据聚合结果更新所有实例记录状态。

### 5.2 会话管理集成
- 定时任务创建 `scheduled_task` 类型的会话（81-92）。
- 手动任务创建 `manual_task` 类型的会话（62-78）。
- 为每个活跃实例创建同步记录，跟踪处理进度（94-98）。
- 根据聚合结果更新实例记录状态为成功或失败（209-260）。

### 5.3 错误处理和状态更新
- 如果所有周期都成功，标记所有实例为成功（204-236）。
- 如果有任何周期失败，标记所有实例为失败（237-259）。
- 最终更新会话状态为 `completed` 或 `failed`（272-277）。

### 5.4 辅助任务函数
- `calculate_instance_aggregations(instance_id)`（322-368）：计算指定实例的聚合。
- `calculate_period_aggregations(period_type, start_date, end_date)`（371-405）：计算指定周期的聚合。
- `get_aggregation_status()`（408-451）：获取聚合状态信息。
- `cleanup_old_aggregations(retention_days=365)`（492-533）：清理旧的聚合数据。

## 6. 数据模型

### 6.1 数据库聚合模型（`database_size_aggregation.py`）
- **表名**：`database_size_aggregations`（按 `period_start` 字段月分区）
- **主要字段**：
  - `instance_id`、`database_name`：关联信息
  - `period_type`、`period_start`、`period_end`：周期信息
  - `avg_size_mb`、`max_size_mb`、`min_size_mb`、`data_count`：基础统计
  - `avg_data_size_mb`、`avg_log_size_mb`：数据和日志大小统计
  - `size_change_mb`、`size_change_percent`：变化统计
  - `growth_rate`：增长率
- **唯一约束**：`(instance_id, database_name, period_type, period_start)`（96）
- **索引优化**：实例+周期、周期类型等查询索引（78-88）

### 6.2 实例聚合模型（`instance_size_aggregation.py`）
- **表名**：`instance_size_aggregations`（按 `period_start` 字段月分区）
- **主要字段**：
  - `instance_id`：实例ID
  - `total_size_mb`、`avg_size_mb`、`max_size_mb`、`min_size_mb`：大小统计
  - `database_count`、`avg_database_count`：数据库数量统计
  - `total_size_change_mb`、`database_count_change`：变化统计
  - `growth_rate`、`trend_direction`：趋势分析
- **唯一约束**：`(instance_id, period_type, period_start)`（86-90）

## 7. 前端实现

### 7.1 数据库统计页面（`database_aggregations.html`）
- **页面标题**：数据库统计 - 数据库大小监控（3-74）
- **统一搜索**：支持实例、周期类型、数据库、数据库类型、时间范围筛选（76-99）
- **操作按钮**：刷新数据、聚合今日数据（63-70）
- **统计概览**：显示基础统计卡片（76-99 in template structure）
- **图表区域**：Chart.js图表展示，支持线图/柱图切换
- **数据表格**：分页显示聚合数据

### 7.2 实例统计页面（`instance_aggregations.html`）
- **页面标题**：容量统计(实例) - 数据库大小监控（3-48）
- **统一搜索**：支持实例、周期类型、数据库类型、时间范围筛选（50-73）
- **统计概览**：活跃实例数、总容量、平均容量、最大容量（76-169）
- **图表控制**：TOP选择器、统计周期选择器、图表类型切换
- **操作按钮**：刷新数据、统计今日容量（37-44）

### 7.3 前端JavaScript实现

#### 7.3.1 数据库统计脚本（`database_aggregations.js`）
- **`DatabaseAggregationsManager` 类**（6-30）：
  - 管理页面状态、过滤器、图表数据。
  - 支持 line/bar 图表类型切换（44-47）。
  - 动态更新实例和数据库选项（59-80）。

- **核心方法**：
  - `loadSummaryData()`：加载汇总统计数据
  - `loadChartData()`：加载图表数据
  - `loadTableData()`：加载表格数据
  - `renderChart(data)`：使用Chart.js渲染图表
  - `calculateAggregations()`：触发手动聚合

#### 7.3.2 实例统计脚本（`instance_aggregations.js`）
- **`InstanceAggregationsManager` 类**（6-31）：
  - 增加TOP选择器（currentTopCount）和统计周期（currentStatisticsPeriod）。
  - 支持动态时间范围更新（58-61）。

- **特色功能**：
  - `updateTimeRangeFromPeriod()`：根据统计周期自动设置时间范围
  - TOP选择器：支持显示TOP 5/10/20实例（50-54）
  - 统计周期：支持显示最近7/14/30个周期的数据（56-61）

### 7.4 样式设计

#### 7.4.1 数据库统计样式（`database_aggregations.css`）
- **页面容器**：最小高度100vh，浅灰背景（7-10）
- **统计卡片**：无边框、阴影效果、悬停动画（13-22）
- **图表容器**：渐变背景、圆角边框（40-46）
- **表格样式**：斑马纹、悬停高亮（58-79）
- **数据库名称**：等宽字体、蓝色链接样式（82-91）

#### 7.4.2 实例统计样式（`instance_aggregations.css`）
- **设计一致性**：与数据库统计页面保持相同的设计风格
- **图表容器**：`#instanceChart` 特定样式（41-46）
- **按钮组**：选中状态的蓝色高亮（93-97）
- **模态框**：现代化弹窗样式（99-287）

## 8. 功能特性

### 8.1 多维度聚合
- **时间维度**：支持日、周、月、季度四种周期类型
- **数据维度**：数据库级别和实例级别的双重聚合
- **统计指标**：平均值、最大值、最小值、变化量、增长率

### 8.2 趋势分析
- **变化统计**：计算与上一周期相比的变化量和百分比
- **增长率计算**：确定数据增长趋势（growing、shrinking、stable）
- **图表可视化**：Chart.js线图和柱图展示趋势

### 8.3 实时监控
- **会话管理**：集成同步会话系统，实时跟踪聚合进度
- **状态监控**：提供聚合状态API，监控任务执行情况
- **错误处理**：详细的错误记录和恢复机制

### 8.4 数据管理
- **分区存储**：聚合表按月分区，优化查询性能
- **数据清理**：支持设置保留期限，自动清理历史数据
- **索引优化**：多维度索引，支持复杂查询场景

## 9. 性能优化

### 9.1 查询优化
- **分区查询**：利用月分区提高查询效率
- **索引策略**：多字段组合索引优化常用查询
- **分页处理**：支持分页查询，避免大数据集性能问题

### 9.2 计算优化
- **增量计算**：只计算新增数据，避免重复计算
- **批量处理**：按实例和数据库分组，批量计算聚合
- **缓存策略**：缓存频繁访问的聚合结果

### 9.3 前端优化
- **异步加载**：图表和表格数据异步加载，提升用户体验
- **动态筛选**：实时筛选和搜索，减少不必要的数据传输
- **图表优化**：Chart.js配置优化，支持大数据集展示

## 10. 错误处理

### 10.1 服务层错误处理
- **数据验证**：验证周期类型、日期范围等参数
- **异常捕获**：完整的try-catch机制，记录详细错误信息
- **事务管理**：使用数据库事务确保数据一致性

### 10.2 任务错误处理
- **会话状态**：通过会话记录跟踪任务执行状态
- **实例状态**：单独跟踪每个实例的处理结果
- **错误恢复**：支持部分失败的容错处理

### 10.3 前端错误处理
- **AJAX错误**：统一的错误提示和用户反馈
- **数据校验**：前端参数验证，减少无效请求
- **加载状态**：明确的加载指示器和错误状态

## 11. 安全考虑

### 11.1 权限控制
- **访问控制**：所有接口使用登录和权限验证
- **数据隔离**：基于用户权限显示相应的数据
- **操作审计**：记录重要操作的审计日志

### 11.2 数据安全
- **参数验证**：严格验证所有输入参数
- **SQL注入防护**：使用ORM和参数化查询
- **数据脱敏**：敏感信息的适当处理

## 12. 测试建议

### 12.1 功能测试
- **聚合准确性**：验证各周期类型的聚合计算准确性
- **趋势分析**：测试变化统计和增长率计算
- **筛选功能**：验证多维度筛选的正确性

### 12.2 性能测试
- **大数据量**：测试大量数据下的聚合性能
- **并发处理**：测试多用户同时访问的性能
- **查询响应**：验证复杂查询的响应时间

### 12.3 集成测试
- **会话集成**：测试与同步会话系统的集成
- **定时任务**：验证定时聚合任务的正确执行
- **前后端**：测试前端界面与后端API的交互

## 13. 后续优化方向

### 13.1 功能增强
- **预测分析**：基于历史趋势进行容量预测
- **告警机制**：异常增长或容量不足的自动告警
- **报表导出**：聚合数据的Excel、PDF导出功能

### 13.2 性能提升
- **实时计算**：支持近实时的聚合计算
- **分布式处理**：大规模数据的分布式聚合
- **智能缓存**：基于访问模式的智能缓存策略

### 13.3 可视化增强
- **高级图表**：更多图表类型和交互功能
- **仪表板**：综合的监控仪表板
- **移动端**：移动设备优化的响应式设计
