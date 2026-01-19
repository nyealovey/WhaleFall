"""sync_details v1 internal contract adapter/normalizer.

目的：
- 收敛 `sync_details(v1)` 的写入 shape：所有写入必须包含 `version=1`。
- 业务层禁止散落“缺字段就 or 兜底”的兼容逻辑；兼容只允许在 schema 单入口处理。
"""

from __future__ import annotations

from typing import Any

SYNC_DETAILS_VERSION_V1 = 1


def normalize_sync_details_v1(value: object) -> dict[str, Any] | None:
    """Normalize sync_details payload into v1 shape (write entry).

    Rules:
    - None -> None
    - Must be a dict, otherwise fail-fast (TypeError)
    - If version is missing/invalid -> inject version=1
    - If version is an int but not 1 -> fail-fast (ValueError)
    """
    if value is None:
        return None

    if not isinstance(value, dict):
        raise TypeError("sync_details must be a dict or None")

    normalized: dict[str, Any] = dict(value)

    raw_version = normalized.get("version")
    if raw_version == SYNC_DETAILS_VERSION_V1:
        return normalized

    if type(raw_version) is int and raw_version != SYNC_DETAILS_VERSION_V1:
        raise ValueError(f"sync_details.version={raw_version} is not supported")

    normalized["version"] = SYNC_DETAILS_VERSION_V1
    return normalized


__all__ = [
    "SYNC_DETAILS_VERSION_V1",
    "normalize_sync_details_v1",
]
