# 实例统计功能技术文档

## 1. 功能概述

### 1.1 模块职责
- 提供数据库实例的统计信息和监控数据，包括实例数量统计、数据库类型分布、端口分布、版本统计等。
- 支持实时统计、性能监控和趋势分析功能。
- 提供统计数据的可视化展示，包括图表和表格形式。
- 支持统计数据的自动刷新和手动刷新功能。

### 1.2 代码定位
- 路由：`app/routes/instances.py`（实例统计相关接口）
- 前端：`app/templates/instances/statistics.html`、`app/static/js/pages/instances/statistics.js`
- 样式：`app/static/css/pages/instances/statistics.css`
- 模型：`app/models/instance.py`（实例数据模型）

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────────────────────┐
│ 前端统计界面                 │
│  - 统计卡片展示            │
│  - 图表可视化              │
│  - 自动刷新功能            │
│  - 手动刷新控制            │
└───────▲───────────┬──────┘
        │AJAX        │
┌───────┴───────────▼──────┐
│ Flask 路由 (instances.py) │
│  - /statistics           │
│  - /api/statistics       │
└───────▲───────────┬──────┘
        │SQLAlchemy │
┌───────┴───────────▼──────┐
│ 数据层                   │
│  - Instance模型           │
│  - 统计查询函数          │
└────────────────────────────┘
```

### 2.2 权限控制
- 所有接口使用 `@login_required` 和 `@view_required`。

## 3. 路由实现（`instances.py`）

### 3.1 统计页面路由
- `GET /instances/statistics`（431-441）：
  - 渲染实例统计页面。
  - 支持JSON请求返回统计数据。
  - 使用 `get_instance_statistics()` 获取统计数据。

### 3.2 统计API路由
- `GET /instances/api/statistics`（444-450）：
  - 提供统计数据API接口。
  - 返回JSON格式的统计数据。
  - 供前端自动刷新使用。

## 4. 核心业务逻辑

### 4.1 统计数据获取函数
- `get_instance_statistics()`（1426-1500）：
  - 基础统计：总实例数、活跃实例数、禁用实例数。
  - 数据库类型统计：按类型分组统计实例数量。
  - 端口统计：按端口分组统计，取前10个最常用端口。
  - 版本统计：按数据库类型和主版本分组统计。
  - 错误处理：异常时返回默认统计数据。

### 4.2 统计查询实现
- 基础统计查询（1429-1432）：
  ```python
  total_instances = Instance.query.count()
  active_instances = Instance.query.filter_by(is_active=True).count()
  inactive_instances = Instance.query.filter_by(is_active=False).count()
  ```

- 数据库类型统计（1434-1439）：
  ```python
  db_type_stats = (
      db.session.query(Instance.db_type, db.func.count(Instance.id).label("count"))
      .group_by(Instance.db_type)
      .all()
  )
  ```

- 端口统计（1441-1448）：
  ```python
  port_stats = (
      db.session.query(Instance.port, db.func.count(Instance.id).label("count"))
      .group_by(Instance.port)
      .order_by(db.func.count(Instance.id).desc())
      .limit(10)
      .all()
  )
  ```

- 版本统计（1450-1469）：
  ```python
  version_stats = (
      db.session.query(
          Instance.db_type,
          Instance.main_version,
          db.func.count(Instance.id).label("count"),
      )
      .group_by(Instance.db_type, Instance.main_version)
      .all()
  )
  ```

## 5. 前端实现

### 5.1 统计页面模板（`statistics.html`）
- 统计卡片：显示总实例数、活跃实例、禁用实例、数据库类型数。
- 数据库类型分布表：显示各数据库类型的数量和百分比。
- 端口分布表：显示端口使用情况统计。
- 版本统计表：显示数据库版本分布。
- 版本分布图：使用Chart.js绘制饼图。

### 5.2 前端JavaScript（`statistics.js`）
- `createVersionChart()`（17-41）：创建版本分布图表。
- `getVersionStats()`（44-62）：获取版本统计数据。
- `groupStatsByDbType()`（65-74）：按数据库类型分组统计数据。
- `createChartData()`（77-110）：创建图表数据。
- `getChartOptions()`（113-140）：获取图表配置选项。
- `startAutoRefresh()`（143-150）：开始自动刷新。
- `refreshStatistics()`（159-171）：刷新统计数据。
- `updateStatistics()`（174-190）：更新统计数据显示。

## 6. 核心功能实现

### 6.1 基础统计功能
- **总实例数**：统计所有数据库实例数量。
- **活跃实例**：统计启用状态的实例数量。
- **禁用实例**：统计禁用状态的实例数量。
- **数据库类型数**：统计不同数据库类型的数量。

### 6.2 数据库类型分布
- **类型统计**：按数据库类型分组统计实例数量。
- **百分比计算**：计算每种类型占总数的百分比。
- **可视化展示**：使用进度条和徽章显示分布情况。

### 6.3 端口分布统计
- **端口统计**：统计各端口的使用情况。
- **TOP 10**：显示使用最多的前10个端口。
- **使用频率**：显示每个端口的实例数量。

### 6.4 版本统计
- **版本分布**：按数据库类型和版本统计实例数量。
- **图表展示**：使用饼图显示版本分布。
- **详细信息**：显示具体版本号和实例数量。

### 6.5 实时监控
- **自动刷新**：每60秒自动刷新统计数据。
- **手动刷新**：提供手动刷新按钮。
- **状态通知**：显示数据更新状态。

## 7. 图表实现

### 7.1 Chart.js集成
- 使用Chart.js库绘制版本分布饼图。
- 支持响应式设计和交互功能。
- 自定义颜色方案和样式。

### 7.2 图表配置
- 图表类型：doughnut（环形图）。
- 响应式：支持不同屏幕尺寸。
- 图例：底部显示，使用点样式。
- 工具提示：显示详细信息和百分比。

### 7.3 数据格式
- 标签：数据库类型和版本组合。
- 数据：实例数量。
- 颜色：按数据库类型分配不同颜色。

## 8. 响应格式

### 8.1 统计数据响应
```json
{
  "total_instances": 15,
  "active_instances": 12,
  "inactive_instances": 3,
  "db_types_count": 4,
  "db_type_stats": [
    {
      "db_type": "mysql",
      "count": 8
    },
    {
      "db_type": "postgresql",
      "count": 4
    }
  ],
  "port_stats": [
    {
      "port": 3306,
      "count": 8
    },
    {
      "port": 5432,
      "count": 4
    }
  ],
  "version_stats": [
    {
      "db_type": "mysql",
      "version": "8.0",
      "count": 5
    },
    {
      "db_type": "mysql",
      "version": "5.7",
      "count": 3
    }
  ]
}
```

## 9. 性能优化

### 9.1 数据库查询优化
- 使用索引优化查询性能。
- 合理使用GROUP BY和聚合函数。
- 避免N+1查询问题。
- 限制端口统计查询结果数量。

### 9.2 前端性能优化
- 使用Chart.js进行图表渲染。
- 实现数据缓存机制。
- 优化DOM操作和事件处理。
- 防抖技术避免频繁请求。

### 9.3 缓存策略
- 统计数据缓存60秒。
- 版本信息缓存更长时间。
- 使用浏览器缓存优化加载速度。

## 10. 错误处理

### 10.1 后端错误处理
- 统一异常处理机制。
- 详细的错误日志记录。
- 返回默认统计数据。
- 用户友好的错误信息。

### 10.2 前端错误处理
- AJAX请求错误处理。
- 图表渲染错误处理。
- 数据解析错误处理。
- 网络异常处理。

## 11. 测试建议

### 11.1 功能测试
- 统计数据的准确性。
- 图表渲染的正确性。
- 自动刷新功能。
- 手动刷新功能。

### 11.2 性能测试
- 大量实例的统计性能。
- 图表渲染性能。
- 自动刷新的稳定性。
- 内存使用情况。

## 12. 后续优化方向

### 12.1 功能增强
- 添加更多统计维度。
- 实现统计数据的导出功能。
- 添加统计数据的趋势分析。
- 支持自定义统计时间范围。

### 12.2 可视化增强
- 添加更多图表类型。
- 实现交互式图表。
- 支持图表数据的钻取。
- 添加统计数据的对比功能。

### 12.3 监控告警
- 集成统计数据的监控告警。
- 添加异常数据检测。
- 实现统计数据的阈值告警。
- 提供统计数据的健康检查。
