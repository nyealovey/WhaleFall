"""Flask 框架相关的类型与扩展声明(Infra).

说明:
- 该模块用于承载 Flask/扩展的运行期子类与类型别名(typing helpers)。
- 它属于 Infra(基础设施)层, **禁止**被 `app/core/**`(shared kernel) 依赖。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import ParamSpec, Protocol, TypeAlias

from flask import Flask
from flask.typing import ResponseReturnValue, RouteCallable as FlaskRouteCallable
from flask_caching import Cache
from flask_login import LoginManager

from app.core.types.structures import LoggerExtra
from app.utils.logging.error_adapter import ErrorContext

P = ParamSpec("P")

# ---------------------------------------------------------------------------
# Routes typing
# ---------------------------------------------------------------------------

# 统一路由返回值类型,涵盖字符串、Response 及包含状态码/头部的元组。
RouteReturn: TypeAlias = ResponseReturnValue
# 支持异步视图返回的 Awaitable 形式。
RouteAwaitable: TypeAlias = Awaitable[RouteReturn]
# 与 Flask 内置 RouteCallable 对齐,用于 add_url_rule 等注册函数。
RouteCallable: TypeAlias = FlaskRouteCallable
# 便捷别名,表示接受任意参数并返回同步或异步路由结果的可调用。
RouteHandler: TypeAlias = Callable[P, RouteReturn | RouteAwaitable]


# ---------------------------------------------------------------------------
# Flask app/extension typing
# ---------------------------------------------------------------------------


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


__all__ = [
    "EnhancedErrorHandler",
    "RouteAwaitable",
    "RouteCallable",
    "RouteHandler",
    "RouteReturn",
    "WhaleFallFlask",
    "WhaleFallLoginManager",
]
