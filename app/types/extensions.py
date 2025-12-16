"""框架扩展协议与运行期挂载属性类型声明.

集中管理 Flask 应用在运行期挂载的扩展/属性,为 Pyright 提供静态类型支持.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Protocol

from flask import Flask
from flask_caching import Cache
from flask_login import LoginManager

from app.types.structures import LoggerExtra
from app.utils.logging.error_adapter import ErrorContext


class EnhancedErrorHandler(Protocol):
    """增强错误处理器调用协议."""

    def __call__(
        self,
        error: Exception,
        context: ErrorContext | None = None,
        *,
        extra: LoggerExtra | None = None,
    ) -> Mapping[str, object]:
        """处理异常并返回序列化后的错误载荷."""
        ...


class WhaleFallFlask(Flask):
    """鲸落定制的 Flask 子类,补充运行期挂载的扩展属性."""

    enhanced_error_handler: EnhancedErrorHandler
    cache: Cache


class WhaleFallLoginManager(LoginManager):
    """登录管理器子类,标注初始化阶段写入的配置属性."""

    login_view: str | None
    login_message: str
    login_message_category: str
    session_protection: str | None
    remember_cookie_duration: int | float | timedelta
    remember_cookie_secure: bool
    remember_cookie_httponly: bool


__all__ = [
    "EnhancedErrorHandler",
    "WhaleFallFlask",
    "WhaleFallLoginManager",
]
