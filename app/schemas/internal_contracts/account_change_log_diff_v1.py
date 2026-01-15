"""AccountChangeLog diff payload v1 internal contract adapter/normalizer.

目的：
- 写入口：统一写入 v1 dict 形状，避免继续持久化 legacy list。
- 读入口：兼容读取 legacy list / v1 dict，并对外输出稳定的 `list[entry]` 形状。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

DIFF_VERSION_V1 = 1


def wrap_entries_v1(entries: Sequence[object]) -> dict[str, Any]:
    """Wrap diff entries into v1 dict shape (write entry)."""
    return {"version": DIFF_VERSION_V1, "entries": list(entries)}


def extract_diff_entries(value: object) -> list[object]:
    """Extract diff entries from legacy(list) or v1(dict) payload (read entry)."""
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        raw_version = value.get("version")
        if raw_version != DIFF_VERSION_V1:
            raise ValueError(f"account_change_log_diff.version={raw_version} is not supported")

        entries = value.get("entries")
        if not isinstance(entries, list):
            raise TypeError("account_change_log_diff.entries must be a list")
        return entries

    raise TypeError("account_change_log_diff must be a list, dict(v1), or None")


__all__ = [
    "DIFF_VERSION_V1",
    "extract_diff_entries",
    "wrap_entries_v1",
]
