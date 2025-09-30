# 时区处理规范

## 概述

鲸落 (TaifishV4) 项目统一使用 `app.utils.time_utils` 模块进行时区处理，确保整个系统的时间处理一致性和准确性。

## 核心原则

### 1. 统一时区标准
- **数据库存储**：所有时间戳使用 UTC 时区存储
- **业务逻辑**：使用中国时区 (Asia/Shanghai) 进行业务计算
- **用户显示**：统一显示为中国时区时间

### 2. 模块使用规范
- **唯一入口**：所有时区相关操作必须通过 `app.utils.time_utils` 模块
- **禁止使用**：不得使用 `datetime.now()` 或 `datetime.utcnow()` 等原生方法
- **禁止导入**：不得从 `app.utils.timezone` 导入（已废弃）

## 使用方法

### 基础时间获取

```python
from app.utils.time_utils import time_utils

# 获取当前 UTC 时间（用于数据库存储）
utc_now = time_utils.now()

# 获取当前中国时间（用于业务逻辑和显示）
china_now = time_utils.now_china()
```

### 时区转换

```python
from app.utils.time_utils import time_utils

# UTC 转中国时区
china_time = time_utils.to_china(utc_datetime)

# 中国时区转 UTC
utc_time = time_utils.to_utc(china_datetime)
```

### 时间格式化

```python
from app.utils.time_utils import time_utils

# 格式化中国时间显示
formatted_time = time_utils.format_china_time(datetime_obj, "%Y-%m-%d %H:%M:%S")

# 格式化 UTC 时间显示
formatted_utc = time_utils.format_utc_time(datetime_obj, "%Y-%m-%d %H:%M:%S")
```

### 向后兼容函数

为了保持向后兼容性，提供了以下快捷函数：

```python
from app.utils.time_utils import now, now_china, utc_to_china, get_china_time

# 快捷函数（推荐使用 time_utils 实例方法）
utc_now = now()
china_now = now_china()
china_time = utc_to_china(utc_datetime)
china_time = get_china_time()
```

## 数据收集规范

### 容量同步数据收集

```python
from app.utils.time_utils import time_utils

# 数据收集时使用中国时区日期
china_now = time_utils.now_china()
data = {
    'collected_date': china_now.date(),  # 使用中国时区的日期
    'collected_at': time_utils.now(),    # 使用 UTC 时间戳
    # ... 其他字段
}
```

### 账户同步数据收集

```python
from app.utils.time_utils import time_utils

# 更新实例连接时间
instance.last_connected_at = time_utils.now()

# 同步会话时间戳
session.started_at = time_utils.now()
session.completed_at = time_utils.now()
```

## 常见使用场景

### 1. 数据库模型默认值

```python
from app.utils.time_utils import now
from sqlalchemy import Column, DateTime

class MyModel(db.Model):
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
```

### 2. API 响应时间戳

```python
from app.utils.time_utils import time_utils

def api_response():
    return {
        'data': {...},
        'timestamp': time_utils.now().isoformat()
    }
```

### 3. 日志记录

```python
from app.utils.time_utils import time_utils

logger.info("操作完成", extra={
    'timestamp': time_utils.now(),
    'user_id': user_id
})
```

### 4. 文件导出

```python
from app.utils.time_utils import time_utils

def export_data():
    timestamp = time_utils.now().strftime("%Y%m%d_%H%M%S")
    filename = f"export_{timestamp}.csv"
    # ... 导出逻辑
```

## 迁移指南

### 从旧 timezone 模块迁移

**旧代码：**
```python
from app.utils.timezone import now, now_china, utc_to_china

utc_time = now()
china_time = now_china()
converted = utc_to_china(utc_time)
```

**新代码：**
```python
from app.utils.time_utils import time_utils

utc_time = time_utils.now()
china_time = time_utils.now_china()
converted = time_utils.to_china(utc_time)
```

### 从原生 datetime 迁移

**旧代码：**
```python
from datetime import datetime

now = datetime.now()
utc_now = datetime.utcnow()
```

**新代码：**
```python
from app.utils.time_utils import time_utils

now = time_utils.now_china()  # 中国时间
utc_now = time_utils.now()    # UTC 时间
```

## 最佳实践

### 1. 导入规范
```python
# ✅ 推荐：使用实例方法
from app.utils.time_utils import time_utils
utc_time = time_utils.now()

# ✅ 可接受：使用快捷函数
from app.utils.time_utils import now
utc_time = now()

# ❌ 禁止：使用原生方法
from datetime import datetime
utc_time = datetime.now()
```

### 2. 时区选择原则
- **数据库字段**：使用 UTC 时间
- **业务计算**：使用中国时区
- **用户界面**：显示中国时区
- **API 响应**：使用 UTC 时间戳

### 3. 错误处理
```python
from app.utils.time_utils import time_utils

try:
    china_time = time_utils.to_china(some_datetime)
    if china_time is None:
        # 处理转换失败的情况
        china_time = time_utils.now_china()
except Exception as e:
    # 记录错误并使用当前时间
    logger.error(f"时区转换失败: {e}")
    china_time = time_utils.now_china()
```

## 注意事项

1. **时区一致性**：确保所有模块使用相同的时区处理标准
2. **性能考虑**：避免频繁的时区转换操作
3. **测试覆盖**：时区相关功能必须有完整的测试用例
4. **文档更新**：新增时区相关功能时及时更新文档

## 相关文件

- `app/utils/time_utils.py` - 时区处理核心模块
- `tests/unit/utils/test_time_utils.py` - 时区处理测试用例
- `docs/development/timezone_handling.md` - 本文档

## 更新历史

- **2024-01-XX**：统一时区处理，废弃 `app.utils.timezone` 模块
- **2024-01-XX**：创建 `app.utils.time_utils` 模块
- **2024-01-XX**：完成全项目时区处理迁移
