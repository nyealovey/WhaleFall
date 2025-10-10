# TaifishingV4 函数文档

## 📖 文档说明

本文档详细列出了 TaifishingV4 项目中 `app` 目录下（`routes` 目录除外）的核心函数，按照功能模块进行分类，旨在提供清晰的函数功能、参数和返回值说明。

---

## 1. `app/utils/api_response.py`

该模块提供了一致的 API 响应格式，包含成功和失败两种响应类型。

| 函数/方法 | 描述 | 参数 | 返回值 |
|-----------|------|------|----------|
| `APIResponse.success(data, message)` | 创建一个标准的成功 API 响应。 | `data` (Any, optional): 响应数据。<br>`message` (str, optional): 成功消息，默认为 "操作成功"。 | `Response` (JSON): 包含 `success: True` 的响应对象。 |
| `APIResponse.error(message, code, data)` | 创建一个标准的错误 API 响应。 | `message` (str, optional): 错误消息，默认为 "操作失败"。 <br>`code` (int, optional): HTTP 状态码，默认为 400。<br>`data` (Any, optional): 额外的错误数据。 | `Response` (JSON): 包含 `success: False` 和错误信息的响应对象。 |
| `success_response(data, message)` | `APIResponse.success` 的便捷函数。 | 同 `APIResponse.success`。 | `APIResponse` 对象。 |
| `error_response(message, code, data)` | `APIResponse.error` 的便捷函数。 | 同 `APIResponse.error`。 | `APIResponse` 对象。 |

---

## 2. `app/utils/cache_manager.py`

该模块提供了一个通用的缓存管理工具，包括一个 `CacheManager` 类、缓存装饰器和多种缓存管理函数，用于提升应用性能。

### `CacheManager` 类
| 方法 | 描述 | 参数 | 返回值 |
|------|------|------|----------|
| `__init__(cache)` | 初始化缓存管理器。 | `cache` (Cache): Flask-Caching 实例。 | `None` |
| `_generate_key(prefix, *args, **kwargs)` | 根据前缀和参数生成一个唯一的 SHA256 哈希缓存键。 | `prefix` (str): 缓存键前缀。<br>`*args`, `**kwargs`: 函数的参数。 | `str`: 生成的缓存键。 |
| `get(key)` | 从缓存中获取一个值。 | `key` (str): 缓存键。 | `Any | None`: 缓存的值，如果不存在或出错则为 `None`。 |
| `set(key, value, timeout)` | 在缓存中设置一个值。 | `key` (str): 缓存键。<br>`value` (Any): 要缓存的值。<br>`timeout` (int, optional): 超时时间（秒）。 | `bool`: 操作是否成功。 |
| `delete(key)` | 从缓存中删除一个值。 | `key` (str): 缓存键。 | `bool`: 操作是否成功。 |
| `clear()` | 清空所有缓存。 | 无。 | `bool`: 操作是否成功。 |
| `get_or_set(key, func, timeout, *args, **kwargs)` | 获取缓存，若不存在则执行函数、设置缓存并返回结果。 | `key` (str): 缓存键。<br>`func` (Callable): 用于生成值的函数。<br>`timeout` (int, optional): 超时时间。<br>`*args`, `**kwargs`: `func` 的参数。 | `Any`: 缓存的或新生成的值。 |
| `invalidate_pattern(pattern)` | 根据模式删除缓存（需要后端支持，如 Redis）。 | `pattern` (str): 匹配键的模式。 | `int`: 删除的键数量。 |

### 核心函数和装饰器
| 函数/装饰器 | 描述 | 参数 | 返回值 |
|---------------|------|------|----------|
| `init_cache_manager(cache)` | 初始化全局的 `cache_manager` 实例。 | `cache` (Cache): Flask-Caching 实例。 | `None` |
| `@cached(timeout, key_prefix, unless, key_func)` | 一个函数装饰器，用于缓存函数执行结果。 | `timeout` (int): 缓存超时秒数。<br>`key_prefix` (str): 键前缀。<br>`unless` (Callable, optional): 如果返回 `True`，则跳过缓存。<br>`key_func` (Callable, optional): 自定义键生成函数。 | `Callable`: 包装后的函数。 |
| `@cache_invalidate(pattern)` | 一个函数装饰器，在函数执行后根据模式使缓存失效。 | `pattern` (str): 匹配键的模式。 | `Callable`: 包装后的函数。 |

### 便捷缓存装饰器
| 装饰器 | 描述 |
|---------|------|
| `@user_cache(timeout)` | 用于用户相关缓存的预设装饰器。 |
| `@instance_cache(timeout)` | 用于实例相关缓存的预设装饰器。 |
| `@task_cache(timeout)` | 用于任务相关缓存的预设装饰器。 |
| `@dashboard_cache(timeout)` | 用于仪表板相关缓存的预设装饰器。 |
| `@api_cache(timeout)` | 用于 API 结果缓存的预设装饰器。 |

### 缓存管理函数
| 函数 | 描述 |
|------|------|
| `clear_user_cache(user_id)` | 清除指定用户的相关缓存。 |
| `clear_instance_cache(instance_id)` | 清除指定实例的相关缓存。 |
| `clear_task_cache(task_id)` | 清除指定任务的相关缓存。 |
| `clear_dashboard_cache()` | 清除仪表板相关缓存。 |
| `clear_all_cache()` | 清除所有缓存。 |
| `get_cache_stats()` | 获取缓存后端的统计信息。 |
| `warm_up_cache()` | 预热缓存，将常用数据提前加载到缓存中。 |

---

## 3. `app/utils/data_validator.py`

该模块提供了一个 `DataValidator` 类，用于对输入数据进行严格的验证和清理，确保数据的完整性和安全性。

### `DataValidator` 类
| 方法 | 描述 | 参数 | 返回值 |
|------|------|------|----------|
| `validate_instance_data(data)` | 验证单个实例的数据。它会检查所有必填字段，并对名称、数据库类型、主机、端口等进行详细验证。 | `data` (Dict): 包含实例数据的字典。 | `Tuple[bool, Optional[str]]`: 一个元组，包含一个布尔值（表示是否有效）和一条错误信息（如果无效）。 |
| `validate_batch_data(data_list)` | 批量验证数据列表。 | `data_list` (List[Dict]): 包含多个实例数据的列表。 | `Tuple[List[Dict], List[str]]`: 一个元组，包含验证通过的数据列表和错误信息列表。 |
| `sanitize_input(data)` | 清理输入数据，主要通过去除字符串值的首尾空格。 | `data` (Dict): 原始数据字典。 | `Dict`: 清理后的数据字典。 |
| `_validate_name(name)` | 验证实例名称的格式、长度和允许的字符。 | `name` (Any): 实例名称。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `_validate_db_type(db_type)` | 验证数据库类型是否在支持的列表中。 | `db_type` (Any): 数据库类型。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `_validate_host(host)` | 验证主机地址的格式（IP 或域名）和长度。 | `host` (Any): 主机地址。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `_validate_port(port)` | 验证端口号是否为有效范围内的整数。 | `port` (Any): 端口号。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `_validate_database_name(db_name)` | 验证数据库名称的格式和长度。 | `db_name` (Any): 数据库名称。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `_validate_description(description)` | 验证描述信息的长度。 | `description` (Any): 描述信息。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `_validate_credential_id(credential_id)` | 验证凭据 ID 是否为正整数。 | `credential_id` (Any): 凭据 ID。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `_is_valid_host(host)` | 检查给定的字符串是否是有效的 IP 地址或域名。 | `host` (str): 主机字符串。 | `bool`: 如果有效则返回 `True`，否则返回 `False`。 |

---

## 4. `app/utils/decorators.py`

该模块提供了一系列 Flask 装饰器，用于处理认证、授权、数据验证和速率限制等横切关注点。

### 权限和认证装饰器
| 装饰器 | 描述 | 参数 | 返回值 |
|---|---|---|---|
| `@admin_required` | 确保只有管理员角色的用户才能访问被装饰的路由。如果用户未登录或不是管理员，将重定向或返回 401/403 错误。 | `f` (Callable): 被装饰的函数。 | `Callable`: 包装后的函数。 |
| `@scheduler_manage_required` | 确保只有管理员才能管理定时任务。 | `f` (Callable): 被装饰的函数。 | `Callable`: 包装后的函数。 |
| `@scheduler_view_required` | 允许任何已登录的用户查看定时任务的状态。 | `f` (Callable): 被装饰的函数。 | `Callable`: 包装后的函数。 |
| `@login_required` | 确保用户已登录。如果未登录，则重定向到登录页面。 | `f` (Callable): 被装饰的函数。 | `Callable`: 包装后的函数。 |
| `@login_required_json` | 专为 JSON API 设计的登录验证装饰器。如果未登录，返回 401 JSON 错误。 | `f` (Callable): 被装饰的函数。 | `Callable`: 包装后的函数。 |
| `@permission_required(permission)` | 一个通用的权限验证装饰器，检查用户是否具有指定的权限。 | `permission` (str): 所需的权限字符串。 | `Callable`: 包装后的函数。 |
| `@view_required` | 检查用户是否具有 `view` 权限。 | `f` (Callable): 被装饰的函数。 | `Callable`: 包装后的函数。 |
| `@create_required` | 检查用户是否具有 `create` 权限。 | `f` (Callable): 被装饰的函数。 | `Callable`: 包装后的函数。 |
| `@update_required` | 检查用户是否具有 `update` 权限。 | `f` (Callable): 被装饰的函数。 | `Callable`: 包装后的函数。 |
| `@delete_required` | 检查用户是否具有 `delete` 权限。 | `f` (Callable): 被装饰的函数。 | `Callable`: 包装后的函数。 |

### 数据验证和速率限制
| 装饰器 | 描述 | 参数 | 返回值 |
|---|---|---|---|
| `@validate_json(required_fields)` | 验证进入的请求是否为 JSON 格式，并可选择检查是否包含所有必需的字段。 | `required_fields` (List[str], optional): 必需的字段列表。 | `Callable`: 包装后的函数。 |
| `@rate_limit(requests_per_minute)` | （当前为占位符）用于限制用户访问速率的装饰器。 | `requests_per_minute` (int): 每分钟允许的请求数。 | `Callable`: 包装后的函数。 |

### 辅助函数
| 函数 | 描述 | 参数 | 返回值 |
|---|---|---|---|
| `has_permission(user, permission)` | 检查指定用户是否拥有特定权限。管理员拥有所有权限。 | `user` (User): 用户对象。<br>`permission` (str): 权限名称。 | `bool`: 如果用户有权限，则为 `True`。 |

---

## 5. `app/utils/security.py`

该模块提供了一系列安全相关的工具函数，用于输入清理、数据验证和防范常见的安全漏洞。

### 输入清理和验证
| 函数 | 描述 | 参数 | 返回值 |
|---|---|---|---|
| `sanitize_input(value)` | 清理用户输入，通过 HTML 转义和移除危险字符来防止 XSS 攻击。 | `value` (Any): 原始输入值。 | `str`: 清理后的字符串。 |
| `validate_required_fields(data, required_fields)` | 验证给定的数据字典中是否包含所有必需的字段。 | `data` (Dict): 表单数据。<br>`required_fields` (List[str]): 必填字段列表。 | `Optional[str]`: 如果有字段缺失，返回错误信息；否则返回 `None`。 |
| `validate_username(username)` | 验证用户名的格式，包括长度和允许的字符。 | `username` (str): 用户名。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `validate_password(password)` | 验证密码的强度，主要检查长度。 | `password` (str): 密码。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `validate_db_type(db_type)` | 验证数据库类型是否在预定义的支持列表中。 | `db_type` (str): 数据库类型。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `validate_credential_type(credential_type)` | 验证凭据类型是否在预定义的支持列表中。 | `credential_type` (str): 凭据类型。 | `Optional[str]`: 如果验证失败，返回错误信息；否则返回 `None`。 |
| `sanitize_form_data(data)` | 对整个表单数据进行清理，对每个字段值应用 `sanitize_input`。 | `data` (Dict): 原始表单数据。 | `Dict`: 清理后的数据。 |

### 安全漏洞防范
| 函数 | 描述 | 参数 | 返回值 |
|---|---|---|---|
| `check_sql_injection(query)` | 检查给定的字符串是否包含潜在的 SQL 注入模式。 | `query` (str): SQL 查询语句。 | `bool`: 如果检测到风险，返回 `True`；否则返回 `False`。 |
| `generate_csrf_token()` | 生成一个用于 CSRF 保护的安全令牌。 | 无。 | `str`: CSRF 令牌。 |
| `verify_csrf_token(token, session_token)` | 安全地比较提交的 CSRF 令牌和会话中存储的令牌。 | `token` (str): 提交的令牌。<br>`session_token` (str): 会话中的令牌。 | `bool`: 如果令牌匹配，返回 `True`。 |

---

## 6. `app/utils/structlog_config.py`

该模块配置了 `structlog`，提供结构化的、可扩展的日志记录功能，包括异步数据库日志记录、上下文管理和增强的错误处理。

### `SQLAlchemyLogHandler`

- **描述**: `SQLAlchemyLogHandler` 是一个自定义的日志处理器，它继承自 `logging.Handler`，用于将日志记录异步地持久化到数据库中。它使用一个后台线程来批量处理和插入日志，从而避免阻塞主应用程序。
- **方法**:
    - `__init__(self, app, model, batch_size=100, flush_interval=5)`: 初始化处理器，设置 Flask 应用、日志模型、批处理大小和刷新间隔。
    - `build_log_entry(self, record)`: 根据日志记录构建一个日志条目字典。
    - `build_context(self, record)`: 从日志记录中提取上下文信息。
    - `emit(self, record)`: 将日志记录放入一个队列中，由后台线程处理。
    - `_process_queue(self)`: 后台线程的目标函数，定期从队列中获取日志并批量插入数据库。
    - `_flush_logs(self)`: 将累积的日志批量插入数据库。
    - `shutdown(self)`: 安全地关闭后台线程。

### `StructlogConfig`

- **描述**: `StructlogConfig` 类用于配置 `structlog`，包括设置处理器链、上下文变量和渲染器。
- **方法**:
    - `__init__(self, app=None)`: 初始化配置类，可选择性地传入 Flask 应用实例。
    - `configure(self)`: 配置 `structlog` 的主要方法。
    - `_filter_log_level(self, logger, method_name, event_dict)`: 根据日志级别过滤日志。
    - `_add_request_context(self, logger, method_name, event_dict)`: 向日志中添加请求相关的上下文（如 request_id）。
    - `_add_user_context(self, logger, method_name, event_dict)`: 向日志中添加用户相关的上下文（如 user_id）。
    - `_add_global_context(self, logger, method_name, event_dict)`: 向日志中添加全局上下文。
    - `_get_console_renderer(self)`: 获取用于开发环境的控制台渲染器。
    - `_get_handler(self)`: 根据环境（生产或开发）获取适当的日志处理器。

### 日志记录函数

- **`get_logger(name="app")`**:
    - **描述**: 获取一个 `structlog` 日志记录器实例。
    - **参数**:
        - `name` (str): 日志记录器的名称。
    - **返回**: `structlog.BoundLogger`

- **`configure_structlog(app)`**:
    - **描述**: 在 Flask 应用中配置 `structlog`。
    - **参数**:
        - `app` (Flask): Flask 应用实例。

- **`set_debug_logging_enabled(enabled)`**:
    - **描述**: 动态地启用或禁用 DEBUG 级别的日志记录。
    - **参数**:
        - `enabled` (bool): 是否启用 DEBUG 日志。

- **`is_debug_logging_enabled()`**:
    - **描述**: 检查 DEBUG 日志记录是否已启用。
    - **返回**: `bool`

- **`log_info(message, module="app", **kwargs)`**:
    - **描述**: 记录一条信息级别的日志。
- **`log_warning(message, module="app", exception=None, **kwargs)`**:
    - **描述**: 记录一条警告级别的日志。
- **`log_error(message, module="app", exception=None, **kwargs)`**:
    - **描述**: 记录一条错误级别的日志，并可选择性地包含异常信息和堆栈跟踪。
- **`log_critical(message, module="app", exception=None, **kwargs)`**:
    - **描述**: 记录一条严重错误级别的日志。
- **`log_debug(message, module="app", **kwargs)`**:
    - **描述**: 记录一条调试级别的日志（仅在启用时）。

### 专用日志记录器

- **`get_system_logger()`**: 获取用于系统事件的日志记录器。
- **`get_api_logger()`**: 获取用于 API 相关事件的日志记录器。
- **`get_auth_logger()`**: 获取用于认证事件的日志记录器。
- **`get_db_logger()`**: 获取用于数据库操作的日志记录器。
- **`get_sync_logger()`**: 获取用于同步任务的日志记录器。
- **`get_task_logger()`**: 获取用于后台任务的日志记录器。

### 上下文管理

- **`bind_context(**kwargs)`**: 绑定全局上下文变量。
- **`clear_context()`**: 清除全局上下文变量。
- **`get_context()`**: 获取当前的全局上下文。
- **`bind_request_context(request_id, user_id=None)`**: 绑定请求上下文。
- **`clear_request_context()`**: 清除请求上下文。
- **`LogContext(**kwargs)`**: 一个上下文管理器，用于在特定代码块内临时添加日志上下文。
- **`@with_log_context(**context)`**: 一个装饰器，用于为函数自动绑定日志上下文。

### 增强的错误处理

- **`ErrorCategory`**: 一个枚举类，定义了错误的分类（如数据库、验证、认证等）。
- **`ErrorSeverity`**: 一个枚举类，定义了错误的严重程度（如低、中、高、严重）。
- **`ErrorContext`**: 一个类，用于封装关于错误的上下文信息（如错误实例、请求、用户 ID 等）。
- **`enhanced_error_handler(error, context=None)`**:
    - **描述**: 一个增强的错误处理器，它对错误进行分类，记录详细的日志，并生成一个结构化的、用户友好的错误响应。
    - **参数**:
        - `error` (Exception): 发生的异常。
        - `context` (ErrorContext): 错误的上下文。
    - **返回**: `dict` - 包含错误信息的字典。
- **`@error_handler`**: 一个装饰器，它捕获函数中发生的异常，并使用 `enhanced_error_handler` 来处理它们。对于严重错误，它会返回一个 JSON 错误响应。
- **`@error_monitor`**: 一个装饰器，它捕获异常，使用 `enhanced_error_handler` 记录它们，然后重新抛出异常。

---

## 7. `app/utils/time_utils.py`

该模块定义了一个 `TimeUtils` 类，用于处理时区转换、时间格式化和相对时间计算。它还提供了一些向后兼容的函数。

### `TimeUtils` 类

- **描述**: `TimeUtils` 类提供了一套统一的工具，用于处理时区转换、时间格式化和相对时间计算。它支持中国时区（`Asia/Shanghai`）和 UTC 之间的转换，并提供多种时间格式化选项。
- **方法**:
    - `now()`: 获取当前的 UTC 时间。
    - `now_china()`: 获取当前的中国时间。
    - `to_china(dt)`: 将给定的时间（字符串或 `datetime` 对象）转换为中国时区。
    - `to_utc(dt)`: 将给定的时间转换为 UTC 时区。
    - `format_china_time(dt, format_str)`: 将时间格式化为中国时区的字符串。
    - `format_utc_time(dt, format_str)`: 将时间格式化为 UTC 时区的字符串。
    - `get_relative_time(dt)`: 获取相对于当前时间的描述（例如，“5分钟前”）。
    - `is_today(dt)`: 判断给定的时间是否是今天。
    - `get_time_range(hours)`: 获取一个时间范围，从指定的小时数前到现在。
    - `to_json_serializable(dt)`: 将 `datetime` 对象转换为 JSON 可序列化的 ISO 格式字符串。

### 向后兼容的时间函数

- **`now()`**: `time_utils.now()` 的别名。
- **`now_china()`**: `time_utils.now_china()` 的别名。
- **`utc_to_china(dt)`**: `time_utils.to_china(dt)` 的别名。
- **`format_china_time(dt, format_str)`**: `time_utils.format_china_time(dt, format_str)` 的别名。
- **`get_china_time()`**: `time_utils.now_china()` 的别名。
- **`china_to_utc(china_dt)`**: `time_utils.to_utc(china_dt)` 的别名。
- **`get_china_date()`**: 获取当前中国日期的 `date` 对象。
- **`get_china_today()`**: 获取中国时区今天开始的 UTC 时间。
- **`get_china_tomorrow()`**: 获取中国时区明天开始的 UTC 时间。