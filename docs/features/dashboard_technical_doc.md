# 系统仪表板功能技术文档

## 1. 功能概述

### 1.1 模块职责
- 提供系统概览数据的实时展示，包括实例、账户、分类、任务、日志等统计信息。
- 实现系统状态监控，包括CPU、内存、磁盘使用率和数据库、Redis、应用服务状态。
- 提供图表数据展示，包括日志趋势、任务状态分布、同步趋势等。
- 支持数据缓存和自动刷新功能，提升用户体验。

### 1.2 代码定位
- 路由：`app/routes/dashboard.py`
- 模板：`app/templates/dashboard/overview.html`
- 脚本：`app/static/js/pages/dashboard/overview.js`
- 样式：`app/static/css/pages/dashboard/overview.css`
- 工具：`app/utils/cache_manager.py`、`app/utils/time_utils.py`

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────────────────────┐
│ 前端仪表板界面               │
│  - 概览卡片展示            │
│  - 图表数据可视化          │
│  - 系统状态监控            │
└───────▲───────────┬──────┘
        │AJAX        │
┌───────┴───────────▼──────┐
│ Flask 路由 (dashboard_bp) │
│  - / (主页面)            │
│  - /api/overview         │
│  - /api/charts           │
│  - /api/status           │
└───────▲───────────┬──────┘
        │SQLAlchemy │缓存/工具
┌───────┴───────────▼──────┐
│ 数据层与服务              │
│  - 多模型数据聚合        │
│  - 缓存管理              │
│  - 系统监控              │
└────────────────────────────┘
```

### 2.2 权限控制
- 所有接口使用 `@login_required`，无需额外权限验证。

## 3. 路由实现（`dashboard.py`）

### 3.1 主页面路由
- `GET /`（30-63）：
  - 获取系统概览、图表数据、系统状态。
  - 支持JSON和HTML两种响应格式。
  - 记录操作日志（注释掉频繁日志记录）。

### 3.2 API接口
- `GET /api/overview`（66-86）：获取系统概览数据API。
- `GET /api/charts`（89-110）：获取图表数据API，支持按类型筛选。
- `GET /api/activities`（113-117）：获取最近活动API（已废弃，返回空数据）。
- `GET /api/status`（120-128）：获取系统状态API。

## 4. 数据获取函数

### 4.1 系统概览数据（`get_system_overview()`）
- **缓存策略**：使用 `@cached(timeout=300, key_prefix="dashboard")` 缓存5分钟（131）。
- **基础统计**：
  - 用户统计：`User.query.count()`（136）。
  - 实例统计：`Instance.query.count()`（137）。
  - 任务统计：从 `apscheduler_jobs` 表查询（147-153）。
  - 日志统计：`UnifiedLog.query.count()`（155）。
  - 账户统计：`CurrentAccountSyncData.query.filter_by(is_deleted=False).count()`（156）。

- **分类账户统计**（158-203）：
  - 获取所有活跃分类：`AccountClassification.query.filter_by(is_active=True).order_by(AccountClassification.priority.desc()).all()`（160）。
  - 从分配表获取分类账户数量：`AccountClassificationAssignment.query.filter_by(classification_id=classification.id, is_active=True)`（176-181）。
  - 验证账户有效性：检查账户是否仍然存在且有效（187-197）。
  - 计算自动分类账户数：`AccountClassificationAssignment.query.filter_by(is_active=True, assignment_type="auto")`（206-210）。

- **活跃账户统计**（215-240）：
  - 根据不同数据库类型判断账户锁定状态：
    - MySQL：使用 `is_locked` 字段（224-225）。
    - PostgreSQL：使用 `can_login` 字段，`can_login=False` 表示锁定（227-229）。
    - Oracle：使用 `account_status` 字段，`LOCKED` 表示锁定（231-233）。
    - SQL Server：使用 `is_locked` 字段（235-237）。

- **日志统计**（242-257）：
  - 今日日志数：使用东八区时间计算（243-250）。
  - 今日错误日志数：统计ERROR和CRITICAL级别日志（253-257）。

### 4.2 图表数据（`get_chart_data()`）
- **日志趋势图**（`get_log_trend_data()`）（316-357）：
  - 最近7天的错误和告警日志趋势。
  - 使用东八区时间计算UTC时间范围（329-331）。
  - 分别统计错误日志和告警日志数量（334-344）。

- **日志级别分布**（`get_log_level_distribution()`）（360-375）：
  - 统计ERROR、WARNING、CRITICAL级别日志分布。
  - 使用 `db.session.query(UnifiedLog.level, db.func.count(UnifiedLog.id).label("count"))`（365-369）。

- **任务状态分布**（`get_task_status_distribution()`）（378-395）：
  - 使用APScheduler获取任务状态。
  - 统计活跃和未活跃任务数量（387-390）。

- **同步趋势图**（`get_sync_trend_data()`）（398-416）：
  - 最近7天的同步数据趋势。
  - 使用 `SyncSession` 模型统计同步记录数量（410）。

### 4.3 系统状态（`get_system_status()`）
- **系统资源监控**（422-425）：
  - CPU使用率：`psutil.cpu_percent(interval=1)`。
  - 内存使用率：`psutil.virtual_memory()`。
  - 磁盘使用率：`psutil.disk_usage("/")`。

- **服务状态检查**（427-446）：
  - 数据库状态：执行 `SELECT 1` 查询（429-432）。
  - Redis状态：通过 `cache_manager.health_check()` 检查（436-443）。
  - 应用状态：默认为 "running"（448-449）。

- **系统运行时间**（`get_system_uptime()`）（489-505）：
  - 计算应用启动时间到当前时间的差值。
  - 格式化为 "X天 X小时 X分钟" 格式。

## 5. 前端实现（`overview.html`）

### 5.1 概览卡片展示
- **实例统计卡片**（24-38）：显示总实例数和活跃实例数。
- **账户统计卡片**（40-54）：显示总账户数和活跃账户数。
- **分类账户卡片**（56-102）：
  - 显示分类账户总数和自动分类数。
  - 按分类显示账户数量，使用不同图标和颜色。
  - 支持特权账户、风险账户、敏感账户、只读用户、普通账户等分类。

- **任务统计卡片**（103-117）：显示总任务数和活跃任务数。
- **日志统计卡片**（119-134）：显示今日日志数和错误日志数。

### 5.2 图表区域
- **日志趋势图**（140-152）：
  - 使用Chart.js绘制最近7天的错误和告警日志趋势。
  - 支持动态数据更新。

### 5.3 系统状态监控
- **资源使用率**（166-212）：
  - CPU、内存、磁盘使用率进度条显示。
  - 根据使用率设置不同颜色（绿色<60%，黄色60-80%，红色>80%）。

- **服务状态**（216-238）：
  - 数据库、Redis、应用服务状态指示器。
  - 使用不同颜色表示正常/异常状态。

- **系统运行时间**（240-245）：显示应用运行时间。

## 6. 缓存策略

### 6.1 数据缓存
- 系统概览数据缓存5分钟（`@cached(timeout=300, key_prefix="dashboard")`）。
- 减少数据库查询压力，提升响应速度。

### 6.2 缓存失效
- 定时任务执行后自动失效缓存。
- 数据更新后手动清理缓存。

## 7. 性能优化

### 7.1 查询优化
- 使用索引优化统计查询。
- 避免N+1查询问题。
- 使用聚合查询减少数据传输。

### 7.2 前端优化
- 图表数据按需加载。
- 支持自动刷新和手动刷新。
- 使用防抖技术优化用户操作。

## 8. 错误处理

### 8.1 后端错误处理
- 所有数据获取函数都有异常处理。
- 错误时返回默认值，确保页面正常显示。
- 记录错误日志用于问题排查。

### 8.2 前端错误处理
- AJAX请求失败时显示错误提示。
- 图表渲染失败时显示备用内容。

## 9. 测试建议

### 9.1 功能测试
- 概览数据统计的准确性。
- 图表数据展示的正确性。
- 系统状态监控的实时性。

### 9.2 性能测试
- 大量数据下的查询性能。
- 缓存机制的有效性。
- 前端渲染性能。

## 10. 后续优化方向

### 10.1 功能增强
- 添加更多图表类型（饼图、柱状图等）。
- 实现数据导出功能。
- 添加自定义时间范围选择。

### 10.2 性能优化
- 实现数据预加载。
- 优化大量数据的查询性能。
- 添加数据压缩和传输优化。

### 10.3 监控告警
- 集成监控告警系统。
- 添加阈值告警功能。
- 实现邮件/短信通知。
