# Structlog 控制台输出和上下文绑定功能

## 概述

泰摸鱼吧的统一日志系统现在支持美化的控制台输出和强大的上下文绑定功能，让日志更加易读和便于调试。

## 🎨 美化的控制台输出

### 特性

- **彩色高亮**: 不同日志级别使用不同颜色（DEBUG=绿色，INFO=蓝色，WARNING=黄色，ERROR=红色）
- **结构化显示**: 日志以易读的格式显示，包含时间戳、级别、消息和上下文信息
- **自动检测**: 自动检测是否在终端环境中，在终端中使用彩色输出，在非终端环境中使用简单文本
- **异常追踪**: 支持详细的异常堆栈信息显示

### 示例输出

```bash
# 在终端中的彩色输出
2025-09-13T06:32:29.738414Z [warning] 这是一条警告日志 [test] app_name=泰摸鱼吧 app_version=4.0.0 module=test warning_type=rate_limit

2025-09-13T06:32:29.740067Z [error] 这是一条错误日志 [test] app_name=泰摸鱼吧 app_version=4.0.0 error_code=E001 module=test
```

## 🔗 上下文绑定功能

### 全局上下文绑定

```python
from app.utils.structlog_config import bind_context, clear_context, get_context

# 绑定全局上下文变量
bind_context(
    operation_id="op_001",
    session_id="sess_123456",
    feature="user_management",
    environment="development"
)

# 所有后续的日志都会自动包含这些上下文
logger = get_logger("my_module")
logger.info("用户操作", module="my_module", user_id=123)
# 输出会包含: operation_id, session_id, feature, environment

# 清除全局上下文
clear_context()

# 获取当前上下文
current_context = get_context()
```

### 临时上下文绑定

```python
from app.utils.structlog_config import LogContext

# 使用上下文管理器临时绑定上下文
with LogContext(transaction_id="tx_789", step="validation"):
    logger.info("验证用户输入", module="validation")
    # 这条日志会包含 transaction_id 和 step

    with LogContext(data_type="email"):
        logger.debug("检查邮箱格式", module="validation")
        # 这条日志会包含 transaction_id, step 和 data_type

    logger.info("验证完成", module="validation")
    # 这条日志只包含 transaction_id 和 step（data_type 已被清除）

# 上下文管理器退出后，所有临时上下文都被清除
logger.info("操作完成", module="my_module")
# 这条日志不包含任何临时上下文
```

### 装饰器上下文绑定

```python
from app.utils.structlog_config import with_log_context

@with_log_context(service="user_service", version="1.2.0")
def create_user(username: str, email: str):
    """创建用户"""
    logger = get_logger("user_service")
    logger.info("开始创建用户", module="user_service", username=username, email=email)
    # 这条日志会自动包含 service="user_service" 和 version="1.2.0"

    # 处理逻辑...

    logger.info("用户创建成功", module="user_service", user_id=123)
    # 这条日志也会包含相同的上下文
    return {"success": True, "username": username}

# 调用函数
result = create_user("john_doe", "john@example.com")
```

### 请求上下文绑定

```python
from app.utils.structlog_config import bind_request_context, clear_request_context

# 在请求开始时绑定请求上下文
bind_request_context(request_id="req_001", user_id=789)

logger = get_logger("request")
logger.info("处理HTTP请求", module="request", method="POST", path="/api/users")
# 这条日志会自动包含 request_id 和 user_id

# 在请求结束时清除请求上下文
clear_request_context()
```

## 🐛 DEBUG 日志控制

### 动态控制

```python
from app.utils.structlog_config import set_debug_logging_enabled, log_debug

# 启用DEBUG日志
set_debug_logging_enabled(True)
log_debug("这是DEBUG日志", module="my_module", detail="详细调试信息")

# 禁用DEBUG日志
set_debug_logging_enabled(False)
log_debug("这条DEBUG日志不会显示", module="my_module")
```

### 在Web界面中控制

访问 `http://localhost:5001/logs` 页面，点击"DEBUG开关"按钮可以动态启用/禁用DEBUG日志。

## 📊 自动上下文信息

系统会自动为所有日志添加以下上下文信息：

- `app_name`: 应用名称（"泰摸鱼吧"）
- `app_version`: 应用版本（"4.0.0"）
- `environment`: 环境（"development"）
- `host`: 主机名
- `logger_name`: 日志记录器名称
- `request_id`: 请求ID（在请求上下文中）
- `user_id`: 用户ID（在请求上下文中）
- `current_user_id`: 当前用户ID
- `current_username`: 当前用户名

## 🚀 使用示例

### 基本使用

```python
from app.utils.structlog_config import get_logger, log_info, log_error

# 获取日志记录器
logger = get_logger("my_module")

# 记录日志
logger.info("操作成功", module="my_module", user_id=123, operation="create")
logger.error("操作失败", module="my_module", error="Permission denied")

# 使用便捷函数
log_info("用户登录", module="auth", username="admin")
log_error("登录失败", module="auth", username="admin", reason="Invalid password")
```

### 高级使用

```python
from app.utils.structlog_config import (
    get_logger, bind_context, LogContext, with_log_context
)

# 绑定全局上下文
bind_context(operation_id="batch_001", batch_size=1000)

@with_log_context(service="data_processor", version="2.0.0")
def process_data(data_list):
    """处理数据"""
    logger = get_logger("data_processor")

    logger.info("开始处理数据", module="data_processor", total_count=len(data_list))

    for i, item in enumerate(data_list):
        with LogContext(item_id=item["id"], step=f"processing_{i}"):
            logger.debug("处理数据项", module="data_processor", item_type=item["type"])

            # 处理逻辑...

            logger.info("数据项处理完成", module="data_processor", result="success")

    logger.info("批量处理完成", module="data_processor")
```

## 🔧 配置说明

### 控制台渲染器配置

系统会根据运行环境自动选择合适的渲染器：

- **终端环境**: 使用彩色 `ConsoleRenderer`，支持颜色高亮和异常追踪
- **非终端环境**: 使用简单的 `ConsoleRenderer`，纯文本输出

### 处理器链

日志处理器的执行顺序：

1. 添加时间戳
2. 添加日志级别
3. 添加堆栈追踪
4. 添加异常信息
5. 添加请求上下文
6. 添加用户上下文
7. 添加全局上下文绑定
8. 数据库处理器（写入数据库）
9. 控制台渲染器（美化输出）
10. JSON渲染器（文件输出）

## 📝 最佳实践

### 1. 合理使用上下文绑定

```python
# ✅ 好的做法：绑定相关的上下文
with LogContext(operation="user_creation", user_id=123):
    logger.info("开始创建用户", module="user_service")
    # 所有相关日志都会包含 operation 和 user_id

# ❌ 避免：绑定过多不相关的上下文
bind_context(
    operation="user_creation",
    weather="sunny",  # 不相关的信息
    random_number=42  # 不相关的信息
)
```

### 2. 使用有意义的模块名

```python
# ✅ 好的做法：使用描述性的模块名
logger = get_logger("user_authentication")
logger.info("用户登录成功", module="user_authentication")

# ❌ 避免：使用模糊的模块名
logger = get_logger("app")
logger.info("操作成功", module="app")
```

### 3. 合理使用DEBUG日志

```python
# ✅ 好的做法：DEBUG日志包含有用的调试信息
log_debug("数据库查询执行", module="database", query="SELECT * FROM users", duration="0.05s")

# ❌ 避免：DEBUG日志信息不足
log_debug("查询完成", module="database")
```

### 4. 使用上下文管理器管理临时上下文

```python
# ✅ 好的做法：使用上下文管理器
with LogContext(step="validation"):
    logger.info("验证开始", module="validation")
    # 验证逻辑...
    logger.info("验证完成", module="validation")

# ❌ 避免：手动管理上下文
bind_context(step="validation")
logger.info("验证开始", module="validation")
# 验证逻辑...
clear_context()  # 容易忘记清除
```

## 🧪 测试和演示

运行演示脚本查看功能效果：

```bash
# 运行基本测试
uv run python test_console_logging.py

# 运行完整演示
uv run python examples/structlog_console_demo.py
```

## 🔍 故障排除

### 问题1：控制台输出没有颜色

**原因**: 可能不在终端环境中运行，或者终端不支持颜色。

**解决方案**: 系统会自动检测环境，在非终端环境中使用纯文本输出。

### 问题2：上下文信息没有显示

**原因**: 可能没有正确绑定上下文，或者上下文被意外清除。

**解决方案**: 检查上下文绑定代码，确保在正确的时机绑定和清除上下文。

### 问题3：DEBUG日志不显示

**原因**: DEBUG日志可能被禁用。

**解决方案**: 使用 `set_debug_logging_enabled(True)` 启用DEBUG日志，或在Web界面中点击DEBUG开关。

## 📚 相关文档

- [统一日志系统迁移指南](UNIFIED_LOGGING_MIGRATION_GUIDE.md)
- [日志系统架构设计](LOGURU_LOGGING_SYSTEM.md)
- [日志迁移总结](LOG_MIGRATION_SUMMARY.md)
