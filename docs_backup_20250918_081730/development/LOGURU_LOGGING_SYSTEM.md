# 泰摸鱼吧 - Loguru日志系统

## 概述

泰摸鱼吧项目已升级到基于Loguru的现代化日志系统，提供统一的日志记录、自动轮转、结构化日志和本地化分析功能。

## 特性

### ✨ 核心特性
- **统一接口**: 所有日志通过统一接口记录
- **自动轮转**: 基于文件大小和时间自动轮转
- **分类存储**: 不同类型日志存储在不同文件
- **结构化日志**: 支持JSON格式的结构化日志
- **异步写入**: 高性能异步日志写入
- **本地分析**: 内置日志分析和监控工具

### 📁 日志文件分类

| 文件 | 用途 | 轮转大小 | 保留时间 |
|------|------|----------|----------|
| `app.log` | 应用主日志 | 10MB | 30天 |
| `error.log` | 错误日志 | 5MB | 60天 |
| `access.log` | 访问日志 | 50MB | 7天 |
| `security.log` | 安全日志 | 5MB | 90天 |
| `database.log` | 数据库日志 | 20MB | 14天 |
| `tasks.log` | 任务日志 | 10MB | 30天 |
| `structured.log` | 结构化日志 | 10MB | 7天 |

## 快速开始

### 1. 基础使用

```python
from app.utils.loguru_logging_system import *

# 基础日志记录
log_info("用户登录成功")
log_warning("缓存即将过期")
log_error("数据库连接失败")
log_debug("调试信息")
log_critical("系统严重错误")
```

### 2. 带上下文的日志

```python
# 带额外信息
log_info("用户操作", user_id=123, action="login", ip="192.168.1.1")
log_error("API调用失败", endpoint="/api/users", status_code=500, error=str(e))
```

### 3. 分类日志

```python
# 访问日志
log_access("API请求", method="GET", endpoint="/api/users", status_code=200)

# 安全日志
log_security("登录失败", user_id=123, ip="192.168.1.1", reason="invalid_password")

# 数据库日志
log_database("查询执行", query="SELECT * FROM users", duration=0.5, rows=100)

# 任务日志
log_task("同步完成", task_id=1, records=100, duration=30.5)
```

### 4. 结构化日志

```python
# 结构化事件日志
log_structured("user_action", {
    "user_id": 123,
    "action": "login",
    "timestamp": "2024-01-01T00:00:00Z",
    "ip_address": "192.168.1.1",
    "success": True
})
```

### 5. 装饰器使用

```python
from app.utils.loguru_logging_system import log_function_call, log_database_operation

@log_function_call
def my_function():
    """这个函数的调用会被自动记录"""
    pass

@log_database_operation("SELECT")
def query_database():
    """数据库操作会被自动记录"""
    pass
```

## 配置

### 环境变量配置

```bash
# 日志级别
export LOG_LEVEL=INFO

# 日志目录
export LOG_DIR=userdata/logs

# 最大文件大小
export LOG_MAX_FILE_SIZE=10MB

# 日志保留天数
export LOG_RETENTION_DAYS=30

# 是否异步写入
export LOG_ENQUEUE=true

# 是否包含堆栈跟踪
export LOG_BACKTRACE=true
```

### 配置文件

```python
# app/utils/logging_config.py
from app.utils.logging_config import get_logging_config

config = get_logging_config()
print(f"日志级别: {config.level}")
print(f"日志目录: {config.log_dir}")
```

## 日志分析

### 1. 基础分析

```python
from app.utils.log_analyzer import analyze_logs, get_error_summary

# 分析应用日志
stats = analyze_logs("app", days=7)
print(f"总日志数: {stats.total_logs}")
print(f"错误数: {stats.error_count}")

# 获取错误摘要
error_summary = get_error_summary(days=1)
print(f"今日错误: {error_summary['error_count']}")
```

### 2. 性能监控

```python
from app.utils.log_analyzer import get_performance_metrics

# 获取性能指标
performance = get_performance_metrics(days=1)
print(f"总请求数: {performance['total_requests']}")
print(f"平均每小时请求数: {performance['avg_requests_per_hour']}")
```

### 3. 健康检查

```python
from app.utils.log_analyzer import get_health_status, check_alerts

# 获取系统健康状态
health = get_health_status()
print(f"健康状态: {health['status']}")
print(f"健康分数: {health['health_score']}")

# 检查告警
alerts = check_alerts()
for alert in alerts:
    print(f"告警: {alert['message']}")
```

## 迁移指南

### 从旧日志系统迁移

1. **运行迁移脚本**:
```bash
python scripts/migrate_to_loguru.py
```

2. **更新导入语句**:
```python
# 旧方式
from app.utils.enhanced_logger import enhanced_logger
enhanced_logger.info("消息")

# 新方式
from app.utils.loguru_logging_system import log_info
log_info("消息")
```

3. **更新日志调用**:
```python
# 旧方式
logger.info("消息")
enhanced_logger.info("消息", module="auth")

# 新方式
log_info("消息")
log_info("消息", module="auth")
```

## 最佳实践

### 1. 日志级别使用

- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息，如用户操作、系统状态
- **WARNING**: 警告信息，如性能问题、配置问题
- **ERROR**: 错误信息，如异常、失败操作
- **CRITICAL**: 严重错误，如系统崩溃、安全事件

### 2. 结构化日志

```python
# 好的做法
log_structured("user_login", {
    "user_id": 123,
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "success": True,
    "duration": 0.5
})

# 避免的做法
log_info(f"用户 {user_id} 从 {ip} 登录成功")
```

### 3. 异常处理

```python
try:
    # 业务逻辑
    result = risky_operation()
except Exception as e:
    # 记录异常
    log_error("操作失败", exception=e, context={"operation": "risky_operation"})
    raise
```

### 4. 性能考虑

```python
# 使用异步写入（默认启用）
log_info("消息")  # 异步写入，不阻塞主线程

# 避免在循环中记录大量日志
for item in large_list:
    # 避免这样做
    log_debug(f"处理项目: {item}")

    # 更好的做法
    if should_log:
        log_debug(f"处理项目: {item}")
```

## 故障排除

### 1. 日志文件过大

```bash
# 检查日志文件大小
ls -lh userdata/logs/

# 手动清理旧日志
find userdata/logs/ -name "*.log.*" -mtime +30 -delete
```

### 2. 日志丢失

```python
# 检查日志配置
from app.utils.logging_config import get_logging_config
config = get_logging_config()
print(f"日志目录: {config.log_dir}")
print(f"日志级别: {config.level}")
```

### 3. 性能问题

```python
# 检查是否启用异步写入
from app.utils.logging_config import get_logging_config
config = get_logging_config()
print(f"异步写入: {config.enqueue}")
```

## 示例代码

查看完整的使用示例：

```bash
python examples/loguru_usage_example.py
```

## 总结

新的Loguru日志系统提供了：

- ✅ **统一的日志接口**
- ✅ **自动日志轮转**
- ✅ **分类日志存储**
- ✅ **结构化日志支持**
- ✅ **本地日志分析**
- ✅ **高性能异步写入**
- ✅ **完整的监控功能**

通过这个系统，您可以更好地监控应用状态、分析用户行为、排查问题，并提高系统的可维护性。
