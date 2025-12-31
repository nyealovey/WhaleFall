"""Permission snapshot view (v4).

V4 decision:
- 不兼容 legacy 旧数据
- snapshot 缺失时必须直接抛出错误,避免静默兜底
"""

from __future__ import annotations

from typing import Any

from app.constants import ErrorCategory, ErrorSeverity, HttpStatus
from app.errors import AppError
from app.models.account_permission import AccountPermission


def build_permission_snapshot_view(account: AccountPermission) -> dict[str, Any]:
    """Build a stable v4 snapshot view for downstream consumers."""
    snapshot = getattr(account, "permission_snapshot", None)
    if isinstance(snapshot, dict) and snapshot.get("version") == 4:
        return snapshot

    raise AppError(
        message_key="SNAPSHOT_MISSING",
        status_code=HttpStatus.CONFLICT,
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.MEDIUM,
    )
