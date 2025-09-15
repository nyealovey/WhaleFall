"""
泰摸鱼吧 - 同步实例记录模型
"""

from datetime import datetime

from app import db
from app.utils.timezone import now


class SyncInstanceRecord(db.Model):
    """同步实例记录模型 - 记录每个实例的同步详情"""

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
        db.Enum("account", "capacity", "config", "other", name="sync_record_category_enum"),
        nullable=False,
        default="account",
    )
    status = db.Column(
        db.Enum("pending", "running", "completed", "failed", name="sync_record_status_enum"),
        nullable=False,
        default="pending",
    )
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # 账户同步统计字段
    accounts_synced = db.Column(db.Integer, default=0)
    accounts_created = db.Column(db.Integer, default=0)
    accounts_updated = db.Column(db.Integer, default=0)
    accounts_deleted = db.Column(db.Integer, default=0)

    # 通用字段
    error_message = db.Column(db.Text)
    sync_details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(
        self,
        session_id: str,
        instance_id: int,
        instance_name: str = None,
        sync_category: str = "account",
    ):
        """
        初始化同步实例记录

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
        self.status = "pending"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "instance_id": self.instance_id,
            "instance_name": self.instance_name,
            "sync_category": self.sync_category,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "accounts_synced": self.accounts_synced,
            "accounts_created": self.accounts_created,
            "accounts_updated": self.accounts_updated,
            "accounts_deleted": self.accounts_deleted,
            "error_message": self.error_message,
            "sync_details": self.sync_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def start_sync(self):
        """开始同步"""
        self.status = "running"
        self.started_at = now()

    def complete_sync(
        self,
        accounts_synced: int = 0,
        accounts_created: int = 0,
        accounts_updated: int = 0,
        accounts_deleted: int = 0,
        sync_details: dict = None,
    ):
        """完成同步"""
        self.status = "completed"
        self.completed_at = now()
        self.accounts_synced = accounts_synced
        self.accounts_created = accounts_created
        self.accounts_updated = accounts_updated
        self.accounts_deleted = accounts_deleted
        self.sync_details = sync_details

    def fail_sync(self, error_message: str, sync_details: dict = None):
        """同步失败"""
        self.status = "failed"
        self.completed_at = now()
        self.error_message = error_message
        self.sync_details = sync_details

    def get_duration_seconds(self):
        """获取同步持续时间（秒）"""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @staticmethod
    def get_records_by_session(session_id: str):
        """根据会话ID获取所有实例记录"""
        return (
            SyncInstanceRecord.query.filter_by(session_id=session_id)
            .order_by(SyncInstanceRecord.created_at.asc())
            .all()
        )

    @staticmethod
    def get_records_by_instance(instance_id: int, limit: int = 50):
        """根据实例ID获取同步记录"""
        return (
            SyncInstanceRecord.query.filter_by(instance_id=instance_id)
            .order_by(SyncInstanceRecord.created_at.desc())
            .limit(limit)
            .all()
        )

    def __repr__(self):
        return f"<SyncInstanceRecord {self.instance_name} ({self.status})>"
