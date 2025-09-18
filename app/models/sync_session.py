"""
鲸落 - 同步会话模型
"""

import uuid

from app import db
from app.utils.timezone import now


class SyncSession(db.Model):
    """同步会话模型 - 管理批量同步会话"""

    __tablename__ = "sync_sessions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    sync_type = db.Column(
        db.Enum("manual_single", "manual_batch", "manual_task", "scheduled_task", name="sync_type_enum"), nullable=False
    )
    sync_category = db.Column(
        db.Enum("account", "capacity", "config", "other", name="sync_category_enum"),
        nullable=False,
        default="account",
    )
    status = db.Column(
        db.Enum("running", "completed", "failed", "cancelled", name="sync_status_enum"),
        nullable=False,
        default="running",
    )
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    completed_at = db.Column(db.DateTime(timezone=True))
    total_instances = db.Column(db.Integer, default=0)
    successful_instances = db.Column(db.Integer, default=0)
    failed_instances = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer)  # 用户ID（手动同步时）
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)

    # 关系
    instance_records = db.relationship(
        "SyncInstanceRecord",
        backref="session",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __init__(self, sync_type: str, sync_category: str = "account", created_by: int | None = None) -> None:
        """
        初始化同步会话

        Args:
            sync_type: 同步类型 ('manual_single', 'manual_batch', 'manual_task', 'scheduled_task')
            sync_category: 同步分类 ('account', 'capacity', 'config', 'other')
            created_by: 创建用户ID
        """
        self.session_id = str(uuid.uuid4())
        self.sync_type = sync_type
        self.sync_category = sync_category
        self.status = "running"
        self.started_at = now()
        self.created_by = created_by

    def to_dict(self) -> dict[str, any]:
        """转换为字典"""
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

    def update_statistics(self) -> None:
        """更新统计信息"""
        records = self.instance_records.all()
        self.total_instances = len(records)
        self.successful_instances = len([r for r in records if r.status == "completed"])
        self.failed_instances = len([r for r in records if r.status == "failed"])

        # 更新状态
        if self.failed_instances == 0:
            self.status = "completed"
        elif self.successful_instances == 0:
            self.status = "failed"
        else:
            self.status = "failed"  # 部分失败也算失败

        self.completed_at = now()
        self.updated_at = now()

    def get_progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_instances == 0:
            return 0
        completed = self.successful_instances + self.failed_instances
        return round((completed / self.total_instances) * 100, 2)

    @staticmethod
    def get_sessions_by_type(sync_type: str, limit: int = 50) -> list["SyncSession"]:
        """根据类型获取会话列表"""
        return (
            SyncSession.query.filter_by(sync_type=sync_type).order_by(SyncSession.created_at.desc()).limit(limit).all()
        )

    @staticmethod
    def get_sessions_by_category(sync_category: str, limit: int = 50) -> list["SyncSession"]:
        """根据分类获取会话列表"""
        return (
            SyncSession.query.filter_by(sync_category=sync_category)
            .order_by(SyncSession.created_at.desc())
            .limit(limit)
            .all()
        )

    def __repr__(self) -> str:
        return f"<SyncSession {self.session_id} ({self.sync_type}-{self.sync_category})>"
