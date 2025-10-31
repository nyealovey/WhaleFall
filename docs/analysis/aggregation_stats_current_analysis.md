# 聚合统计当前周期显示问题分析

## 问题描述

用户反馈：容量统计图表不显示当前周期的数据。

## 现状分析

### 1. 数据存储情况

✅ **当前周期数据已经存入数据库**

代码证据：
```python
# app/services/aggregation/database_runner.py
def _persist_database_aggregation(...):
    aggregation = DatabaseSizeAggregation.query.filter(...).first()
    if aggregation is None:
        aggregation = DatabaseSizeAggregation(...)
    # 更新数据
    db.session.add(aggregation)
    self._commit_with_partition_retry(aggregation, start_date)
```

当用户点击"统计当前周期"按钮时，数据会写入 `database_size_aggregations` 和 `instance_size_aggregations` 表。

### 2. 当前周期的特征

**当前周期数据**：
- `period_start`: 周期开始日期（如本周一、本月1日）
- `period_end`: **今天的日期**
- 数据会随时间更新

**历史周期数据**：
- `period_start`: 周期开始日期
- `period_end`: 周期结束日期（完整周期）
- 数据固定不变

**示例**（假设今天是 2024-10-31 周四）：

| 周期类型 | period_start | period_end | 说明 |
|---------|--------------|------------|------|
| 当前周 | 2024-10-28 (周一) | 2024-10-31 (今天) | 当前周期 |
| 上周 | 2024-10-21 (周一) | 2024-10-27 (周日) | 历史周期 |

### 3. 问题根因

查看 API 查询逻辑（`app/routes/database_stats.py`）：

```python
def _fetch_database_aggregations(...):
    query = DatabaseSizeAggregation.query.join(Instance)
    
    # ... 各种筛选条件 ...
    
    if end_date:
        query = query.filter(DatabaseSizeAggregation.period_end <= end_date)
```

**可能的问题**：

1. **前端没有传 `end_date`**：如果前端查询时没有指定 `end_date`，或者 `end_date` 设置为过去的日期，就会漏掉当前周期数据

2. **前端查询逻辑**：需要检查前端是如何构造查询参数的

## 解决方案

### 方案：确保前端查询包含当前周期

**不需要修改数据库结构**，只需要确保：

1. **前端查询时不限制 `end_date`**，或者将 `end_date` 设置为今天或未来日期
2. **后端查询逻辑保持不变**，已经可以查询到所有数据

### 实施步骤

#### 步骤1：检查前端查询逻辑

查看 `app/static/js/common/capacity_stats/data_source.js` 或相关文件，确认：

```javascript
// 查询参数应该包含当前周期
const params = {
    instance_id: selectedInstance,
    period_type: selectedPeriod,
    // 不设置 end_date，或者设置为今天
    // end_date: today
};
```

#### 步骤2：验证数据

在数据库中检查当前周期数据是否存在：

```sql
-- 查看今天的数据
SELECT 
    instance_id,
    database_name,
    period_type,
    period_start,
    period_end,
    avg_size_mb
FROM database_size_aggregations
WHERE period_end = CURRENT_DATE
ORDER BY period_start DESC
LIMIT 10;
```

#### 步骤3：测试

1. 点击"统计当前周期"按钮
2. 刷新页面
3. 检查图表是否显示最新数据

## 前端改造建议（可选）

如果需要在图表中区分当前周期和历史周期，可以：

### 选项1：使用不同样式（推荐）

```javascript
// 在图表渲染时，根据 period_end 判断是否为当前周期
const isCurrentPeriod = (item) => {
    const today = new Date().toISOString().split('T')[0];
    return item.period_end === today;
};

// 当前周期使用虚线
dataset.borderDash = isCurrentPeriod(item) ? [5, 5] : [];
```

### 选项2：添加图例说明

```javascript
// 在图表上添加说明
const legend = {
    labels: [
        { text: '历史周期', style: 'solid' },
        { text: '当前周期（实时）', style: 'dashed' }
    ]
};
```

## 总结

### 核心问题

**不是数据库的问题，是查询逻辑的问题**：
- ✅ 数据已经存入数据库
- ❌ 前端查询时可能过滤掉了当前周期数据

### 解决方案

**最简单的方案**：
1. 确保前端查询时不限制 `end_date`
2. 或者将 `end_date` 设置为今天或未来日期

**不需要**：
- ❌ 修改数据库结构
- ❌ 添加 `is_current_period` 字段
- ❌ 修改后端查询逻辑

### 验证方法

```sql
-- 1. 检查当前周期数据是否存在
SELECT COUNT(*) FROM database_size_aggregations 
WHERE period_end >= CURRENT_DATE - INTERVAL '7 days';

-- 2. 检查最新的聚合数据
SELECT 
    period_type,
    period_start,
    period_end,
    COUNT(*) as count
FROM database_size_aggregations
GROUP BY period_type, period_start, period_end
ORDER BY period_end DESC
LIMIT 20;
```

### 下一步

1. 检查前端查询参数
2. 验证数据库中是否有当前周期数据
3. 如果数据存在但图表不显示，检查前端渲染逻辑
4. 如果需要，添加视觉区分（虚线、颜色等）

---

**文档版本**: 2.0  
**创建日期**: 2024-10-31  
**最后更新**: 2024-10-31  
**结论**: 不需要修改数据库，只需要检查前端查询逻辑
