"""表单/JSON 数据类型转换工具.

提供稳定的转换函数,将 `PayloadValue` 映射为具体的 str/bool/int 类型,
便于服务层书写类型安全的逻辑.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.types.structures import PayloadValue

_STRING_LIKE_TYPES = (str, bytes, bytearray)


def _unwrap_sequence(value: PayloadValue | None) -> PayloadValue | None:
    if isinstance(value, Sequence) and not isinstance(value, _STRING_LIKE_TYPES):
        if not value:
            return None
        return value[-1]
    return value


def as_str(value: PayloadValue | None, *, default: str = "") -> str:
    base = _unwrap_sequence(value)
    if base is None:
        return default
    if isinstance(base, str):
        return base
    if isinstance(base, (bytes, bytearray)):
        return base.decode()
    return str(base)


def as_optional_str(value: PayloadValue | None) -> str | None:
    cleaned = as_str(value, default="").strip()
    return cleaned or None


def as_int(value: PayloadValue | None, *, default: int | None = None) -> int | None:
    base = _unwrap_sequence(value)
    if base is None:
        return default
    if isinstance(base, bool):
        return int(base)
    if isinstance(base, (int, float)):
        return int(base)
    if isinstance(base, str):
        stripped = base.strip()
        if not stripped:
            return default
        try:
            return int(stripped, 10)
        except ValueError:
            return default
    return default


def as_bool(value: PayloadValue | None, *, default: bool = False) -> bool:
    base = _unwrap_sequence(value)
    if base is None:
        return default
    if isinstance(base, bool):
        return base
    if isinstance(base, (int, float)):
        return bool(base)
    if isinstance(base, str):
        normalized = base.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
        return default
    return default


def as_list_of_str(value: PayloadValue | None) -> list[str]:
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
    base = _unwrap_sequence(value)
    if isinstance(base, Mapping):
        return base
    return None
