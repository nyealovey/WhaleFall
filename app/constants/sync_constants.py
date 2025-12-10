"""鲸落 - 同步相关常量定义

统一管理同步操作方式和同步分类的常量.
"""

from enum import Enum
from typing import ClassVar


class SyncOperationType(Enum):
    """同步操作方式枚举 - 定义如何执行同步操作."""

    MANUAL_SINGLE = "manual_single"      # 手动单台操作
    MANUAL_BATCH = "manual_batch"        # 手动批量操作
    MANUAL_TASK = "manual_task"          # 手动任务操作
    SCHEDULED_TASK = "scheduled_task"    # 定时任务操作


class SyncCategory(Enum):
    """同步分类枚举 - 定义同步的业务类型."""

    ACCOUNT = "account"          # 账户同步
    CAPACITY = "capacity"        # 容量同步
    CONFIG = "config"           # 配置同步
    AGGREGATION = "aggregation"  # 聚合统计
    OTHER = "other"             # 其他


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

    @staticmethod
    def is_valid_operation_type(value: str) -> bool:
        """验证操作方式是否有效.

        Args:
            value: 操作方式的字符串值.

        Returns:
            True 表示存在于支持列表,否则 False.

        """
        return value in SyncConstants.OPERATION_TYPE_VALUES

    @staticmethod
    def is_valid_category(value: str) -> bool:
        """验证同步分类是否有效.

        Args:
            value: 分类字符串.

        Returns:
            True 表示有效分类,否则 False.

        """
        return value in SyncConstants.CATEGORY_VALUES

    @staticmethod
    def get_operation_type_display(value: str) -> str:
        """获取操作方式的中文显示名称.

        Args:
            value: 操作方式取值.

        Returns:
            对应中文标签,无法解析时返回原值.

        """
        try:
            operation_type = SyncOperationType(value)
            return SyncConstants.OPERATION_TYPE_DISPLAY.get(operation_type, value)
        except ValueError:
            return value

    @staticmethod
    def get_category_display(value: str) -> str:
        """获取同步分类的中文显示名称.

        Args:
            value: 分类取值.

        Returns:
            中文标签,未匹配时返回原值.

        """
        try:
            category = SyncCategory(value)
            return SyncConstants.CATEGORY_DISPLAY.get(category, value)
        except ValueError:
            return value

    @staticmethod
    def get_operation_type_description(value: str) -> str:
        """获取操作方式的英文描述.

        Args:
            value: 操作方式取值.

        Returns:
            英文描述文本,未知值返回原值.

        """
        try:
            operation_type = SyncOperationType(value)
            return SyncConstants.OPERATION_TYPE_DESCRIPTIONS.get(operation_type, value)
        except ValueError:
            return value

    @staticmethod
    def get_category_description(value: str) -> str:
        """获取同步分类的英文描述.

        Args:
            value: 分类取值.

        Returns:
            英文描述文本,未知值返回原值.

        """
        try:
            category = SyncCategory(value)
            return SyncConstants.CATEGORY_DESCRIPTIONS.get(category, value)
        except ValueError:
            return value

    @staticmethod
    def get_all_operation_types() -> list[dict[str, str]]:
        """获取所有操作方式的选项列表.

        Returns:
            包含 value/label/description 的字典列表.

        """
        return [
            {
                "value": op_type.value,
                "label": SyncConstants.OPERATION_TYPE_DISPLAY[op_type],
                "description": SyncConstants.OPERATION_TYPE_DESCRIPTIONS[op_type],
            }
            for op_type in SyncOperationType
        ]

    @staticmethod
    def get_all_categories() -> list[dict[str, str]]:
        """获取所有同步分类的选项列表.

        Returns:
            包含 value/label/description 的字典列表.

        """
        return [
            {
                "value": category.value,
                "label": SyncConstants.CATEGORY_DISPLAY[category],
                "description": SyncConstants.CATEGORY_DESCRIPTIONS[category],
            }
            for category in SyncCategory
        ]


# 向后兼容的别名
SyncType = SyncOperationType  # 保持向后兼容
