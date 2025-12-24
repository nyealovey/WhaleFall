"""状态类型常量.

定义各种业务状态值,避免魔法字符串.
"""

from typing import ClassVar


class SyncStatus:
    """同步状态常量.

    定义数据同步任务的状态值.
    """

    # 状态值
    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    PAUSED = "paused"  # 已暂停

    ALL: ClassVar[tuple[str, ...]] = (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, PAUSED)

    ACTIVE: ClassVar[tuple[str, ...]] = (PENDING, RUNNING, PAUSED)

    TERMINAL: ClassVar[tuple[str, ...]] = (COMPLETED, FAILED, CANCELLED)

    # 成功状态
    SUCCESS: ClassVar[tuple[str, ...]] = (COMPLETED,)

    # 失败状态
    ERROR: ClassVar[tuple[str, ...]] = (FAILED, CANCELLED)

    # 辅助方法

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """判断是否为终止状态(已结束).

        Args:
            status: 状态值

        Returns:
            bool: 是否为终止状态

        """
        return status in cls.TERMINAL

    @classmethod
    def is_active(cls, status: str) -> bool:
        """判断是否为活动状态(未结束).

        Args:
            status: 状态值

        Returns:
            bool: 是否为活动状态

        """
        return status in cls.ACTIVE

    @classmethod
    def is_success(cls, status: str) -> bool:
        """判断是否为成功状态.

        Args:
            status: 状态值

        Returns:
            bool: 是否为成功状态

        """
        return status in cls.SUCCESS

    @classmethod
    def is_error(cls, status: str) -> bool:
        """判断是否为错误状态.

        Args:
            status: 状态值

        Returns:
            bool: 是否为错误状态

        """
        return status in cls.ERROR


class SyncSessionStatus:
    """同步会话状态常量.

    该常量用于 `sync_sessions.status`,必须与 DB 侧 `CHECK` 约束保持一致,
    避免默认值与可选集合漂移导致写入失败或统计口径不一致.
    """

    RUNNING = SyncStatus.RUNNING  # 执行中
    COMPLETED = SyncStatus.COMPLETED  # 已完成
    FAILED = SyncStatus.FAILED  # 失败
    CANCELLED = SyncStatus.CANCELLED  # 已取消

    ALL: ClassVar[tuple[str, ...]] = (RUNNING, COMPLETED, FAILED, CANCELLED)

    TERMINAL: ClassVar[tuple[str, ...]] = (COMPLETED, FAILED, CANCELLED)

    @classmethod
    def is_valid(cls, status: str) -> bool:
        """判断状态值是否有效.

        Args:
            status: 状态值.

        Returns:
            bool: True 表示有效,否则 False.

        """
        return status in cls.ALL


class TaskStatus:
    """任务执行状态常量.

    定义后台任务和调度任务的状态值.
    """

    # 状态值
    SUCCESS = "success"  # 成功
    ERROR = "error"  # 错误
    WARNING = "warning"  # 警告
    INFO = "info"  # 信息
    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中

    # 所有状态
    ALL: ClassVar[tuple[str, ...]] = (SUCCESS, ERROR, WARNING, INFO, PENDING, RUNNING)

    # 完成状态
    COMPLETED: ClassVar[tuple[str, ...]] = (SUCCESS, ERROR, WARNING)

    # 进行中状态
    IN_PROGRESS: ClassVar[tuple[str, ...]] = (PENDING, RUNNING)

    # 辅助方法

    @classmethod
    def is_completed(cls, status: str) -> bool:
        """判断任务是否已完成.

        Args:
            status: 状态值

        Returns:
            bool: 是否已完成

        """
        return status in cls.COMPLETED

    @classmethod
    def is_in_progress(cls, status: str) -> bool:
        """判断任务是否进行中.

        Args:
            status: 状态值

        Returns:
            bool: 是否进行中

        """
        return status in cls.IN_PROGRESS


class InstanceStatus:
    """实例状态常量.

    定义数据库实例的状态值.
    """

    # 状态值
    ACTIVE = "active"  # 活动
    INACTIVE = "inactive"  # 非活动
    MAINTENANCE = "maintenance"  # 维护中
    ERROR = "error"  # 错误

    # 所有状态
    ALL: ClassVar[tuple[str, ...]] = (ACTIVE, INACTIVE, MAINTENANCE, ERROR)

    # 辅助方法

    @classmethod
    def is_operational(cls, status: str) -> bool:
        """判断实例是否可操作.

        Args:
            status: 状态值

        Returns:
            bool: 是否可操作

        """
        return status == cls.ACTIVE


class JobStatus:
    """作业状态常量.

    定义APScheduler作业的状态值.
    """

    # 状态值
    SCHEDULED = "scheduled"  # 已调度
    RUNNING = "running"  # 运行中
    PAUSED = "paused"  # 已暂停
    STOPPED = "stopped"  # 已停止

    # 所有状态
    ALL: ClassVar[tuple[str, ...]] = (SCHEDULED, RUNNING, PAUSED, STOPPED)
