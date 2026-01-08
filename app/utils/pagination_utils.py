"""分页参数解析工具.

用于统一解析列表接口的分页参数.
"""

from __future__ import annotations

from collections.abc import Mapping


def _safe_int(value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def resolve_page(
    args: Mapping[str, str | None],
    *,
    default: int = 1,
    minimum: int = 1,
) -> int:
    """解析分页页码.

    Args:
        args: 请求参数映射.
        default: 缺省页码.
        minimum: 最小页码.

    Returns:
        解析后的页码(已做下限保护).

    """
    page = _safe_int(args.get("page"), default=default)
    return max(page, minimum)


def resolve_page_size(
    args: Mapping[str, str | None],
    *,
    default: int = 20,
    minimum: int = 1,
    maximum: int = 200,
) -> int:
    """解析分页每页数量.

    Args:
        args: 请求参数映射.
        default: 缺省每页数量.
        minimum: 最小值.
        maximum: 最大值.

    Returns:
        解析后的每页数量(已做范围裁剪).

    """
    raw = args.get("limit")
    page_size = _safe_int(raw, default=default)
    page_size = max(page_size, minimum)
    return min(page_size, maximum)
