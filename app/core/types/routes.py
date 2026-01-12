"""路由层通用类型别名.

集中定义 Flask 路由返回值与可调用签名,便于装饰器包装后保持一致的类型推断。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeAlias

from flask.typing import ResponseReturnValue, RouteCallable as FlaskRouteCallable

P = ParamSpec("P")

# 统一路由返回值类型,涵盖字符串、Response 及包含状态码/头部的元组。
RouteReturn: TypeAlias = ResponseReturnValue
# 支持异步视图返回的 Awaitable 形式。
RouteAwaitable: TypeAlias = Awaitable[RouteReturn]
# 与 Flask 内置 RouteCallable 对齐,用于 add_url_rule 等注册函数。
RouteCallable: TypeAlias = FlaskRouteCallable
# 便捷别名,表示接受任意参数并返回同步或异步路由结果的可调用。
RouteHandler: TypeAlias = Callable[P, RouteReturn | RouteAwaitable]

__all__ = [
    "RouteAwaitable",
    "RouteCallable",
    "RouteHandler",
    "RouteReturn",
]
