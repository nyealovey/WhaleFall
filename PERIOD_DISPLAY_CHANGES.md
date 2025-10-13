# 周期显示时间修改总结

## 修改目标
将图表X轴的日期显示统一改为使用 `period_end`（结束时间），替代原来的 `period_start`（开始时间）。

## 修改原因
- **统一性**：所有聚合类型都使用相同的日期字段，代码更简洁统一
- **直观性**：显示结束时间更直观，表示"截止到这个时间点的数据"
- **日聚合兼容**：对于日聚合，`period_start` 和 `period_end` 本身就是同一天，所以改用 `period_end` 不会有任何影响
- **周聚合**：显示周日日期比周一日期更直观
- **月聚合**：显示月末日期比月初日期更直观  
- **季度聚合**：显示季度末日期比季度初日期更直观

## 修改的文件

### 1. app/static/js/pages/database_sizes/aggregations_chart.js
- **函数**: `groupDataByDate(data)`
- **函数**: `updateChartStats(data)`  
- **修改**: 统一使用 `period_end` 替代 `period_start`

### 2. app/static/js/pages/database_sizes/database_aggregations.js
- **函数**: `groupSizeDataByDate(data)`
- **函数**: `groupChangePercentDataByDate(data)`
- **函数**: `groupChangeDataByDate(data)`
- **修改**: 所有三个函数都统一使用 `period_end` 替代 `period_start`

### 3. app/static/js/pages/database_sizes/instance_aggregations.js
- **函数**: `groupDataByDate(data)`
- **函数**: `groupChangeDataByDate(data)`
- **函数**: `groupChangePercentDataByDate(data)`
- **修改**: 所有三个函数都统一使用 `period_end` 替代 `period_start`

## 修改逻辑
```javascript
// 修改前
const date = item.period_start;

// 修改后（统一使用period_end）
const date = item.period_end;
```

## 影响的页面
1. **http://10.10.66.45/database_stats** - 实例统计页面
2. **http://10.10.66.45/database_stats/database** - 数据库统计页面

## 预期效果
- **日聚合**: X轴显示 `2025-01-13`（当天日期，与之前相同）
- **周聚合**: X轴显示 `2025-01-12`（周日日期，而不是周一日期）
- **月聚合**: X轴显示 `2025-01-31`（月末日期，而不是月初日期）
- **季度聚合**: X轴显示 `2025-03-31`（季度末日期，而不是季度初日期）

## 代码优势
1. **简化逻辑**：不再需要根据 `period_type` 进行条件判断
2. **统一性**：所有聚合类型使用相同的日期字段
3. **可维护性**：代码更简洁，减少出错可能性
4. **向后兼容**：对日聚合没有任何影响

## 注意事项
1. 后端数据结构无需修改，仍然返回 `period_start` 和 `period_end` 两个字段
2. 只是前端显示逻辑的调整，不影响数据存储和计算
3. 所有相关的图表和数据展示都已同步修改

## 部署建议
1. 清除浏览器缓存以确保加载新的JavaScript文件
2. 验证各个聚合类型的图表显示是否正确
3. 检查时间范围选择器的行为是否正常