# 前端调用检查总结

## 问题："统计今日容量"按钮使用什么方法？

### 调用链路

```
前端按钮 "统计今日容量"
    ↓
JavaScript: calculateAggregations()
    ↓
API 请求: POST /aggregations/api/aggregate-today
    ↓
路由方法: aggregate_today()
    ↓
服务方法: service.calculate_daily_aggregations() ✅ 正在使用
```

### 代码位置

1. **前端按钮**：
   - `app/templates/database_sizes/instance_aggregations.html`
   - `app/templates/database_sizes/database_aggregations.html`
   ```html
   <button class="btn btn-light" id="calculateAggregations">
       <i class="fas fa-calculator me-1"></i>统计今日容量
   </button>
   ```

2. **前端 JavaScript**：
   - `app/static/js/pages/capacity_stats/instance_aggregations.js`
   - `app/static/js/pages/capacity_stats/database_aggregations.js`
   ```javascript
   async calculateAggregations() {
       const response = await fetch('/aggregations/api/aggregate-today', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' }
       });
   }
   ```

3. **后端路由**：
   - `app/routes/aggregations.py:206`
   ```python
   @aggregations_bp.route('/api/aggregate-today', methods=['POST'])
   def aggregate_today() -> Response:
       service = DatabaseSizeAggregationService()
       raw_result = service.calculate_daily_aggregations()  # ← 这里
   ```

4. **服务方法**：
   - `app/services/database_size_aggregation_service.py`
   ```python
   def calculate_daily_aggregations(self) -> Dict[str, Any]:  # ✅ 正在使用
       """计算每日统计聚合（定时任务用，处理今天的数据）"""
   ```

### 关键区别

⚠️ **注意方法名称的区别**：

| 方法名 | 状态 | 说明 |
|--------|------|------|
| `calculate_daily_aggregations()` | ✅ 正在使用 | 被前端"统计今日容量"按钮调用 |
| `calculate_today_aggregations()` | ❌ 未使用 | 冗余方法，功能相似但未被调用 |
| `calculate_daily_instance_aggregations()` | ✅ 正在使用 | 定时任务使用 |
| `calculate_today_instance_aggregations()` | ❌ 未使用 | 冗余方法，功能相似但未被调用 |

### 结论

- **可以安全删除**：`calculate_today_aggregations()` 和 `calculate_today_instance_aggregations()`
- **必须保留**：`calculate_daily_aggregations()` 和 `calculate_daily_instance_aggregations()`

这些是命名相似但实际不同的方法，前者是死代码，后者是正在使用的活代码。
