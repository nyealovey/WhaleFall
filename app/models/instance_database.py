"""鲸落 - 实例数据库关系模型
用于维护实例包含哪些数据库,以及数据库的状态变化.
"""

from datetime import date

from app import db
from app.utils.time_utils import time_utils


class InstanceDatabase(db.Model):
    """实例-数据库关系模型.

    维护实例包含的数据库信息,跟踪数据库的存在状态和生命周期.
    支持数据库的首次发现、持续存在和删除状态的记录.

    Attributes:
        id: 主键 ID.
        instance_id: 关联的实例 ID.
        database_name: 数据库名称.
        is_active: 数据库是否活跃(未删除).
        first_seen_date: 首次发现日期.
        last_seen_date: 最后发现日期.
        deleted_at: 删除时间(软删除).
        created_at: 创建时间.
        updated_at: 更新时间.
        instance: 关联的实例对象.

    """

    __tablename__ = "instance_databases"

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    database_name = db.Column(db.String(255), nullable=False, comment="数据库名称")
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="数据库是否活跃(未删除)")
    first_seen_date = db.Column(db.Date, nullable=False, default=date.today, comment="首次发现日期")
    last_seen_date = db.Column(db.Date, nullable=False, default=date.today, comment="最后发现日期")
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, comment="删除时间")
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now, nullable=False)

    # 关系
    instance = db.relationship("Instance", back_populates="instance_databases")

    __table_args__ = (
        db.UniqueConstraint("instance_id", "database_name", name="uq_instance_database_instance_name"),
        db.Index("ix_instance_databases_database_name", "database_name"),
        db.Index("ix_instance_databases_active", "is_active"),
        db.Index("ix_instance_databases_last_seen", "last_seen_date"),
        {
            "comment": "实例-数据库关系表,维护数据库的存在状态",
        },
    )

    def __repr__(self) -> str:
        """返回实例数据库关系的调试字符串.

        Returns:
            str: 包含实例 ID、数据库名及活跃状态的文本.

        """
        return (
            f"<InstanceDatabase(id={self.id}, instance_id={self.instance_id}, "
            f"database_name='{self.database_name}', is_active={self.is_active})>"
        )
