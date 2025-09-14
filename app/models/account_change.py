"""
泰摸鱼吧 - 账户变化跟踪模型
"""

from datetime import datetime

from app import db


class AccountChange(db.Model):
    """账户变化跟踪模型"""

    __tablename__ = "account_changes"

    id = db.Column(db.Integer, primary_key=True)
    sync_data_id = db.Column(db.Integer, nullable=True)  # 移除外键约束，因为sync_data表已删除
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False)
    change_type = db.Column(db.String(20), nullable=False)  # 'added', 'removed', 'modified'
    account_data = db.Column(db.JSON, nullable=False)  # 账户的完整信息
    change_time = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # 关联关系
    # sync_data关系已移除，因为SyncData表已删除
    instance = db.relationship("Instance", backref="account_changes")

    def __init__(self, sync_data_id: int, instance_id: int, change_type: str, account_data: dict) -> None:
        """
        初始化账户变化记录

        Args:
            sync_data_id: 同步数据ID
            instance_id: 实例ID
            change_type: 变化类型 ('added', 'removed', 'modified')
            account_data: 账户数据
        """
        self.sync_data_id = sync_data_id
        self.instance_id = instance_id
        self.change_type = change_type
        self.account_data = account_data

    def to_dict(self) -> dict:
        """
        转换为字典

        Returns:
            dict: 账户变化字典
        """
        return {
            "id": self.id,
            "sync_data_id": self.sync_data_id,
            "instance_id": self.instance_id,
            "change_type": self.change_type,
            "account_data": self.account_data,
            "change_time": self.change_time.isoformat() if self.change_time else None,
            "instance_name": self.instance.name if self.instance else "未知实例",
        }

    @staticmethod
    def get_changes_by_sync(sync_data_id: int) -> list:
        """
        获取指定同步的账户变化

        Args:
            sync_data_id: 同步数据ID

        Returns:
            list: 账户变化列表
        """
        return AccountChange.query.filter_by(sync_data_id=sync_data_id).all()

    @staticmethod
    def get_changes_by_instance(instance_id: int, limit: int = 100) -> list:
        """
        获取指定实例的账户变化历史

        Args:
            instance_id: 实例ID
            limit: 限制数量

        Returns:
            list: 账户变化列表
        """
        return (
            AccountChange.query.filter_by(instance_id=instance_id)
            .order_by(AccountChange.change_time.desc())
            .limit(limit)
            .all()
        )

    def __repr__(self) -> str:
        return f"<AccountChange {self.change_type} for account {self.account_data.get('username', 'Unknown')}>"
