"""定时任务模块集合.

为避免循环导入,此包不在导入时触发实际任务加载,具体任务请在使用处按需导入.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 仅用于类型检查,避免实际导入时触发任务加载
    from app.tasks import (
        accounts_sync_tasks,
        capacity_aggregation_tasks,
        capacity_collection_tasks,
        log_cleanup_tasks,
        partition_management_tasks,
    )

__all__ = [
    "accounts_sync_tasks",
    "capacity_aggregation_tasks",
    "capacity_collection_tasks",
    "log_cleanup_tasks",
    "partition_management_tasks",
]
