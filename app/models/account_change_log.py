"""
泰摸鱼吧 - 账户变更日志模型
"""

from datetime import datetime

from app import db


class AccountChangeLog(db.Model):
    """账户变更日志表"""

    __tablename__ = "account_change_log"

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    db_type = db.Column(db.String(20), nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False, index=True)
    change_type = db.Column(db.String(50), nullable=False)  # 'add', 'modify_privilege', 'modify_other', 'delete'
    change_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    session_id = db.Column(db.String(36), nullable=True)
    status = db.Column(db.String(20), default="success")
    message = db.Column(db.Text, nullable=True)

    # 变更差异
    privilege_diff = db.Column(db.JSON, nullable=True)  # 权限变更差异
    other_diff = db.Column(db.JSON, nullable=True)  # 其他字段变更差异

    __table_args__ = (
        db.Index(
            "idx_instance_dbtype_username_time",
            "instance_id",
            "db_type",
            "username",
            "change_time",
        ),
        db.Index("idx_change_type_time", "change_type", "change_time"),
        db.Index("idx_username_time", "username", "change_time"),
    )

    # 关联实例
    instance = db.relationship("Instance")

    def __repr__(self) -> str:
        return f"<AccountChangeLog {self.username}@{self.db_type}:{self.change_type}>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "db_type": self.db_type,
            "username": self.username,
            "change_type": self.change_type,
            "change_time": self.change_time.isoformat() if self.change_time else None,
            "session_id": self.session_id,
            "status": self.status,
            "message": self.message,
            "privilege_diff": self.privilege_diff,
            "other_diff": self.other_diff,
        }
