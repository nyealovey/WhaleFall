"""鲸落 - 实例账户关系模型.

用于维护实例包含哪些账户,以及账户的存在状态.
"""

from app import db
from app.utils.time_utils import time_utils


class InstanceAccount(db.Model):
    """实例-账户关系模型.

    维护实例包含的账户信息,跟踪账户的存在状态和生命周期.
    支持账户的首次发现、持续存在和删除状态的记录.

    Attributes:
        id: 主键 ID.
        instance_id: 关联的实例 ID.
        username: 账户名(含必要的主机信息).
        db_type: 数据库类型.
        is_active: 账户是否活跃.
        first_seen_at: 首次发现时间.
        last_seen_at: 最后发现时间.
        deleted_at: 删除时间(软删除).
        created_at: 创建时间.
        updated_at: 更新时间.
        instance: 关联的实例对象.

    """

    __tablename__ = "instance_accounts"

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False, comment="账户名(对外展示,含必要的主机信息)")
    db_type = db.Column(db.String(50), nullable=False, comment="数据库类型")
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="账户是否活跃")
    first_seen_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=time_utils.now, comment="首次发现时间",
    )
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, comment="最后发现时间")
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, comment="删除时间")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    # 关系
    instance = db.relationship("Instance", back_populates="instance_accounts")

    __table_args__ = (
        db.UniqueConstraint("instance_id", "db_type", "username", name="uq_instance_account_instance_username"),
        db.Index("ix_instance_accounts_username", "username"),
        db.Index("ix_instance_accounts_active", "is_active"),
        db.Index("ix_instance_accounts_last_seen", "last_seen_at"),
        {
            "comment": "实例-账户关系表,维护账户存在状态",
        },
    )

    def __repr__(self) -> str:
        """返回实例账户关系的调试字符串.

        Returns:
            str: 展示实例 ID、账户名与激活状态的文本.

        """
        return (
            f"<InstanceAccount(id={self.id}, instance_id={self.instance_id}, "
            f"username='{self.username}', is_active={self.is_active})>"
        )
