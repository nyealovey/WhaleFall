"""分页参数解析工具.

用于统一解析列表接口的分页参数,兼容历史字段.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.utils.structlog_config import log_info

_LEGACY_PAGE_SIZE_KEYS: tuple[str, ...] = ("limit", "pageSize")


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
    module: str | None = None,
    action: str | None = None,
) -> int:
    """解析分页每页数量,兼容历史字段.

    兼容顺序: page_size -> pageSize -> limit.

    Args:
        args: 请求参数映射.
        default: 缺省每页数量.
        minimum: 最小值.
        maximum: 最大值.
        module: 结构化日志模块名,用于记录旧字段使用.
        action: 结构化日志动作名,用于记录旧字段使用.

    Returns:
        解析后的每页数量(已做范围裁剪).

    """
    raw = args.get("page_size")
    legacy_key: str | None = None

    if raw is None:
        for key in _LEGACY_PAGE_SIZE_KEYS:
            candidate = args.get(key)
            if candidate is None:
                continue
            raw = candidate
            legacy_key = key
            break

    page_size = _safe_int(raw, default=default)
    page_size = max(page_size, minimum)
    page_size = min(page_size, maximum)

    if legacy_key and module and action:
        log_info(
            "检测到旧分页参数字段",
            module=module,
            action=action,
            legacy_key=legacy_key,
            page_size=page_size,
        )

    return page_size
