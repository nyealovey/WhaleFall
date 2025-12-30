"""鲸落 - 账户权限快照数据模型."""

from app import db
from app.models.base_sync_data import BaseSyncData
from app.utils.time_utils import time_utils
from sqlalchemy.dialects import postgresql


class AccountPermission(BaseSyncData):
    """账户权限快照(支持复杂权限结构).

    存储账户权限的版本化 snapshot(v4) 与 facts(用于统计/规则评估),
    不再使用按 db_type 固定列的 legacy 权限字段.继承自 BaseSyncData.

    Attributes:
        instance_account_id: 关联的实例账户 ID.
        username: 账户名.
        is_superuser: 是否为超级用户.
        is_locked: 是否被锁定.
        type_specific: 其他类型特定字段(JSON).
        permission_snapshot: 权限快照(v4, jsonb).
        permission_facts: 权限事实(用于统计/查询, jsonb).
        last_sync_time: 最后同步时间.

    """

    __tablename__ = "account_permission"

    __table_args__ = (
        db.UniqueConstraint("instance_id", "db_type", "username", name="uq_account_permission"),
        db.Index("idx_account_permission_instance_dbtype", "instance_id", "db_type"),
        db.Index("idx_account_permission_username", "username"),
    )

    instance_account_id = db.Column(db.Integer, db.ForeignKey("instance_accounts.id"), nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False)
    is_superuser = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # 通用扩展字段
    type_specific = db.Column(db.JSON, nullable=True)  # 其他类型特定字段

    # 权限快照(v4)
    permission_snapshot = db.Column(
        db.JSON().with_variant(postgresql.JSONB(), "postgresql"),
        nullable=True,
    )

    # 权限事实(用于统计/查询)
    permission_facts = db.Column(
        db.JSON().with_variant(postgresql.JSONB(), "postgresql"),
        nullable=True,
    )

    # 时间戳和状态字段
    last_sync_time = db.Column(db.DateTime(timezone=True), default=time_utils.now, index=True)
    last_change_type = db.Column(db.String(20), default="add")
    last_change_time = db.Column(db.DateTime(timezone=True), default=time_utils.now, index=True)

    instance = db.relationship("Instance", backref="account_permissions")
    instance_account = db.relationship(
        "InstanceAccount",
        backref=db.backref("current_sync", uselist=False),
    )

    def __repr__(self) -> str:
        """Return concise account permission label.

        Returns:
            str: `<AccountPermission username@db>` 格式.

        """
        return f"<AccountPermission {self.username}@{self.db_type}>"

    def to_dict(self) -> dict:
        """转换为字典.

        Returns:
            dict: 包含权限快照及基础字段的字典.

        """
        base_dict = super().to_dict()
        base_dict.update(
            {
                "username": self.username,
                "is_superuser": self.is_superuser,
                "is_locked": self.is_locked,
                "type_specific": self.type_specific,
                "permission_snapshot": self.permission_snapshot,
                "permission_facts": self.permission_facts,
                "last_sync_time": (self.last_sync_time.isoformat() if self.last_sync_time else None),
                "last_change_type": self.last_change_type,
                "last_change_time": (self.last_change_time.isoformat() if self.last_change_time else None),
                "instance_account_id": self.instance_account_id,
            },
        )
        return base_dict
