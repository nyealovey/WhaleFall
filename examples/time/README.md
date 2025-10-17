# 统一时间处理示例

本目录包含了统一时间处理工具的完整示例代码，展示了如何在不同环境中使用统一的时间处理方案。

## 📁 文件说明

### 1. `unified_time_example.py`
**后端 Python 示例**
- 展示后端时间处理的完整用法
- 包含数据库模型、API 响应、错误处理等场景
- 基于 `app/utils/time_utils.py` 的统一时间工具

**运行方式：**
```bash
python examples/time/unified_time_example.py
```

**主要演示内容：**
- 基础时间操作（获取、转换）
- 时间格式化（多种格式）
- 相对时间计算
- 时间范围处理
- 数据库模型使用
- API 响应序列化
- 错误处理
- 性能考虑

### 2. `frontend_time_example.js`
**前端 JavaScript 示例**
- 展示前端时间处理的完整用法
- 包含 DOM 操作、API 交互、性能优化等场景
- 基于 `app/static/js/common/time-utils.js` 的统一时间工具

**使用方式：**
```html
<!-- 在 HTML 中引入 -->
<script src="../../app/static/js/common/time-utils.js"></script>
<script src="frontend_time_example.js"></script>
```

**主要演示内容：**
- 基础时间格式化
- 时间解析和验证
- 相对时间计算
- DOM 操作中的时间处理
- 与后端 API 的时间数据交互
- 错误处理
- 性能优化技巧

### 3. `time_demo.html`
**完整的网页演示**
- 可视化的时间处理演示页面
- 包含实时更新、交互式测试等功能
- 展示实际应用场景

**使用方式：**
```bash
# 在浏览器中打开
open examples/time/time_demo.html
```

**主要功能：**
- 实时时间显示
- 交互式时间验证
- 性能测试
- API 数据处理演示
- 错误处理展示

## 🎯 核心原则

### 1. 统一的时间处理方式
```python
# 后端 Python
from app.utils.time_utils import time_utils

# 获取时间
utc_now = time_utils.now()
china_now = time_utils.now_china()

# 格式化时间
formatted = time_utils.format_china_time(utc_now)
relative = time_utils.get_relative_time(utc_now)
```

```javascript
// 前端 JavaScript
// 格式化时间
const formatted = timeUtils.formatDateTime(timestamp);
const relative = timeUtils.formatRelativeTime(timestamp);

// 时间验证
const isValid = timeUtils.isValidTime(input);
const parsed = timeUtils.parseTime(input);
```

### 2. 数据库时间字段
```python
# 所有模型时间字段统一使用
created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)
```

### 3. API 响应时间序列化
```python
# 统一使用 ISO 格式
{
    "created_at": time_utils.to_json_serializable(record.created_at),
    "updated_at": time_utils.to_json_serializable(record.updated_at)
}
```

### 4. 模板时间显示
```html
<!-- 使用统一的时间过滤器 -->
<td>{{ instance.created_at | china_datetime }}</td>
<td>{{ instance.last_connected | china_time('%Y-%m-%d %H:%M') }}</td>
<td>{{ log.timestamp | relative_time }}</td>
```

## 🔧 技术实现

### 后端架构
```
app/utils/time_utils.py
├── TimeUtils 类
│   ├── now() - 获取 UTC 时间
│   ├── now_china() - 获取中国时间
│   ├── to_china() - 转换为中国时区
│   ├── format_china_time() - 格式化中国时间
│   └── get_relative_time() - 相对时间计算
├── TimeFormats 类 - 时间格式常量
└── time_utils 全局实例
```

### 前端架构
```
app/static/js/common/time-utils.js
├── TimeUtils 对象
│   ├── formatTime() - 基础格式化
│   ├── formatDateTime() - 日期时间格式化
│   ├── formatRelativeTime() - 相对时间
│   ├── parseTime() - 时间解析
│   └── isValidTime() - 时间验证
├── TimeFormats 常量
└── window.timeUtils 全局实例
```

### 模板过滤器
```
app/__init__.py
├── china_time - 中国时区时间格式化
├── china_date - 中国时区日期格式化
├── china_datetime - 中国时区日期时间格式化
├── relative_time - 相对时间显示
└── smart_time - 智能时间显示
```

## 📊 使用场景

### 1. 数据库操作
```python
# 创建记录
instance = Instance(
    name="测试实例",
    created_at=time_utils.now(),  # UTC 时间存储
    updated_at=time_utils.now()
)

# 查询时间范围
time_range = time_utils.get_time_range(24)  # 最近24小时
instances = Instance.query.filter(
    Instance.created_at >= time_range['start_utc']
).all()
```

### 2. API 响应
```python
# 序列化时间数据
def serialize_instance(instance):
    return {
        "id": instance.id,
        "name": instance.name,
        "created_at": time_utils.to_json_serializable(instance.created_at),
        "created_at_formatted": time_utils.format_china_time(instance.created_at),
        "created_at_relative": time_utils.get_relative_time(instance.created_at)
    }
```

### 3. 前端显示
```javascript
// 处理 API 响应
fetch('/api/instances')
    .then(response => response.json())
    .then(data => {
        data.forEach(instance => {
            const formatted = timeUtils.formatDateTime(instance.created_at);
            const relative = timeUtils.formatRelativeTime(instance.created_at);
            
            // 更新 DOM
            element.innerHTML = `
                <div>创建时间: ${formatted}</div>
                <div>相对时间: ${relative}</div>
            `;
        });
    });
```

### 4. 模板渲染
```html
<!-- 实例列表 -->
{% for instance in instances %}
<tr>
    <td>{{ instance.name }}</td>
    <td>{{ instance.created_at | china_datetime }}</td>
    <td>{{ instance.last_connected | relative_time }}</td>
</tr>
{% endfor %}
```

## ⚡ 性能优化

### 1. 批量处理
```python
# 后端批量格式化
formatted_times = [
    time_utils.format_china_time(record.created_at)
    for record in records
]
```

```javascript
// 前端批量处理
const formattedTimes = timestamps.map(ts => 
    timeUtils.formatDateTime(ts)
);
```

### 2. 缓存策略
```python
# 缓存相对时间计算结果
@lru_cache(maxsize=1000)
def cached_relative_time(timestamp_str):
    return time_utils.get_relative_time(timestamp_str)
```

### 3. 避免重复计算
```javascript
// 前端避免重复格式化
const timeCache = new Map();

function getCachedFormattedTime(timestamp) {
    if (!timeCache.has(timestamp)) {
        timeCache.set(timestamp, timeUtils.formatDateTime(timestamp));
    }
    return timeCache.get(timestamp);
}
```

## 🛡️ 错误处理

### 1. 统一错误处理
```python
# 后端统一返回默认值
def safe_format_time(timestamp):
    try:
        return time_utils.format_china_time(timestamp)
    except Exception:
        return "-"
```

```javascript
// 前端统一错误处理
function safeFormatTime(timestamp) {
    try {
        return timeUtils.formatDateTime(timestamp);
    } catch (error) {
        console.warn('时间格式化失败:', error);
        return '-';
    }
}
```

### 2. 输入验证
```python
# 后端验证
if not time_utils.to_china(user_input):
    raise ValidationError("无效的时间格式")
```

```javascript
// 前端验证
if (!timeUtils.isValidTime(userInput)) {
    showError("请输入有效的时间格式");
    return;
}
```

## 📝 最佳实践

### 1. 开发规范
- **后端**: 强制使用 `time_utils.method()` 方式
- **前端**: 强制使用 `timeUtils.method()` 方式
- **模板**: 使用统一的时间过滤器
- **数据库**: 所有时间字段使用 `timezone=True`

### 2. 代码审查
- 检查是否使用了统一的时间处理方式
- 确保时间格式的一致性
- 验证错误处理的完整性
- 测试时区转换的正确性

### 3. 测试策略
- 单元测试覆盖所有时间处理函数
- 集成测试验证前后端时间一致性
- 性能测试确保批量处理效率
- 边界测试验证错误处理

## 🔗 相关文档

- [时间处理统一方案完成报告](../../docs/refactoring/time_unification_100_percent_completion_report.md)
- [前端时间工具重构报告](../../docs/refactoring/frontend_time_utils_refactoring_completion.md)
- [时间分析报告](../../docs/reports/time_analysis_report.md)
- [时区和日志级别统一方案](../../docs/refactoring/timezone_and_loglevel_unification.md)

---

**🎯 这些示例展示了完整的统一时间处理方案，确保前后端时间处理的完全一致性和系统的长期稳定性。**