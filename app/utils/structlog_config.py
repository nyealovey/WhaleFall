"""TaifishingV4 项目的结构化日志配置与辅助函数。"""

from __future__ import annotations

import atexit
import logging
import sys
from typing import Any, Callable, Mapping

import structlog
from flask import current_app, g, has_request_context
from flask_login import current_user
from app.constants.system_constants import ErrorSeverity
from app.errors import map_exception_to_status
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
from app.utils.time_utils import time_utils


class StructlogConfig:
    """structlog 配置核心类。"""

    def __init__(self) -> None:
        self.handler = DatabaseLogHandler()
        self.debug_filter = DebugFilter(enabled=False)
        self.worker: LogQueueWorker | None = None
        self.configured = False

    def configure(self, app=None):  # noqa: ANN001
        """初始化 structlog 处理器（幂等）。"""
        if not self.configured:
            structlog.configure(
                processors=[
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
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            self.configured = True

        if app is not None:
            self._attach_app(app)

    def _attach_app(self, app):  # noqa: ANN001
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
        self.debug_filter.set_enabled(enable_debug)

    def _add_request_context(self, logger, method_name, event_dict):  # noqa: ANN001
        if has_request_context():
            event_dict["request_id"] = request_id_var.get()
            event_dict["user_id"] = user_id_var.get()
        return event_dict

    def _add_user_context(self, logger, method_name, event_dict):  # noqa: ANN001
        try:
            if current_user and getattr(current_user, "is_authenticated", False):
                event_dict["current_user_id"] = getattr(current_user, "id", None)
                event_dict["current_username"] = getattr(current_user, "username", None)
        except Exception:  # noqa: BLE001
            pass
        return event_dict

    def _add_global_context(self, logger, method_name, event_dict):  # noqa: ANN001
        event_dict["app_name"] = "鲸落"
        try:
            event_dict["app_version"] = getattr(current_app.config, "APP_VERSION", "unknown")
        except RuntimeError:
            event_dict["app_version"] = "unknown"

        if has_request_context():
            event_dict["environment"] = current_app.config.get("ENV", "development")
            event_dict["host"] = getattr(g, "host", "localhost")

        logger_name = getattr(logger, "name", "unknown")
        event_dict["logger_name"] = logger_name
        return event_dict

    def _get_console_renderer(self):
        if sys.stdout.isatty():
            return structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(show_locals=True, max_frames=10),
            )
        return structlog.dev.ConsoleRenderer(colors=False)

    def shutdown(self) -> None:
        if self.worker:
            self.worker.shutdown()
            self.handler.set_worker(None)
            self.worker = None


structlog_config = StructlogConfig()
atexit.register(structlog_config.shutdown)


def get_logger(name: str) -> structlog.BoundLogger:
    structlog_config.configure()
    return structlog.get_logger(name)


def configure_structlog(app):  # noqa: ANN001
    structlog_config.configure(app)

    @app.teardown_appcontext
    def log_teardown_error(exception):  # noqa: ANN001
        if exception:
            get_logger("app").error("Application error", module="system", exception=str(exception))


def should_log_debug() -> bool:
    try:
        return bool(current_app.config.get("ENABLE_DEBUG_LOG", False))
    except RuntimeError:
        return False


def log_info(message: str, module: str = "app", **kwargs):
    logger = get_logger("app")
    logger.info(message, module=module, **kwargs)


def log_warning(message: str, module: str = "app", exception: Exception | None = None, **kwargs):
    logger = get_logger("app")
    if exception:
        logger.warning(message, module=module, exception=str(exception), **kwargs)
    else:
        logger.warning(message, module=module, **kwargs)


def log_error(message: str, module: str = "app", exception: Exception | None = None, **kwargs):
    logger = get_logger("app")
    if exception:
        logger.error(message, module=module, error=str(exception), **kwargs, exc_info=True)
    else:
        logger.error(message, module=module, **kwargs)


def log_critical(message: str, module: str = "app", exception: Exception | None = None, **kwargs):
    logger = get_logger("app")
    if exception:
        logger.critical(message, module=module, error=str(exception), **kwargs, exc_info=True)
    else:
        logger.critical(message, module=module, **kwargs)


def log_debug(message: str, module: str = "app", **kwargs):
    if not should_log_debug():
        return
    logger = get_logger("app")
    logger.debug(message, module=module, **kwargs)


def get_system_logger() -> structlog.BoundLogger:
    return get_logger("system")


def get_api_logger() -> structlog.BoundLogger:
    return get_logger("api")


def get_auth_logger() -> structlog.BoundLogger:
    return get_logger("auth")


def get_db_logger() -> structlog.BoundLogger:
    return get_logger("database")


def get_sync_logger() -> structlog.BoundLogger:
    return get_logger("sync")


def get_task_logger() -> structlog.BoundLogger:
    return get_logger("task")


def enhanced_error_handler(
    error: Exception,
    context: ErrorContext | None = None,
    *,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or ErrorContext(error)
    context.ensure_request()

    metadata = derive_error_metadata(error)
    public_context = build_public_context(context)

    extra_payload: dict[str, Any] = {}
    if extra:
        extra_payload.update(extra)

    payload: dict[str, Any] = {
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


def _log_enhanced_error(error: Exception, metadata: ErrorMetadata, payload: dict[str, Any]) -> None:
    log_kwargs = {
        "module": "error_handler",
        "error_id": payload["error_id"],
        "category": payload["category"],
        "severity": payload["severity"],
        "context": payload.get("context"),
    }
    if "extra" in payload:
        log_kwargs["extra"] = payload["extra"]

    if metadata.severity == ErrorSeverity.CRITICAL:
        log_critical(payload["message"], exception=error, **log_kwargs)
    elif metadata.severity == ErrorSeverity.HIGH:
        log_error(payload["message"], exception=error, **log_kwargs)
    else:
        log_warning(payload["message"], exception=error, **log_kwargs)


def error_handler(func: Callable):
    from functools import wraps
    from flask import jsonify

    @wraps(func)
    def wrapper(*args, **kwargs):  # noqa: ANN002, ANN003
        try:
            return func(*args, **kwargs)
        except Exception as error:  # noqa: BLE001
            context = ErrorContext(error)
            payload = enhanced_error_handler(error, context)
            status_code = map_exception_to_status(error, default=500)
            return jsonify(payload), status_code

    return wrapper


__all__ = [
    "ErrorContext",
    "ErrorMetadata",
    "enhanced_error_handler",
    "configure_structlog",
    "get_logger",
    "get_system_logger",
    "get_api_logger",
    "get_auth_logger",
    "get_db_logger",
    "get_sync_logger",
    "get_task_logger",
    "log_info",
    "log_warning",
    "log_error",
    "log_critical",
    "log_debug",
    "error_handler",
    "should_log_debug",
]
