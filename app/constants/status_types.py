"""
状态类型常量

定义各种业务状态值，避免魔法字符串。
"""


class SyncStatus:
    """同步状态常量

    定义数据同步任务的状态值。
    """

    # ============================================================================
    # 状态值
    # ============================================================================
    PENDING = "pending"         # 等待中
    RUNNING = "running"         # 运行中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
    PAUSED = "paused"           # 已暂停

    # 所有状态
    ALL = [PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, PAUSED]

    # 活动状态（未结束）
    ACTIVE = [PENDING, RUNNING, PAUSED]

    # 终止状态（已结束）
    TERMINAL = [COMPLETED, FAILED, CANCELLED]

    # 成功状态
    SUCCESS = [COMPLETED]

    # 失败状态
    ERROR = [FAILED, CANCELLED]

    # ============================================================================
    # 辅助方法
    # ============================================================================

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """判断是否为终止状态（已结束）

        Args:
            status: 状态值

        Returns:
            bool: 是否为终止状态

        """
        return status in cls.TERMINAL

    @classmethod
    def is_active(cls, status: str) -> bool:
        """判断是否为活动状态（未结束）

        Args:
            status: 状态值

        Returns:
            bool: 是否为活动状态

        """
        return status in cls.ACTIVE

    @classmethod
    def is_success(cls, status: str) -> bool:
        """判断是否为成功状态

        Args:
            status: 状态值

        Returns:
            bool: 是否为成功状态

        """
        return status in cls.SUCCESS

    @classmethod
    def is_error(cls, status: str) -> bool:
        """判断是否为错误状态

        Args:
            status: 状态值

        Returns:
            bool: 是否为错误状态

        """
        return status in cls.ERROR


class TaskStatus:
    """任务执行状态常量

    定义后台任务和调度任务的状态值。
    """

    # ============================================================================
    # 状态值
    # ============================================================================
    SUCCESS = "success"         # 成功
    ERROR = "error"             # 错误
    WARNING = "warning"         # 警告
    INFO = "info"               # 信息
    PENDING = "pending"         # 等待中
    RUNNING = "running"         # 运行中

    # 所有状态
    ALL = [SUCCESS, ERROR, WARNING, INFO, PENDING, RUNNING]

    # 完成状态
    COMPLETED = [SUCCESS, ERROR, WARNING]

    # 进行中状态
    IN_PROGRESS = [PENDING, RUNNING]

    # ============================================================================
    # 辅助方法
    # ============================================================================

    @classmethod
    def is_completed(cls, status: str) -> bool:
        """判断任务是否已完成

        Args:
            status: 状态值

        Returns:
            bool: 是否已完成

        """
        return status in cls.COMPLETED

    @classmethod
    def is_in_progress(cls, status: str) -> bool:
        """判断任务是否进行中

        Args:
            status: 状态值

        Returns:
            bool: 是否进行中

        """
        return status in cls.IN_PROGRESS


class InstanceStatus:
    """实例状态常量

    定义数据库实例的状态值。
    """

    # ============================================================================
    # 状态值
    # ============================================================================
    ACTIVE = "active"           # 活动
    INACTIVE = "inactive"       # 非活动
    MAINTENANCE = "maintenance" # 维护中
    ERROR = "error"             # 错误

    # 所有状态
    ALL = [ACTIVE, INACTIVE, MAINTENANCE, ERROR]

    # ============================================================================
    # 辅助方法
    # ============================================================================

    @classmethod
    def is_operational(cls, status: str) -> bool:
        """判断实例是否可操作

        Args:
            status: 状态值

        Returns:
            bool: 是否可操作

        """
        return status == cls.ACTIVE


class JobStatus:
    """作业状态常量

    定义APScheduler作业的状态值。
    """

    # ============================================================================
    # 状态值
    # ============================================================================
    SCHEDULED = "scheduled"     # 已调度
    RUNNING = "running"         # 运行中
    PAUSED = "paused"           # 已暂停
    STOPPED = "stopped"         # 已停止

    # 所有状态
    ALL = [SCHEDULED, RUNNING, PAUSED, STOPPED]
