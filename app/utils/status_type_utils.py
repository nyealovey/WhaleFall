"""状态类型工具.

从 `app/core/constants/status_types.py` 读取静态集合,提供状态判定的纯函数.
"""

from __future__ import annotations

from app.core.constants.status_types import SyncSessionStatus


def is_valid_sync_session_status(status: str) -> bool:
    """判断会话状态是否合法."""
    return status in SyncSessionStatus.ALL
