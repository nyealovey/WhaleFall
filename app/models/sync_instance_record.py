"""同步实例记录模型.

记录每个实例在同步会话中的详细执行情况,包括状态、统计数据和错误信息.
"""

from typing import Any

from app import db
from app.core.constants.status_types import SyncStatus
from app.utils.time_utils import time_utils


class SyncInstanceRecord(db.Model):
    """同步实例记录模型.

    记录每个实例的同步详情,包括同步状态、时间、统计数据和错误信息.

    Attributes:
        id: 记录 ID.
        session_id: 关联的同步会话 ID.
        instance_id: 关联的实例 ID.
        instance_name: 实例名称.
        sync_category: 同步分类(account、capacity、aggregation、config、other).
        status: 同步状态(pending、running、completed、failed).
        started_at: 同步开始时间.
        completed_at: 同步完成时间.
        items_synced: 同步的项目数量.
        items_created: 创建的项目数量.
        items_updated: 更新的项目数量.
        items_deleted: 删除的项目数量.
        error_message: 错误消息.
        sync_details: 同步详细信息(JSON).
        created_at: 记录创建时间.

    Example:
        >>> record = SyncInstanceRecord(session_id='abc-123', instance_id=1, instance_name='MySQL-01')
        >>> record.start_sync()
        >>> record.complete_sync(items_synced=100, items_created=10)

    """

    __tablename__ = "sync_instance_records"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.String(36),
        db.ForeignKey("sync_sessions.session_id"),
        nullable=False,
        index=True,
    )
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    instance_name = db.Column(db.String(255))
    sync_category = db.Column(
        db.String(20),
        nullable=False,
        default="account",
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default=SyncStatus.PENDING,
    )
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))

    # 通用同步统计字段
    items_synced = db.Column(db.Integer, default=0)  # 同步的项目数量
    items_created = db.Column(db.Integer, default=0)  # 创建的项目数量
    items_updated = db.Column(db.Integer, default=0)  # 更新的项目数量
    items_deleted = db.Column(db.Integer, default=0)  # 删除的项目数量

    # 通用字段
    error_message = db.Column(db.Text)
    sync_details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)

    def __init__(
        self,
        session_id: str,
        instance_id: int,
        instance_name: str | None = None,
        sync_category: str = "account",
    ) -> None:
        """初始化同步实例记录.

        Args:
            session_id: 同步会话ID
            instance_id: 实例ID
            instance_name: 实例名称
            sync_category: 同步分类

        """
        self.session_id = session_id
        self.instance_id = instance_id
        self.instance_name = instance_name
        self.sync_category = sync_category
        self.status = SyncStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            包含所有字段的字典表示.

        """
        return {
            "id": self.id,
            "session_id": self.session_id,
            "instance_id": self.instance_id,
            "instance_name": self.instance_name,
            "sync_category": self.sync_category,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "items_synced": self.items_synced,
            "items_created": self.items_created,
            "items_updated": self.items_updated,
            "items_deleted": self.items_deleted,
            "error_message": self.error_message,
            "sync_details": self.sync_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def start_sync(self) -> None:
        """开始同步.

        将状态设置为 running 并记录开始时间.

        Returns:
            None: 状态更新后立即返回.

        """
        self.status = SyncStatus.RUNNING
        self.started_at = time_utils.now()

    def complete_sync(
        self,
        items_synced: int = 0,
        items_created: int = 0,
        items_updated: int = 0,
        items_deleted: int = 0,
        sync_details: dict | None = None,
    ) -> None:
        """完成同步.

        将状态设置为 completed 并记录统计数据.

        Args:
            items_synced: 同步的项目数量.
            items_created: 创建的项目数量.
            items_updated: 更新的项目数量.
            items_deleted: 删除的项目数量.
            sync_details: 同步详细信息.

        Returns:
            None: 仅更新实例记录状态与统计数据.

        """
        self.status = SyncStatus.COMPLETED
        self.completed_at = time_utils.now()
        self.items_synced = items_synced
        self.items_created = items_created
        self.items_updated = items_updated
        self.items_deleted = items_deleted
        self.sync_details = sync_details

    def fail_sync(self, error_message: str, sync_details: dict | None = None) -> None:
        """同步失败.

        将状态设置为 failed 并记录错误信息.

        Args:
            error_message: 错误消息.
            sync_details: 同步详细信息.

        Returns:
            None: 状态与错误信息写入完成后返回.

        """
        self.status = "failed"
        self.completed_at = time_utils.now()
        self.error_message = error_message
        self.sync_details = sync_details

    def get_duration_seconds(self) -> float | None:
        """获取同步持续时间.

        Returns:
            同步持续时间(秒),如果未完成则返回 None.

        """
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @staticmethod
    def get_records_by_session(session_id: str) -> list["SyncInstanceRecord"]:
        """根据会话 ID 获取所有实例记录.

        Args:
            session_id: 同步会话 ID.

        Returns:
            实例记录列表,按创建时间升序排列.

        """
        return (
            SyncInstanceRecord.query.filter_by(session_id=session_id)
            .order_by(SyncInstanceRecord.created_at.asc())
            .all()
        )

    def __repr__(self) -> str:
        """返回同步实例记录的调试字符串.

        Returns:
            str: 包含实例名称与当前状态的描述.

        """
        return f"<SyncInstanceRecord {self.instance_name} ({self.status})>"
