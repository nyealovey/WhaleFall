"""Internal data contract adapters/normalizers.

说明：
- 该目录用于 internal payload（snapshot/cache/JSON column）的单入口 canonicalization。
- 业务层/Service/Repository 禁止出现结构兼容链（如 `data.get("new") or data.get("old")`）。
"""

from .permission_snapshot_v4 import normalize_permission_snapshot_categories_v4, parse_permission_snapshot_categories_v4

__all__ = [
    "normalize_permission_snapshot_categories_v4",
    "parse_permission_snapshot_categories_v4",
]
