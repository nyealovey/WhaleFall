"""Structlog processors/handlers for database logging."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

import structlog
from flask import g, has_request_context
from flask_login import current_user

from app.constants.system_constants import LogLevel
from app.utils.logging.context_vars import request_id_var, user_id_var
from app.utils.time_utils import UTC_TZ, time_utils

SYSTEM_FIELDS = {"level", "module", "event", "timestamp", "exception", "logger", "logger_name"}


class DebugFilter:
    """Processor that drops DEBUG logs unless显式开启."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def __call__(self, logger: structlog.BoundLogger, method_name: str, event_dict: Dict[str, Any]):
        level = str(event_dict.get("level", "INFO")).upper()
        if level == "DEBUG" and not self.enabled:
            raise structlog.DropEvent
        return event_dict


class DatabaseLogHandler:
    """Structlog processor that enqueues DB log entries via a worker."""

    def __init__(self, worker: Any | None = None) -> None:  # noqa: ANN401 - worker is queue worker instance
        self.worker = worker

    def set_worker(self, worker: Any | None) -> None:  # noqa: ANN401
        self.worker = worker

    def __call__(self, logger: structlog.BoundLogger, method_name: str, event_dict: Dict[str, Any]):
        if not self.worker:
            return event_dict

        log_entry = _build_log_entry(event_dict)
        if log_entry:
            self.worker.enqueue(log_entry)
        return event_dict


def _build_log_entry(event_dict: Dict[str, Any]) -> dict[str, Any] | None:
    """Map structlog event dict to UnifiedLog fields."""

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
        except Exception:  # noqa: BLE001
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
    if not logger_name:
        return None
    if "." in logger_name:
        return logger_name.split(".")[-1]
    return logger_name


def _build_context(event_dict: Dict[str, Any]) -> dict[str, Any]:
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
            }
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
    except Exception:  # noqa: BLE001 - 容错当前用户代理
        pass

    for key, value in event_dict.items():
        if key in SYSTEM_FIELDS or value is None:
            continue
        if isinstance(value, datetime):
            context[key] = value.isoformat()
        elif hasattr(value, "to_dict"):
            try:
                context[key] = value.to_dict()
            except Exception:  # noqa: BLE001
                context[key] = str(value)
        else:
            context[key] = value

    return context


__all__ = ["DatabaseLogHandler", "DebugFilter", "SYSTEM_FIELDS"]
