"""Permission snapshot view (v4).

V4 decision:
- 不兼容 legacy 旧数据
- snapshot 缺失时必须直接抛出错误,避免静默兜底
"""

from __future__ import annotations

from typing import Any, Final

from app.core.exceptions import ConflictError
from app.models.account_permission import AccountPermission

PERMISSION_SNAPSHOT_VERSION_V4: Final[int] = 4


def build_permission_snapshot_view(account: AccountPermission) -> dict[str, Any]:
    """Build a stable v4 snapshot view for downstream consumers."""
    snapshot = getattr(account, "permission_snapshot", None)
    if isinstance(snapshot, dict) and snapshot.get("version") == PERMISSION_SNAPSHOT_VERSION_V4:
        return snapshot

    raise ConflictError(
        message_key="SNAPSHOT_MISSING",
    )
