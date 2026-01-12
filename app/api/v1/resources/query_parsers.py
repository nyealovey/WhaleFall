"""API v1 query 参数解析工具.

约束:
- 仅用于 API 层的 query params(`request.args`)
- 通过 `flask_restx.reqparse.RequestParser` 统一解析并配合 `@ns.expect(parser)`
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

from flask_restx import reqparse

from app.utils.payload_converters import as_bool

_DEFAULT_BUNDLE_ERRORS: Final[bool] = True


def new_parser(*, bundle_errors: bool = _DEFAULT_BUNDLE_ERRORS) -> reqparse.RequestParser:
    """构造统一配置的 RequestParser."""
    return reqparse.RequestParser(bundle_errors=bundle_errors)


def bool_with_default(default: bool) -> Callable[[Any], bool]:
    """构造布尔解析器,兼容常见 truthy/falsey 字符串."""

    def _convert(value: Any) -> bool:
        return as_bool(value, default=default)

    return _convert


def split_comma_separated(values: list[str] | None) -> list[str]:
    """将 `['a', 'b,c']` 统一解析为 `['a', 'b', 'c']`(去空白,去空项)."""
    if not values:
        return []
    output: list[str] = []
    for item in values:
        for segment in (item or "").split(","):
            cleaned = segment.strip()
            if cleaned:
                output.append(cleaned)
    return output

