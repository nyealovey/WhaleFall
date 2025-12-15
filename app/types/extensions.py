"""框架扩展协议与运行期挂载属性类型声明.

集中管理 Flask 应用在运行期挂载的扩展/属性,为 Pyright 提供静态类型支持.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import TYPE_CHECKING, Protocol

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


if TYPE_CHECKING:
    class WhaleFallFlask(Flask, Protocol):
        """鲸落定制的 Flask 协议,声明运行期挂载属性（仅静态检查使用）."""

        enhanced_error_handler: EnhancedErrorHandler
        cache: Cache

    class WhaleFallLoginManager(LoginManager, Protocol):
        """登录管理器协议,补齐在应用初始化阶段设置的属性（仅静态检查使用）."""

        login_view: str | None
        login_message: str
        login_message_category: str
        session_protection: str | None
        remember_cookie_duration: int | float | timedelta
        remember_cookie_secure: bool
        remember_cookie_httponly: bool
else:
    class WhaleFallFlask(Flask):
        """运行期 Flask 扩展容器，提供附加属性。"""

        enhanced_error_handler: EnhancedErrorHandler
        cache: Cache

    class WhaleFallLoginManager(LoginManager):
        """运行期登录管理器，保持与协议一致的属性。"""

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
