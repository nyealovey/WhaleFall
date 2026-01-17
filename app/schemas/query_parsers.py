"""Query 参数解析 helper.

说明：
- 这些函数只做“类型转换 + 去空白 + 默认值”的稳定 canonicalization。
- 统一实现是为了删除各 query schema 文件中复制粘贴的解析逻辑，降低维护面。
"""

from __future__ import annotations

from typing import Any


def parse_int(value: Any, *, default: int) -> int:
    """Parse int with default (strip strings; reject bool)."""
    if value is None:
        return default
    # bool 是 int 的子类，分页等参数不应接受 bool。
    if isinstance(value, bool):
        raise TypeError("参数必须为整数")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return int(stripped, 10)
        except ValueError as exc:
            raise ValueError("参数必须为整数") from exc
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("参数必须为整数") from exc


def parse_optional_int(value: Any) -> int | None:
    """Parse optional int (strip strings; blank -> None; reject bool)."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("参数必须为整数")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped, 10)
        except ValueError as exc:
            raise ValueError("参数必须为整数") from exc
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("参数必须为整数") from exc


def parse_text(value: Any) -> str:
    """Parse text as stripped string; None -> ''."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def parse_tags(value: Any) -> list[str]:
    """Parse tags as list[str] (strip, drop blanks; ignore non-str items)."""
    if value is None:
        return []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            if cleaned:
                result.append(cleaned)
        return result
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    return []


__all__ = ["parse_int", "parse_optional_int", "parse_tags", "parse_text"]
