"""Permission snapshot view (v4).

V4 decision:
- 不兼容 legacy 旧数据
- snapshot 缺失时必须显式暴露错误码(用于金丝雀监控与回滚)
"""

from __future__ import annotations

from typing import Any

from app.models.account_permission import AccountPermission


def build_permission_snapshot_view(account: AccountPermission) -> dict[str, Any]:
    """Build a stable v4 snapshot view for downstream consumers."""
    snapshot = getattr(account, "permission_snapshot", None)
    if isinstance(snapshot, dict) and snapshot.get("version") == 4:
        return snapshot

    return {
        "version": 4,
        "categories": {},
        "type_specific": {},
        "extra": {},
        "errors": ["SNAPSHOT_MISSING"],
        "meta": {},
    }
