"""鲸落 - 同步会话模型."""

import uuid

from app import db
from app.utils.time_utils import time_utils


class SyncSession(db.Model):
    """同步会话模型 - 管理批量同步会话。.

    记录批量同步任务的会话信息，包括同步类型、状态、时间、
    实例统计等。支持账户同步、容量采集、聚合等多种同步类型。

    Attributes:
        id: 主键 ID。
        session_id: 会话唯一标识（UUID）。
        sync_type: 同步操作方式（manual_single/manual_batch/manual_task/scheduled_task）。
        sync_category: 同步分类（account/capacity/config/aggregation/other）。
        status: 会话状态（pending/running/completed/failed）。
        started_at: 开始时间。
        completed_at: 完成时间。
        total_instances: 总实例数。
        successful_instances: 成功实例数。
        failed_instances: 失败实例数。
        created_by: 创建用户 ID（手动同步时）。
        created_at: 创建时间。
        updated_at: 更新时间。
        instance_records: 关联的实例同步记录。

    """

    __tablename__ = "sync_sessions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    sync_type = db.Column(
        db.String(20), nullable=False,
    )
    sync_category = db.Column(
        db.String(20),
        nullable=False,
        default="account",
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",  # 可选值：pending（待处理）、running（执行中）、completed（已完成）、failed（失败）
    )
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    total_instances = db.Column(db.Integer, default=0)
    successful_instances = db.Column(db.Integer, default=0)
    failed_instances = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer)  # 用户ID（手动同步时）
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

    # 关系
    instance_records = db.relationship(
        "SyncInstanceRecord",
        backref="session",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __init__(self, sync_type: str, sync_category: str = "account", created_by: int | None = None) -> None:
        """初始化同步会话.

        Args:
            sync_type: 同步操作方式 ('manual_single', 'manual_batch', 'manual_task', 'scheduled_task')
            sync_category: 同步分类 ('account', 'capacity', 'config', 'aggregation', 'other')
            created_by: 创建用户ID

        """
        self.session_id = str(uuid.uuid4())
        self.sync_type = sync_type
        self.sync_category = sync_category
        self.total_instances = 0
        self.status = "running"
        self.started_at = time_utils.now()

    def to_dict(self) -> dict[str, any]:
        """序列化同步会话。.

        Returns:
            dict[str, Any]: 包含状态、统计与时间戳字段的字典。

        """
        return {
            "id": self.id,
            "session_id": self.session_id,
            "sync_type": self.sync_type,
            "sync_category": self.sync_category,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "total_instances": self.total_instances,
            "successful_instances": self.successful_instances,
            "failed_instances": self.failed_instances,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def update_statistics(self, succeeded_instances: int, failed_instances: int) -> None:
        """更新会话统计信息并根据情况更新状态.

        Args:
            succeeded_instances: 成功实例数
            failed_instances: 失败实例数

        Returns:
            None: 更新完成后立即返回。

        """
        self.successful_instances = succeeded_instances
        self.failed_instances = failed_instances

        # 只有当所有实例都完成后才更新最终状态
        if self.successful_instances + self.failed_instances == self.total_instances:
            if self.failed_instances > 0:
                self.status = "failed"
            else:
                self.status = "completed"
            self.completed_at = time_utils.now()

    def get_progress_percentage(self) -> int:
        """获取同步进度百分比。.

        Returns:
            int: 0-100 的进度百分比（保留两位小数）。

        """
        if self.total_instances == 0:
            return 0
        completed = self.successful_instances + self.failed_instances
        return round((completed / self.total_instances) * 100, 2)

    @staticmethod
    def get_sessions_by_type(sync_type: str, limit: int = 50) -> list["SyncSession"]:
        """根据类型获取会话列表。.

        Args:
            sync_type: 会话类型过滤条件。
            limit: 返回的最大记录数。

        Returns:
            list[SyncSession]: 满足条件的会话集合，按创建时间倒序。

        """
        return (
            SyncSession.query.filter_by(sync_type=sync_type).order_by(SyncSession.created_at.desc()).limit(limit).all()
        )

    @staticmethod
    def get_sessions_by_category(sync_category: str, limit: int = 50) -> list["SyncSession"]:
        """根据分类获取会话列表。.

        Args:
            sync_category: 会话分类过滤条件。
            limit: 返回的最大记录数。

        Returns:
            list[SyncSession]: 满足条件的会话集合，按创建时间倒序。

        """
        return (
            SyncSession.query.filter_by(sync_category=sync_category)
            .order_by(SyncSession.created_at.desc())
            .limit(limit)
            .all()
        )

    def __repr__(self) -> str:
        """返回同步会话的调试字符串。.

        Returns:
            str: 包含 session_id、类型与分类的文本。

        """
        return f"<SyncSession {self.session_id} ({self.sync_type}-{self.sync_category})>"
