"""
泰摸鱼吧 - 基础同步数据模型
"""

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped

from app import db
from app.utils.timezone import now


class BaseSyncData(db.Model):
    """基础同步数据模型（抽象基类）"""

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)

    @declared_attr
    def instance_id(cls) -> Mapped[int]:
        return db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)

    db_type = db.Column(db.String(20), nullable=False, index=True)  # 'mysql', 'postgresql', 'sqlserver', 'oracle'
    session_id = db.Column(db.String(36), nullable=True, index=True)
    sync_time = db.Column(db.DateTime(timezone=True), default=now, index=True)
    status = db.Column(db.String(20), default="success", index=True)
    message = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    # 关联实例 - 在子类中定义

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "db_type": self.db_type,
            "session_id": self.session_id,
            "sync_time": self.sync_time.isoformat() if self.sync_time else None,
            "status": self.status,
            "message": self.message,
            "error_message": self.error_message,
        }
