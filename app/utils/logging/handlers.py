"""结构化日志处理器:负责将事件标准化并交由数据库 worker 写入."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from flask import g, has_request_context
from flask_login import current_user

from app.constants.system_constants import LogLevel
from app.utils.logging.context_vars import request_id_var, user_id_var
from app.utils.logging.queue_worker import LogQueueWorker
from app.utils.time_utils import UTC_TZ, time_utils

SYSTEM_FIELDS = {"level", "module", "event", "timestamp", "exception", "logger", "logger_name"}
_logger = structlog.get_logger(__name__)


class DebugFilter:
    """根据配置决定是否丢弃 DEBUG 日志的处理器.

    Attributes:
        enabled: 是否启用 DEBUG 日志.

    """

    def __init__(self, *, enabled: bool = False) -> None:
        """初始化 DEBUG 过滤器.

        Args:
            enabled: 是否启用 DEBUG 日志,默认为 False.

        """
        self.enabled = enabled

    def set_enabled(self, *, enabled: bool) -> None:
        """设置是否启用 DEBUG 日志.

        Args:
            enabled: 是否启用 DEBUG 日志.

        Returns:
            None.

        """
        self.enabled = enabled

    def __call__(self, logger: structlog.BoundLogger, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        """处理日志事件,根据配置决定是否丢弃 DEBUG 日志.

        Args:
            logger: structlog 绑定的日志记录器.
            method_name: 日志方法名称.
            event_dict: 日志事件字典.

        Returns:
            处理后的事件字典.

        Raises:
            structlog.DropEvent: 当 DEBUG 日志未启用时抛出,丢弃该日志.

        """
        level = str(event_dict.get("level", "INFO")).upper()
        if level == "DEBUG" and not self.enabled:
            raise structlog.DropEvent
        return event_dict


class DatabaseLogHandler:
    """将日志事件入队,由后台线程统一写入数据库的处理器.

    Attributes:
        worker: 日志队列工作线程实例.

    """

    def __init__(self, worker: LogQueueWorker | None = None) -> None:
        """初始化数据库日志处理器.

        Args:
            worker: 日志队列工作线程实例,可选.

        """
        self.worker = worker

    def set_worker(self, worker: LogQueueWorker | None) -> None:
        """设置日志队列工作线程.

        Args:
            worker: 日志队列工作线程实例.

        Returns:
            None.

        """
        self.worker = worker

    def __call__(self, logger: structlog.BoundLogger, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        """处理日志事件,将其入队等待写入数据库.

        Args:
            logger: structlog 绑定的日志记录器.
            method_name: 日志方法名称.
            event_dict: 日志事件字典.

        Returns:
            处理后的事件字典.

        """
        if not self.worker:
            return event_dict

        log_entry = _build_log_entry(event_dict)
        if log_entry:
            self.worker.enqueue(log_entry)
        return event_dict


def _build_log_entry(event_dict: dict[str, Any]) -> dict[str, Any] | None:
    """把 structlog 事件转换为 UnifiedLog 可用的字段字典.

    Args:
        event_dict: structlog 事件字典.

    Returns:
        包含日志字段的字典,如果是 DEBUG 级别则返回 None.

    """
    if not isinstance(event_dict, dict):
        message = str(event_dict)
        return {
            "level": LogLevel.INFO,
            "module": "app",
            "message": message,
            "traceback": None,
            "context": {},
            "timestamp": time_utils.now(),
        }

    level_str = str(event_dict.get("level", "INFO")).upper()
    try:
        level = LogLevel(level_str)
    except ValueError:
        level = LogLevel.INFO

    if level == LogLevel.DEBUG:
        return None

    module = event_dict.get("module") or _extract_module_from_logger(event_dict.get("logger")) or "app"
    message = event_dict.get("event") or event_dict.get("message") or ""

    timestamp = event_dict.get("timestamp", time_utils.now())
    if isinstance(timestamp, str):
        try:
            timestamp = time_utils.to_utc(timestamp)
        except Exception:
            timestamp = time_utils.now()
    if timestamp is None:
        timestamp = time_utils.now()
    if isinstance(timestamp, datetime) and timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC_TZ)

    traceback = str(event_dict["exception"]) if event_dict.get("exception") else None
    context = _build_context(event_dict)

    return {
        "timestamp": timestamp,
        "level": level,
        "module": module,
        "message": message,
        "traceback": traceback,
        "context": context,
    }


def _extract_module_from_logger(logger_name: str | None) -> str | None:
    """从日志记录器名称中提取模块名.

    Args:
        logger_name: 日志记录器名称.

    Returns:
        提取的模块名,如果无法提取则返回 None.

    """
    if not logger_name:
        return None
    if "." in logger_name:
        return logger_name.split(".")[-1]
    return logger_name


def _build_context(event_dict: dict[str, Any]) -> dict[str, Any]:
    """构建日志上下文信息.

    从事件字典和请求上下文中提取相关信息,包括请求 ID、用户信息、
    URL、HTTP 方法等,并过滤掉系统字段.

    Args:
        event_dict: structlog 事件字典.

    Returns:
        包含上下文信息的字典.

    """
    context: dict[str, Any] = {}

    if has_request_context():
        context.update(
            {
                "request_id": request_id_var.get(),
                "user_id": user_id_var.get(),
                "url": getattr(g, "url", None),
                "method": getattr(g, "method", None),
                "ip_address": getattr(g, "ip_address", None),
                "user_agent": getattr(g, "user_agent", None),
            },
        )

    try:
        if current_user and hasattr(current_user, "id"):
            context["current_user_id"] = getattr(current_user, "id", None)
            context["current_username"] = getattr(current_user, "username", None)
            context["current_user_role"] = getattr(current_user, "role", None)
            is_admin = getattr(current_user, "is_admin", None)
            if callable(is_admin):
                context["is_admin"] = is_admin()
            else:
                context["is_admin"] = bool(is_admin)
    except Exception as exc:
        _logger.warning("logging_handler_extract_user_failed", error=str(exc))

    for key, value in event_dict.items():
        if key in SYSTEM_FIELDS or value is None:
            continue
        if isinstance(value, datetime):
            context[key] = value.isoformat()
        elif hasattr(value, "to_dict"):
            try:
                context[key] = value.to_dict()
            except Exception:
                context[key] = str(value)
        else:
            context[key] = value

    return context


__all__ = ["SYSTEM_FIELDS", "DatabaseLogHandler", "DebugFilter"]
