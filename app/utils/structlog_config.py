"""
泰摸鱼吧 - Structlog 配置
统一日志系统的核心配置和处理器
"""

import logging
import sys
import threading
import time
from contextvars import ContextVar
from datetime import datetime
from queue import Empty, Queue
from typing import Any

import structlog
from flask import current_app, g, has_request_context
from flask_login import current_user

from app import db
from app.models.unified_log import LogLevel, UnifiedLog
from app.utils.time_utils import time_utils

# 请求上下文变量
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)

# 全局日志级别控制
_debug_logging_enabled = False

# 全局上下文绑定
_global_context = {}


class SQLAlchemyLogHandler:
    """SQLAlchemy 日志处理器"""

    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.log_queue = Queue()
        self.batch_buffer: list[dict[str, Any]] = []
        self.last_flush = time.time()
        self._shutdown = False

        # 启动后台线程处理日志
        self._thread = threading.Thread(target=self._process_logs, daemon=True)
        self._thread.start()

    def __call__(self, logger, method_name, event_dict):
        """处理日志事件"""
        if self._shutdown:
            return event_dict

        # 过滤DEBUG级别日志
        level = event_dict.get("level", "INFO")
        level_priority = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

        # 如果级别低于INFO，则丢弃日志
        if level_priority.get(level, 20) < 20:  # INFO级别
            raise structlog.DropEvent()

        # 构建日志条目
        log_entry = self._build_log_entry(event_dict)
        if log_entry:
            # 直接同步写入数据库
            try:
                # 检查是否有应用上下文
                if has_request_context() or current_app:
                    with current_app.app_context():
                        # 确保时间戳是datetime对象，使用东八区时间
                        if isinstance(log_entry.get("timestamp"), str):
                            from datetime import datetime

                            try:
                                log_entry["timestamp"] = datetime.fromisoformat(
                                    log_entry["timestamp"].replace("Z", "+00:00")
                                )
                            except ValueError:
                                log_entry["timestamp"] = time_utils.now()

                        # 创建并保存日志条目
                        unified_log = UnifiedLog.create_log_entry(**log_entry)
                        db.session.add(unified_log)
                        db.session.commit()
                else:
                    # 如果没有应用上下文，跳过数据库写入
                    pass
            except Exception:
                # 使用标准logging避免循环依赖
                import logging

                logging.error("Error writing log to database: {e}")

        return event_dict

    def _build_log_entry(self, event_dict: dict[str, Any]) -> dict[str, Any] | None:
        """构建日志条目"""
        try:
            # 检查event_dict是否为字典
            if not isinstance(event_dict, dict):
                # 如果不是字典，尝试从字符串中提取信息
                if isinstance(event_dict, str):
                    return {
                        "level": LogLevel.INFO,
                        "module": "unknown",
                        "message": event_dict,
                        "context": {},
                        "timestamp": time_utils.now(),
                    }
                return None

            # 提取基本信息
            level_str = event_dict.get("level", "INFO").upper()
            try:
                level = LogLevel(level_str)
            except ValueError:
                level = LogLevel.INFO

            # 获取模块名，优先从logger名称获取
            module = event_dict.get("module", "unknown")
            if not module or module == "unknown":
                # 尝试从logger名称提取模块
                logger_name = event_dict.get("logger", "")
                if logger_name:
                    module = logger_name.split(".")[-1]

            # 获取消息内容
            message = event_dict.get("event", "")
            if not message:
                # 如果没有event字段，尝试其他可能的字段
                message = event_dict.get("message", "")

            # 获取时间戳，确保带时区信息
            timestamp = event_dict.get("timestamp", time_utils.now())
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = time_utils.now()

            # 确保时间戳带时区信息
            if timestamp.tzinfo is None:
                from app.utils.timezone import UTC_TZ

                timestamp = timestamp.replace(tzinfo=UTC_TZ)

            # 提取堆栈追踪
            traceback = None
            if "exception" in event_dict and event_dict["exception"]:
                traceback = str(event_dict["exception"])

            # 构建上下文
            context = self._build_context(event_dict)

            return {
                "timestamp": timestamp,
                "level": level,
                "module": module,
                "message": message,
                "traceback": traceback,
                "context": context,
            }
        except Exception:
            # 避免日志处理本身出错
            # 使用标准logging避免循环依赖
            import logging

            logging.error("Error building log entry: {e}")
            return None

    def _build_context(self, event_dict: dict[str, Any]) -> dict[str, Any]:
        """构建日志上下文"""
        context = {}

        # 添加请求上下文
        if has_request_context():
            context.update(
                {
                    "request_id": request_id_var.get(),
                    "user_id": user_id_var.get(),
                    "url": getattr(g, "url", None),
                    "method": getattr(g, "method", None),
                    "ip_address": getattr(g, "ip_address", None),
                    "user_agent": getattr(g, "user_agent", None),
                }
            )

        # 添加用户信息
        if current_user and hasattr(current_user, "id"):
            context["current_user_id"] = current_user.id
            context["current_username"] = getattr(current_user, "username", None)
            context["current_user_role"] = getattr(current_user, "role", None)
            context["is_admin"] = getattr(current_user, "is_admin", lambda: False)()

        # 添加其他上下文信息（过滤掉系统字段）
        system_fields = ["level", "module", "event", "timestamp", "exception", "logger", "logger_name"]
        for key, value in event_dict.items():
            if key not in system_fields and value is not None:
                # 处理特殊数据类型
                if isinstance(value, datetime):
                    context[key] = value.isoformat()
                elif hasattr(value, "to_dict"):
                    # 如果是模型对象，转换为字典
                    try:
                        context[key] = value.to_dict()
                    except:
                        context[key] = str(value)
                else:
                    context[key] = value

        return context

    def _process_logs(self):
        """后台处理日志队列"""
        while not self._shutdown:
            try:
                # 尝试获取日志条目
                try:
                    log_entry = self.log_queue.get(timeout=1.0)
                    self.batch_buffer.append(log_entry)
                except Empty:
                    pass

                # 检查是否需要刷新
                current_time = time.time()
                should_flush = len(self.batch_buffer) >= self.batch_size or (
                    self.batch_buffer and current_time - self.last_flush >= self.flush_interval
                )

                if should_flush:
                    self._flush_logs()

            except Exception:
                # 使用标准logging避免循环依赖
                import logging

                logging.error("Error processing logs: {e}")
                time.sleep(1)

    def _flush_logs(self):
        """刷新日志到数据库"""
        if not self.batch_buffer:
            return

        try:
            # 创建新的应用上下文
            from flask import current_app

            with current_app.app_context():
                # 批量插入日志
                log_entries = []
                for log_data in self.batch_buffer:
                    # 确保时间戳是datetime对象，使用东八区时间
                    if isinstance(log_data.get("timestamp"), str):
                        from datetime import datetime

                        try:
                            log_data["timestamp"] = datetime.fromisoformat(log_data["timestamp"].replace("Z", "+00:00"))
                        except ValueError:
                            log_data["timestamp"] = time_utils.now()

                        # 确保时间戳带时区信息
                        if log_data["timestamp"].tzinfo is None:
                            from app.utils.timezone import UTC_TZ

                            log_data["timestamp"] = log_data["timestamp"].replace(tzinfo=UTC_TZ)

                    log_entry = UnifiedLog.create_log_entry(**log_data)
                    log_entries.append(log_entry)

                db.session.add_all(log_entries)
                db.session.commit()

                self.batch_buffer.clear()
                self.last_flush = time.time()

        except Exception:
            # 使用标准logging避免循环依赖
            import logging

            logging.error("Error flushing logs to database: {e}")
            try:
                db.session.rollback()
            except:
                pass
            # 清空缓冲区避免重复错误
            self.batch_buffer.clear()

    def shutdown(self):
        """关闭处理器"""
        self._shutdown = True
        # 刷新剩余的日志
        if self.batch_buffer:
            self._flush_logs()
        self._thread.join(timeout=5)


class StructlogConfig:
    """Structlog 配置类"""

    def __init__(self):
        self.handler = None
        self.configured = False

    def configure(self, app=None):
        """配置 structlog"""
        if self.configured:
            return

        # 配置 structlog - 按照官方文档推荐的最佳实践
        structlog.configure(
            processors=[
                # 1. 过滤日志级别（只允许INFO及以上级别）
                self._filter_log_level,
                # 2. 添加时间戳
                structlog.processors.TimeStamper(fmt="iso"),
                # 3. 添加日志级别
                structlog.stdlib.add_log_level,
                # 4. 添加堆栈追踪
                structlog.processors.StackInfoRenderer(),
                # 5. 添加异常信息
                structlog.processors.format_exc_info,
                # 6. 添加请求上下文
                self._add_request_context,
                # 7. 添加用户上下文
                self._add_user_context,
                # 8. 添加全局上下文绑定
                self._add_global_context,
                # 9. 数据库处理器（在JSON渲染之前）
                self._get_handler(),
                # 10. 控制台渲染器（美化输出）
                self._get_console_renderer(),
                # 11. JSON 渲染器（用于文件输出）
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        self.configured = True

    def _filter_log_level(self, logger, method_name, event_dict):
        """过滤日志级别，只允许INFO及以上级别"""
        # 获取日志级别
        level = event_dict.get("level", "INFO")

        # 定义级别优先级
        level_priority = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

        # 如果级别低于INFO，则丢弃日志
        if level_priority.get(level, 20) < 20:  # INFO级别
            # 静默丢弃DEBUG日志，不打印调试信息
            raise structlog.DropEvent()

        return event_dict

    def _add_request_context(self, logger, method_name, event_dict):
        """添加请求上下文"""
        if has_request_context():
            event_dict["request_id"] = request_id_var.get()
            event_dict["user_id"] = user_id_var.get()
        return event_dict

    def _add_user_context(self, logger, method_name, event_dict):
        """添加用户上下文"""
        if current_user and hasattr(current_user, "id"):
            event_dict["current_user_id"] = current_user.id
            event_dict["current_username"] = getattr(current_user, "username", None)
        return event_dict

    def _add_global_context(self, logger, method_name, event_dict):
        """添加全局上下文绑定"""
        # 添加应用信息
        event_dict["app_name"] = "泰摸鱼吧"
        event_dict["app_version"] = "4.0.0"

        # 添加环境信息
        if has_request_context():
            event_dict["environment"] = "development"  # 可以根据实际环境设置
            event_dict["host"] = getattr(g, "host", "localhost")

        # 添加模块信息（从logger名称提取）
        logger_name = logger.name if hasattr(logger, "name") else "unknown"
        event_dict["logger_name"] = logger_name

        # 添加全局上下文变量
        global _global_context
        event_dict.update(_global_context)

        return event_dict

    def _get_console_renderer(self):
        """获取控制台渲染器"""
        # 检查是否在终端环境中
        if sys.stdout.isatty():
            # 在终端中，使用彩色控制台渲染器
            return structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(
                    show_locals=True,
                    max_frames=10,
                ),
            )
        # 非终端环境，使用简单的控制台渲染器
        return structlog.dev.ConsoleRenderer(colors=False)

    def _get_handler(self):
        """获取数据库处理器"""
        if not self.handler:
            self.handler = SQLAlchemyLogHandler()
        return self.handler

    def shutdown(self):
        """关闭配置"""
        if self.handler:
            self.handler.shutdown()


# 全局配置实例
structlog_config = StructlogConfig()


def get_logger(name: str) -> structlog.BoundLogger:
    """获取结构化日志记录器"""
    if not structlog_config.configured:
        structlog_config.configure()

    return structlog.get_logger(name)


def configure_structlog(app):
    """配置应用的结构化日志"""
    structlog_config.configure(app)

    # 注册关闭处理器
    @app.teardown_appcontext
    def shutdown_logging(exception):
        if exception:
            get_logger("app").error("Application error", module="system", exception=str(exception))


def set_debug_logging_enabled(enabled: bool) -> None:
    """设置DEBUG日志开关"""
    global _debug_logging_enabled
    _debug_logging_enabled = enabled

    # 更新所有日志记录器的级别
    if enabled:
        logging.getLogger().setLevel(logging.DEBUG)
        # 更新structlog配置
        structlog.configure(
            processors=[
                # 1. 过滤日志级别（只允许INFO及以上级别）
                structlog_config._filter_log_level,
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog_config._get_handler(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        logging.getLogger().setLevel(logging.INFO)
        # 恢复原始structlog配置
        structlog_config.configure()


def is_debug_logging_enabled() -> bool:
    """检查DEBUG日志是否启用"""
    return _debug_logging_enabled


def should_log_debug() -> bool:
    """检查是否应该记录DEBUG日志"""
    return _debug_logging_enabled


# 便捷函数
def log_info(message: str, module: str = "app", **kwargs):
    """记录信息日志"""
    logger = get_logger("app")
    logger.info(message, module=module, **kwargs)


def log_warning(message: str, module: str = "app", exception: Exception | None = None, **kwargs):
    """记录警告日志"""
    logger = get_logger("app")
    if exception:
        logger.warning(message, module=module, exception=str(exception), **kwargs)
    else:
        logger.warning(message, module=module, **kwargs)


def log_error(message: str, module: str = "app", exception: Exception | None = None, **kwargs):
    """记录错误日志"""
    logger = get_logger("app")
    if exception:
        # 使用 exc_info=True 来触发堆栈追踪
        logger.error(message, module=module, error=str(exception), **kwargs, exc_info=True)
    else:
        logger.error(message, module=module, **kwargs)


def log_critical(message: str, module: str = "app", exception: Exception | None = None, **kwargs):
    """记录严重错误日志"""
    logger = get_logger("app")
    if exception:
        # 使用 exc_info=True 来触发堆栈追踪
        logger.critical(message, module=module, error=str(exception), **kwargs, exc_info=True)
    else:
        logger.critical(message, module=module, **kwargs)


def log_debug(message: str, module: str = "app", **kwargs):
    """记录调试日志"""
    if not should_log_debug():
        return  # 如果DEBUG日志未启用，直接返回
    logger = get_logger("app")
    logger.debug(message, module=module, **kwargs)


# 专门的日志记录器函数
def get_system_logger() -> structlog.BoundLogger:
    """获取系统日志记录器"""
    return get_logger("system")


def get_api_logger() -> structlog.BoundLogger:
    """获取API日志记录器"""
    return get_logger("api")


def get_auth_logger() -> structlog.BoundLogger:
    """获取认证日志记录器"""
    return get_logger("auth")


def get_db_logger() -> structlog.BoundLogger:
    """获取数据库日志记录器"""
    return get_logger("database")


def get_sync_logger() -> structlog.BoundLogger:
    """获取同步日志记录器"""
    return get_logger("sync")


def get_task_logger() -> structlog.BoundLogger:
    """获取任务日志记录器"""
    return get_logger("task")


# 上下文绑定功能
def bind_context(**kwargs) -> None:
    """绑定全局上下文变量"""
    global _global_context
    _global_context.update(kwargs)


def clear_context() -> None:
    """清除全局上下文变量"""
    global _global_context
    _global_context.clear()


def get_context() -> dict[str, Any]:
    """获取当前全局上下文"""
    return _global_context.copy()


def bind_request_context(request_id: str, user_id: int | None = None) -> None:
    """绑定请求上下文"""
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context() -> None:
    """清除请求上下文"""
    request_id_var.set(None)
    user_id_var.set(None)


# 上下文管理器
class LogContext:
    """日志上下文管理器"""

    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_context = {}

    def __enter__(self):
        global _global_context
        self.old_context = _global_context.copy()
        _global_context.update(self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _global_context
        _global_context.clear()
        _global_context.update(self.old_context)


# 装饰器用于自动绑定上下文
def with_log_context(**context):
    """装饰器：为函数自动绑定日志上下文"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            with LogContext(**context):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# 错误处理增强功能
class ErrorCategory:
    """错误分类"""
    DATABASE = "database"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SYSTEM = "system"
    NETWORK = "network"
    UNKNOWN = "unknown"


class ErrorSeverity:
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorContext:
    """错误上下文信息"""
    
    def __init__(self, error: Exception, request=None):
        self.error = error
        self.error_type = type(error).__name__
        self.error_id = f"{int(time.time() * 1000)}-{id(error)}"
        self.timestamp = time_utils.now()
        self.request = request
        self.url = request.url if request else None
        self.user_id = user_id_var.get() if user_id_var.get() else None
        self.request_id = request_id_var.get() if request_id_var.get() else None


def enhanced_error_handler(error: Exception, context: ErrorContext = None) -> dict[str, Any]:
    """增强的错误处理器"""
    if context is None:
        context = ErrorContext(error)
    
    # 分类错误
    error_info = _classify_error(error, context)
    
    # 记录错误日志
    _log_enhanced_error(error, context, error_info)
    
    # 生成用户友好的错误响应
    return _generate_error_response(error, context, error_info)


def _classify_error(error: Exception, context: ErrorContext) -> dict[str, Any]:
    """分类错误"""
    error_type = type(error)
    error_message = str(error)
    
    # 数据库错误
    if "IntegrityError" in error_type.__name__ or "OperationalError" in error_type.__name__:
        if "UNIQUE constraint failed" in error_message:
            return {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "数据已存在，请检查唯一性约束",
                "technical_message": error_message,
            }
        elif "FOREIGN KEY constraint failed" in error_message:
            return {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "外键约束失败，请检查关联数据",
                "technical_message": error_message,
            }
        else:
            return {
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.HIGH,
                "user_message": "数据库操作失败",
                "technical_message": error_message,
            }
    
    # 连接错误
    elif "connection" in error_message.lower() or "timeout" in error_message.lower():
        return {
            "category": ErrorCategory.NETWORK,
            "severity": ErrorSeverity.HIGH,
            "user_message": "网络连接问题，请稍后重试",
            "technical_message": error_message,
        }
    
    # 权限错误
    elif "permission" in error_message.lower() or "access" in error_message.lower():
        return {
            "category": ErrorCategory.AUTHORIZATION,
            "severity": ErrorSeverity.MEDIUM,
            "user_message": "权限不足，请联系管理员",
            "technical_message": error_message,
        }
    
    # 验证错误
    elif "validation" in error_message.lower() or "invalid" in error_message.lower():
        return {
            "category": ErrorCategory.VALIDATION,
            "severity": ErrorSeverity.LOW,
            "user_message": "输入数据验证失败",
            "technical_message": error_message,
        }
    
    # 默认错误
    else:
        return {
            "category": ErrorCategory.UNKNOWN,
            "severity": ErrorSeverity.HIGH,
            "user_message": "系统内部错误",
            "technical_message": error_message,
        }


def _log_enhanced_error(error: Exception, context: ErrorContext, error_info: dict[str, Any]) -> None:
    """记录增强的错误日志"""
    logger = get_logger("error_handler")
    
    # 根据严重程度选择日志级别
    severity = error_info.get("severity", ErrorSeverity.HIGH)
    if severity == ErrorSeverity.CRITICAL:
        log_critical(
            f"严重错误: {error_info.get('user_message', '未知错误')}",
            module="error_handler",
            error_id=context.error_id,
            error_type=context.error_type,
            category=error_info.get("category"),
            severity=severity,
            user_id=context.user_id,
            request_id=context.request_id,
            url=context.url,
            technical_message=error_info.get("technical_message"),
            exception=error,
        )
    elif severity == ErrorSeverity.HIGH:
        log_error(
            f"高级错误: {error_info.get('user_message', '未知错误')}",
            module="error_handler",
            error_id=context.error_id,
            error_type=context.error_type,
            category=error_info.get("category"),
            severity=severity,
            user_id=context.user_id,
            request_id=context.request_id,
            url=context.url,
            technical_message=error_info.get("technical_message"),
            exception=error,
        )
    else:
        log_warning(
            f"错误: {error_info.get('user_message', '未知错误')}",
            module="error_handler",
            error_id=context.error_id,
            error_type=context.error_type,
            category=error_info.get("category"),
            severity=severity,
            user_id=context.user_id,
            request_id=context.request_id,
            url=context.url,
            technical_message=error_info.get("technical_message"),
            exception=error,
        )


def _generate_error_response(error: Exception, context: ErrorContext, error_info: dict[str, Any]) -> dict[str, Any]:
    """生成错误响应"""
    return {
        "error": True,
        "error_id": context.error_id,
        "category": error_info.get("category", ErrorCategory.UNKNOWN),
        "severity": error_info.get("severity", ErrorSeverity.HIGH),
        "message": error_info.get("user_message", "系统内部错误"),
        "timestamp": context.timestamp.isoformat(),
        "recoverable": error_info.get("severity") in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM],
        "suggestions": _get_error_suggestions(error_info.get("category")),
    }


def _get_error_suggestions(category: str) -> list[str]:
    """获取错误建议"""
    suggestions_map = {
        ErrorCategory.DATABASE: ["检查数据库连接", "联系管理员"],
        ErrorCategory.VALIDATION: ["检查输入数据", "查看错误详情"],
        ErrorCategory.AUTHENTICATION: ["重新登录", "检查凭据"],
        ErrorCategory.AUTHORIZATION: ["联系管理员", "检查权限"],
        ErrorCategory.NETWORK: ["检查网络连接", "稍后重试"],
        ErrorCategory.SYSTEM: ["联系管理员", "查看错误日志"],
        ErrorCategory.UNKNOWN: ["联系管理员", "查看错误日志"],
    }
    return suggestions_map.get(category, ["联系管理员", "查看错误日志"])


# 错误处理装饰器
def error_handler(func):
    """错误处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as error:
            context = ErrorContext(error)
            error_response = enhanced_error_handler(error, context)
            
            # 根据错误严重程度决定是否返回错误响应
            if error_response.get("severity") in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
                # 对于严重错误，返回错误响应
                from flask import jsonify
                return jsonify(error_response), 500
            else:
                # 对于轻微错误，记录日志但继续执行
                return func(*args, **kwargs)
    
    return wrapper


def error_monitor(func):
    """错误监控装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as error:
            context = ErrorContext(error)
            enhanced_error_handler(error, context)
            raise  # 重新抛出异常
    
    return wrapper
