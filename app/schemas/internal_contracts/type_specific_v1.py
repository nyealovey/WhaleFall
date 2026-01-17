"""type_specific v1 internal contract adapter/normalizer.

目的：
- 收敛 `account_permission.type_specific(v1)` 的写入 shape：所有写入必须包含 `version=1`。
- 读入口只允许在 schema 单入口补齐 legacy payload，避免业务层散落兼容分支与 `or` 兜底链。
"""

from __future__ import annotations

from typing import Any

TYPE_SPECIFIC_VERSION_V1 = 1


def normalize_type_specific_v1(value: object) -> dict[str, Any] | None:
    """Normalize type_specific payload into v1 shape (write/read entry).

    Rules:
    - None -> None
    - Must be a dict, otherwise fail-fast (TypeError)
    - If version is missing/invalid -> inject version=1
    - If version is an int but not 1 -> fail-fast (ValueError)
    """
    if value is None:
        return None

    if not isinstance(value, dict):
        raise TypeError("type_specific must be a dict or None")

    normalized: dict[str, Any] = dict(value)

    raw_version = normalized.get("version")
    if raw_version == TYPE_SPECIFIC_VERSION_V1:
        return normalized

    if type(raw_version) is int and raw_version != TYPE_SPECIFIC_VERSION_V1:
        raise ValueError(f"type_specific.version={raw_version} is not supported")

    normalized["version"] = TYPE_SPECIFIC_VERSION_V1
    return normalized


__all__ = [
    "TYPE_SPECIFIC_VERSION_V1",
    "normalize_type_specific_v1",
]
