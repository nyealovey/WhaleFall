"""表单/JSON 数据类型转换工具.

提供稳定的转换函数,将 `PayloadValue` 映射为具体的 str/bool/int 类型,
便于服务层书写类型安全的逻辑.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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


def as_str(value: PayloadValue | None, *, default: str = "") -> str:
    """转换为字符串.

    Args:
        value: 待转换的原始值.
        default: 当值为空或 None 时的默认字符串.

    Returns:
        转换后的字符串.

    """
    base = _unwrap_sequence(value)
    if base is None:
        return default
    if isinstance(base, str):
        return base
    if isinstance(base, (bytes, bytearray)):
        return base.decode()
    return str(base)


def as_optional_str(value: PayloadValue | None) -> str | None:
    """转换为可选字符串,空白返回 None."""
    cleaned = as_str(value, default="").strip()
    return cleaned or None


def as_int(value: PayloadValue | None, *, default: int | None = None) -> int | None:
    """转换为整数.

    Args:
        value: 待转换的值.
        default: 无法转换时返回的默认值.

    Returns:
        int 或 None.

    """
    base = _unwrap_sequence(value)
    if base is None:
        return default

    result = default
    if isinstance(base, (bool, int, float)):
        result = int(base)
    elif isinstance(base, str):
        stripped = base.strip()
        if stripped:
            try:
                result = int(stripped, 10)
            except ValueError:
                result = default
    return result


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


def as_list_of_str(value: PayloadValue | None) -> list[str]:
    """转换为字符串列表,按逗号或序列拆分."""
    base = _unwrap_sequence(value)
    if base is None:
        return []
    if isinstance(base, str):
        return [segment.strip() for segment in base.split(",") if segment.strip()]
    if isinstance(base, Sequence):
        result: list[str] = []
        for item in base:
            normalized = as_optional_str(item)
            if normalized:
                result.append(normalized)
        return result
    return [as_str(base, default="").strip()]


def ensure_mapping(value: PayloadValue | None) -> Mapping[str, PayloadValue] | None:
    """确保值为映射类型,否则返回 None."""
    base = _unwrap_sequence(value)
    if isinstance(base, Mapping):
        return base
    return None
