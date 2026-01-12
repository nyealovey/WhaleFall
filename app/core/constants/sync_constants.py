"""鲸落 - 同步相关常量定义.

统一管理同步操作方式和同步分类的常量.
"""

from enum import Enum
from typing import ClassVar


class SyncOperationType(Enum):
    """同步操作方式枚举 - 定义如何执行同步操作."""

    MANUAL_SINGLE = "manual_single"  # 手动单台操作
    MANUAL_BATCH = "manual_batch"  # 手动批量操作
    MANUAL_TASK = "manual_task"  # 手动任务操作
    SCHEDULED_TASK = "scheduled_task"  # 定时任务操作


class SyncCategory(Enum):
    """同步分类枚举 - 定义同步的业务类型."""

    ACCOUNT = "account"  # 账户同步
    CAPACITY = "capacity"  # 容量同步
    CONFIG = "config"  # 配置同步
    AGGREGATION = "aggregation"  # 聚合统计
    OTHER = "other"  # 其他


class SyncConstants:
    """同步相关常量."""

    OPERATION_TYPE_DISPLAY: ClassVar[dict[SyncOperationType, str]] = {
        SyncOperationType.MANUAL_SINGLE: "手动单台",
        SyncOperationType.MANUAL_BATCH: "手动批量",
        SyncOperationType.MANUAL_TASK: "手动任务",
        SyncOperationType.SCHEDULED_TASK: "定时任务",
    }

    CATEGORY_DISPLAY: ClassVar[dict[SyncCategory, str]] = {
        SyncCategory.ACCOUNT: "账户同步",
        SyncCategory.CAPACITY: "容量同步",
        SyncCategory.CONFIG: "配置同步",
        SyncCategory.AGGREGATION: "聚合统计",
        SyncCategory.OTHER: "其他",
    }

    OPERATION_TYPE_DESCRIPTIONS: ClassVar[dict[SyncOperationType, str]] = {
        SyncOperationType.MANUAL_SINGLE: "Manual Single Instance Operation",
        SyncOperationType.MANUAL_BATCH: "Manual Batch Operation",
        SyncOperationType.MANUAL_TASK: "Manual Task Operation",
        SyncOperationType.SCHEDULED_TASK: "Scheduled Task Operation",
    }

    CATEGORY_DESCRIPTIONS: ClassVar[dict[SyncCategory, str]] = {
        SyncCategory.ACCOUNT: "Account Synchronization",
        SyncCategory.CAPACITY: "Capacity Synchronization",
        SyncCategory.CONFIG: "Configuration Synchronization",
        SyncCategory.AGGREGATION: "Aggregation Statistics",
        SyncCategory.OTHER: "Other Operations",
    }

    OPERATION_TYPE_VALUES: ClassVar[tuple[str, ...]] = tuple(t.value for t in SyncOperationType)
    CATEGORY_VALUES: ClassVar[tuple[str, ...]] = tuple(c.value for c in SyncCategory)
