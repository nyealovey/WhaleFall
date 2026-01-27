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

    ALL: ClassVar[tuple[str, ...]] = (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)

    ACTIVE: ClassVar[tuple[str, ...]] = (PENDING, RUNNING)

    TERMINAL: ClassVar[tuple[str, ...]] = (COMPLETED, FAILED, CANCELLED)

    # 成功状态
    SUCCESS: ClassVar[tuple[str, ...]] = (COMPLETED,)

    # 失败状态
    ERROR: ClassVar[tuple[str, ...]] = (FAILED, CANCELLED)


class SyncSessionStatus:
    """同步会话状态常量.

    该常量用于 `sync_sessions.status`,必须与 DB 侧 `CHECK` 约束保持一致,
    避免默认值与可选集合漂移导致写入失败或统计口径不一致.
    """

    RUNNING = SyncStatus.RUNNING  # 运行中
    COMPLETED = SyncStatus.COMPLETED  # 已完成
    FAILED = SyncStatus.FAILED  # 失败
    CANCELLED = SyncStatus.CANCELLED  # 已取消

    ALL: ClassVar[tuple[str, ...]] = (RUNNING, COMPLETED, FAILED, CANCELLED)

    TERMINAL: ClassVar[tuple[str, ...]] = (COMPLETED, FAILED, CANCELLED)


class TaskRunStatus:
    """任务运行状态常量.

    定义 task_runs 表的状态值.
    """

    PENDING = SyncStatus.PENDING  # 等待中
    RUNNING = SyncStatus.RUNNING  # 运行中
    COMPLETED = SyncStatus.COMPLETED  # 已完成
    FAILED = SyncStatus.FAILED  # 失败
    CANCELLED = SyncStatus.CANCELLED  # 已取消

    ALL: ClassVar[tuple[str, ...]] = SyncStatus.ALL

    TERMINAL: ClassVar[tuple[str, ...]] = SyncStatus.TERMINAL

    IN_PROGRESS: ClassVar[tuple[str, ...]] = SyncStatus.ACTIVE
