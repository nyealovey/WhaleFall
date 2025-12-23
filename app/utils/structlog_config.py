"""WhaleFall 项目的结构化日志配置与辅助函数."""

from __future__ import annotations

import atexit
import sys
from contextlib import suppress
from functools import wraps
from typing import TYPE_CHECKING, ParamSpec, cast

import structlog
from flask import Flask, current_app, g, has_request_context, jsonify
from flask_login import current_user

from app.constants.system_constants import ErrorSeverity
from app.errors import map_exception_to_status
from app.settings import APP_VERSION
from app.types import ContextDict, JsonValue, LoggerExtra, StructlogEventDict
from app.utils.logging.context_vars import request_id_var, user_id_var
from app.utils.logging.error_adapter import (
    ErrorContext,
    ErrorMetadata,
    build_public_context,
    derive_error_metadata,
    get_error_suggestions,
)
from app.utils.logging.handlers import DatabaseLogHandler, DebugFilter
from app.utils.logging.queue_worker import LogQueueWorker

if TYPE_CHECKING:
    from collections.abc import Callable

    from flask.typing import ResponseReturnValue
    from structlog.typing import BindableLogger, Processor

P = ParamSpec("P")
LogField = JsonValue | ContextDict | LoggerExtra
ErrorPayload = dict[str, LogField]
ERROR_HANDLER_EXCEPTIONS: tuple[type[Exception], ...] = (Exception,)


class StructlogConfig:
    """structlog 配置核心类.

    负责配置和管理 structlog 日志系统,包括处理器、过滤器和工作线程.
    支持数据库日志持久化、异步批量写入和调试日志过滤.

    Attributes:
        handler: 数据库日志处理器.
        debug_filter: 调试日志过滤器.
        worker: 日志队列工作线程.
        configured: 是否已配置标志.

    Example:
        >>> config = StructlogConfig()
        >>> config.configure(app)
        >>> logger = get_logger('my_module')

    """

    def __init__(self) -> None:
        self.handler = DatabaseLogHandler()
        self.debug_filter = DebugFilter(enabled=False)
        self.worker: LogQueueWorker | None = None
        self.configured = False

    def configure(self, app: Flask | None = None) -> None:
        """初始化 structlog 处理器(幂等).

        配置 structlog 的处理器链、上下文管理和日志工厂.
        可以多次调用,只会配置一次.

        Args:
            app: Flask 应用实例,可选.如果提供,将附加应用特定配置.

        Returns:
            None.

        """
        if not self.configured:
            processors = [
                self.debug_filter,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                self._add_request_context,
                self._add_user_context,
                self._add_global_context,
                self.handler,
                self._get_console_renderer(),
                structlog.processors.JSONRenderer(),
            ]
            structlog.configure(
                processors=cast("list[structlog.types.Processor]", processors),
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            self.configured = True

        if app is not None:
            self._attach_app(app)

    def _attach_app(self, app: Flask) -> None:
        """绑定位于 Flask 应用上的队列配置.

        Args:
            app: 当前 Flask 应用.

        Returns:
            None.

        """
        if not self.worker:
            queue_size = int(app.config.get("LOG_QUEUE_SIZE", 1000))
            batch_size = int(app.config.get("LOG_BATCH_SIZE", 100))
            flush_interval = float(app.config.get("LOG_FLUSH_INTERVAL", 3.0))
            self.worker = LogQueueWorker(
                app,
                queue_size=queue_size,
                batch_size=batch_size,
                flush_interval=flush_interval,
            )
            self.handler.set_worker(self.worker)

        enable_debug = bool(app.config.get("ENABLE_DEBUG_LOG", False))
        self.debug_filter.set_enabled(enabled=enable_debug)

    @staticmethod
    def _add_request_context(
        _logger: BindableLogger,
        _method_name: str,
        event_dict: StructlogEventDict,
    ) -> StructlogEventDict:
        """向事件字典写入请求上下文.

        Args:
            logger: 当前 logger 实例.
            method_name: 调用的方法名.
            event_dict: structlog 事件字典.

        Returns:
            包含 request_id/user_id 的事件字典.

        """
        if has_request_context():
            event_dict["request_id"] = request_id_var.get()
            event_dict["user_id"] = user_id_var.get()
        return event_dict

    @staticmethod
    def _add_user_context(
        _logger: BindableLogger,
        _method_name: str,
        event_dict: StructlogEventDict,
    ) -> StructlogEventDict:
        """附加当前用户上下文.

        Args:
            logger: 当前 logger.
            method_name: 日志级别名称.
            event_dict: 事件字典.

        Returns:
            更新后的事件字典.

        """
        with suppress(RuntimeError):
            if current_user and getattr(current_user, "is_authenticated", False):
                event_dict["current_user_id"] = getattr(current_user, "id", None)
                event_dict["current_username"] = getattr(current_user, "username", None)
        return event_dict

    @staticmethod
    def _add_global_context(
        _logger: BindableLogger,
        _method_name: str,
        event_dict: StructlogEventDict,
    ) -> StructlogEventDict:
        """附加环境、版本等全局上下文.

        Args:
            logger: 当前 logger.
            method_name: 日志方法.
            event_dict: 事件字典.

        Returns:
            更新后的事件字典.

        """
        try:
            event_dict["app_name"] = current_app.config["APP_NAME"]
            event_dict["app_version"] = current_app.config["APP_VERSION"]
        except RuntimeError:
            event_dict["app_name"] = "鲸落"
            event_dict["app_version"] = APP_VERSION

        if has_request_context():
            event_dict["environment"] = current_app.config.get("ENV", "development")
            event_dict["host"] = getattr(g, "host", "localhost")

        logger_name = getattr(_logger, "name", "unknown")
        event_dict["logger_name"] = logger_name
        return event_dict

    @staticmethod
    def _get_console_renderer() -> Processor:
        """根据终端能力返回渲染器.

        Returns:
            structlog renderer,用于控制台输出.

        """
        if sys.stdout.isatty():
            return structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(show_locals=True, max_frames=10),
            )
        return structlog.dev.ConsoleRenderer(colors=False)

    def shutdown(self) -> None:
        """关闭日志系统.

        停止日志队列工作线程,刷新所有待处理的日志.
        通常在应用退出时自动调用.

        Returns:
            None. 清理副作用来自 worker 线程.

        """
        if self.worker:
            self.worker.close()
            self.handler.set_worker(None)
            self.worker = None


structlog_config = StructlogConfig()
atexit.register(structlog_config.shutdown)


def get_logger(name: str) -> structlog.BoundLogger:
    """获取结构化日志记录器.

    Args:
        name: 日志记录器名称,通常使用模块名.

    Returns:
        绑定的 structlog 日志记录器实例.

    Example:
        >>> logger = get_logger('my_module')
        >>> logger.info('操作成功', user_id=123)

    """
    structlog_config.configure()
    return structlog.get_logger(name)


def configure_structlog(app: Flask) -> None:
    """配置 structlog 并注册 Flask 钩子.

    Args:
        app: Flask 应用实例.

    Returns:
        None.

    """
    structlog_config.configure(app)

    @app.teardown_appcontext
    def log_teardown_error(exception: BaseException | None) -> None:
        if exception:
            get_logger("app").error("应用请求处理异常", module="system", exception=str(exception))


def should_log_debug() -> bool:
    """检查是否应该记录调试日志.

    Returns:
        如果启用调试日志返回 True,否则返回 False.

    """
    try:
        return bool(current_app.config.get("ENABLE_DEBUG_LOG", False))
    except RuntimeError:
        return False


def log_info(message: str, module: str = "app", **kwargs: LogField) -> None:
    """记录信息级别日志.

    Args:
        message: 日志消息.
        module: 模块名称,默认为 'app'.
        **kwargs: 额外的上下文信息.

    Returns:
        None.

    Example:
        >>> log_info('用户登录成功', module='auth', user_id=123)

    """
    logger = get_logger("app")
    logger.info(message, module=module, **kwargs)


def log_warning(
    message: str,
    module: str = "app",
    exception: Exception | None = None,
    **kwargs: LogField,
) -> None:
    """记录警告级别日志.

    Args:
        message: 日志消息.
        module: 模块名称,默认为 'app'.
        exception: 可选的异常对象.
        **kwargs: 额外的上下文信息.

    Returns:
        None.

    Example:
        >>> log_warning('配置项缺失', module='config', key='API_KEY')

    """
    logger = get_logger("app")
    if exception:
        logger.warning(message, module=module, exception=str(exception), **kwargs)
    else:
        logger.warning(message, module=module, **kwargs)


def log_error(
    message: str,
    module: str = "app",
    exception: Exception | None = None,
    **kwargs: LogField,
) -> None:
    """记录错误级别日志.

    Args:
        message: 日志消息.
        module: 模块名称,默认为 'app'.
        exception: 可选的异常对象,会记录堆栈信息.
        **kwargs: 额外的上下文信息.

    Returns:
        None.

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_error('操作失败', module='service', exception=e)

    """
    logger = get_logger("app")
    if exception:
        logger.exception(message, module=module, error=str(exception), **kwargs)
    else:
        logger.error(message, module=module, **kwargs)


def log_critical(
    message: str,
    module: str = "app",
    exception: Exception | None = None,
    **kwargs: LogField,
) -> None:
    """记录严重错误级别日志.

    Args:
        message: 日志消息.
        module: 模块名称,默认为 'app'.
        exception: 可选的异常对象,会记录堆栈信息.
        **kwargs: 额外的上下文信息.

    Returns:
        None.

    Example:
        >>> log_critical('数据库连接失败', module='database', exception=e)

    """
    logger = get_logger("app")
    if exception:
        logger.critical(message, module=module, error=str(exception), **kwargs)
    else:
        logger.critical(message, module=module, **kwargs)


def log_debug(message: str, module: str = "app", **kwargs: LogField) -> None:
    """记录调试级别日志.

    仅在启用调试日志时记录.

    Args:
        message: 日志消息.
        module: 模块名称,默认为 'app'.
        **kwargs: 额外的上下文信息.

    Returns:
        None.

    Example:
        >>> log_debug('查询参数', module='api', params={'page': 1})

    """
    if not should_log_debug():
        return
    logger = get_logger("app")
    logger.debug(message, module=module, **kwargs)


def get_system_logger() -> structlog.BoundLogger:
    """返回系统级 logger.

    Returns:
        structlog.BoundLogger: 绑定系统模块的 logger.

    """
    return get_logger("system")


def get_api_logger() -> structlog.BoundLogger:
    """返回 API 级 logger.

    Returns:
        structlog.BoundLogger: 针对 API 模块的 logger.

    """
    return get_logger("api")


def get_auth_logger() -> structlog.BoundLogger:
    """返回认证模块 logger.

    Returns:
        structlog.BoundLogger: 认证场景使用的 logger.

    """
    return get_logger("auth")


def get_db_logger() -> structlog.BoundLogger:
    """返回数据库操作 logger.

    Returns:
        structlog.BoundLogger: 数据库相关的 logger.

    """
    return get_logger("database")


def get_sync_logger() -> structlog.BoundLogger:
    """返回同步任务 logger.

    Returns:
        structlog.BoundLogger: 同步模块 logger.

    """
    return get_logger("sync")


def get_task_logger() -> structlog.BoundLogger:
    """返回后台任务 logger.

    Returns:
        structlog.BoundLogger: 背景任务 logger.

    """
    return get_logger("task")


def enhanced_error_handler(
    error: Exception,
    context: ErrorContext | None = None,
    *,
    extra: LoggerExtra | None = None,
) -> ErrorPayload:
    """增强的错误处理器.

    将异常转换为结构化的错误响应,包含错误分类、严重级别和建议.

    Args:
        error: 异常对象.
        context: 错误上下文,可选.如果未提供会自动创建.
        extra: 额外的上下文信息,可选.

    Returns:
        结构化的错误响应字典,包含以下字段:
        - error_id: 错误唯一标识
        - category: 错误分类
        - severity: 严重级别
        - message: 错误消息
        - suggestions: 解决建议
        - context: 错误上下文

    Example:
        >>> try:
        ...     operation()
        ... except Exception as e:
        ...     payload = enhanced_error_handler(e, extra={'user_id': 123})
        ...     return jsonify(payload), 500

    """
    context = context or ErrorContext(error)
    context.ensure_request()

    metadata = derive_error_metadata(error)
    public_context = build_public_context(context)

    extra_payload: dict[str, JsonValue] = {}
    if extra:
        extra_payload.update(extra)

    payload: ErrorPayload = {
        "error": True,
        "error_id": context.error_id,
        "category": metadata.category.value,
        "severity": metadata.severity.value,
        "message_code": metadata.message_key,
        "message": metadata.message,
        "timestamp": context.timestamp.isoformat(),
        "recoverable": metadata.recoverable,
        "suggestions": get_error_suggestions(metadata.category),
        "context": public_context,
    }

    if extra_payload:
        payload["extra"] = extra_payload

    _log_enhanced_error(error, metadata, payload)
    return payload


def _log_enhanced_error(error: Exception, metadata: ErrorMetadata, payload: ErrorPayload) -> None:
    """根据严重度输出增强错误.

    Args:
        error: 捕获的异常.
        metadata: 推导出的错误元数据.
        payload: 序列化后的错误响应.

    Returns:
        None.

    """
    log_kwargs: dict[str, JsonValue | ContextDict | LoggerExtra] = {
        "error_id": payload["error_id"],
        "category": payload["category"],
        "severity": payload["severity"],
        "context": payload.get("context"),
    }
    if "extra" in payload:
        log_kwargs["extra"] = payload["extra"]

    message_val = payload.get("message", "")
    message_text = message_val if isinstance(message_val, str) else str(message_val)

    if metadata.severity == ErrorSeverity.CRITICAL:
        log_critical(message_text, module="error_handler", exception=error, **log_kwargs)
    elif metadata.severity == ErrorSeverity.HIGH:
        log_error(message_text, module="error_handler", exception=error, **log_kwargs)
    else:
        log_warning(message_text, module="error_handler", exception=error, **log_kwargs)


def error_handler(func: Callable[P, ResponseReturnValue]) -> Callable[P, ResponseReturnValue]:
    """Flask 视图装饰器,统一捕获异常并输出结构化日志.

    Args:
        func: 原始视图函数.

    Returns:
        包含 try/except 的包装函数.

    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
        try:
            return func(*args, **kwargs)
        except ERROR_HANDLER_EXCEPTIONS as error:
            context = ErrorContext(error)
            payload = enhanced_error_handler(error, context)
            status_code = map_exception_to_status(error, default=500)
            return jsonify(payload), status_code

    return wrapper


__all__ = [
    "ErrorContext",
    "ErrorMetadata",
    "configure_structlog",
    "enhanced_error_handler",
    "error_handler",
    "get_api_logger",
    "get_auth_logger",
    "get_db_logger",
    "get_logger",
    "get_sync_logger",
    "get_system_logger",
    "get_task_logger",
    "log_critical",
    "log_debug",
    "log_error",
    "log_info",
    "log_warning",
    "should_log_debug",
]
