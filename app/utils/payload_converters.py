"""表单/JSON 数据类型转换工具.

提供稳定的转换函数,将 `PayloadValue` 映射为具体的 str/bool/int 类型,
便于服务层书写类型安全的逻辑.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.types.structures import PayloadValue

_STRING_LIKE_TYPES = (str, bytes, bytearray)


def _unwrap_sequence(value: PayloadValue | None) -> PayloadValue | None:
    if isinstance(value, Sequence) and not isinstance(value, _STRING_LIKE_TYPES):
        if not value:
            return None
        return value[-1]
    return value


def as_bool(value: PayloadValue | None, *, default: bool = False) -> bool:
    """转换为布尔值."""
    base = _unwrap_sequence(value)
    if base is None:
        return default

    result = default
    if isinstance(base, bool):
        result = base
    elif isinstance(base, (int, float)):
        result = bool(base)
    elif isinstance(base, str):
        normalized = base.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            result = True
        elif normalized in {"false", "0", "no", "off"}:
            result = False
    return result
