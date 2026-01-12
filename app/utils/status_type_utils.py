"""状态类型工具.

从 `app/constants/status_types.py` 读取静态集合,提供状态判定的纯函数.
"""

from __future__ import annotations

from app.constants.status_types import InstanceStatus, SyncSessionStatus, SyncStatus, TaskStatus


def is_terminal_sync_status(status: str) -> bool:
    return status in SyncStatus.TERMINAL


def is_active_sync_status(status: str) -> bool:
    return status in SyncStatus.ACTIVE


def is_success_sync_status(status: str) -> bool:
    return status in SyncStatus.SUCCESS


def is_error_sync_status(status: str) -> bool:
    return status in SyncStatus.ERROR


def is_valid_sync_session_status(status: str) -> bool:
    return status in SyncSessionStatus.ALL


def is_completed_task_status(status: str) -> bool:
    return status in TaskStatus.COMPLETED


def is_in_progress_task_status(status: str) -> bool:
    return status in TaskStatus.IN_PROGRESS


def is_operational_instance_status(status: str) -> bool:
    return status == InstanceStatus.ACTIVE

