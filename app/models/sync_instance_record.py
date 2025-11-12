"""
鲸落 - 同步实例记录模型
"""

from app import db
from app.utils.time_utils import time_utils


class SyncInstanceRecord(db.Model):
    """同步实例记录模型 - 记录每个实例的同步详情
    
    支持多种同步类型：
    - account: 账户同步
    - capacity: 容量同步  
    - aggregation: 聚合统计
    - config: 配置同步
    - other: 其他同步类型
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
        default="pending",
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

    def to_dict(self) -> dict[str, any]:
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
            "items_synced": self.items_synced,
            "items_created": self.items_created,
            "items_updated": self.items_updated,
            "items_deleted": self.items_deleted,
            "error_message": self.error_message,
            "sync_details": self.sync_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def start_sync(self) -> None:
        """开始同步"""
        self.status = "running"
        self.started_at = time_utils.now()

    def complete_sync(
        self,
        items_synced: int = 0,
        items_created: int = 0,
        items_updated: int = 0,
        items_deleted: int = 0,
        sync_details: dict | None = None,
    ) -> None:
        """完成同步"""
        self.status = "completed"
        self.completed_at = time_utils.now()
        self.items_synced = items_synced
        self.items_created = items_created
        self.items_updated = items_updated
        self.items_deleted = items_deleted
        self.sync_details = sync_details

    def fail_sync(self, error_message: str, sync_details: dict | None = None) -> None:
        """同步失败"""
        self.status = "failed"
        self.completed_at = time_utils.now()
        self.error_message = error_message
        self.sync_details = sync_details

    def get_duration_seconds(self) -> float | None:
        """获取同步持续时间（秒）"""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @staticmethod
    def get_records_by_session(session_id: str) -> list["SyncInstanceRecord"]:
        """根据会话ID获取所有实例记录"""
        return (
            SyncInstanceRecord.query.filter_by(session_id=session_id)
            .order_by(SyncInstanceRecord.created_at.asc())
            .all()
        )

    @staticmethod
    def __repr__(self) -> str:
        return f"<SyncInstanceRecord {self.instance_name} ({self.status})>"
