"""鲸落 - 实例大小统计模型.

存储数据库实例的总大小统计数据.
"""

from app import db
from app.utils.time_utils import time_utils


class InstanceSizeStat(db.Model):
    """实例大小统计模型.

    存储数据库实例的总大小统计数据,按日期记录实例的容量变化.
    支持软删除和历史数据追踪.

    Attributes:
        id: 主键 ID(与 collected_date 组成复合主键).
        instance_id: 关联的实例 ID.
        total_size_mb: 实例总大小(MB).
        database_count: 数据库数量.
        collected_date: 采集日期(分区键,复合主键之一).
        collected_at: 采集时间.
        is_deleted: 是否已删除.
        deleted_at: 删除时间.
        created_at: 创建时间.
        updated_at: 更新时间.
        instance: 关联的实例对象.

    """

    __tablename__ = "instance_size_stats"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    total_size_mb = db.Column(db.Integer, nullable=False, default=0, comment="实例总大小(MB)")
    database_count = db.Column(db.Integer, nullable=False, default=0, comment="数据库数量")
    collected_date = db.Column(db.Date, primary_key=True, nullable=False, index=True, comment="采集日期")
    collected_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, comment="采集时间")
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True, comment="是否已删除")
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, comment="删除时间")
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, comment="创建时间")
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=time_utils.now,
        onupdate=time_utils.now,
        comment="更新时间",
    )

    # 关系
    instance = db.relationship("Instance", back_populates="instance_size_stats")

    def __repr__(self) -> str:
        """返回实例大小记录的字符串表示.

        Returns:
            str: 含实例 ID、容量与采集日期的调试文本.

        """
        return (
            f"<InstanceSizeStat(instance_id={self.instance_id}, total_size_mb={self.total_size_mb}, "
            f"collected_date={self.collected_date})>"
        )

    def to_dict(self) -> dict:
        """序列化实例大小记录.

        Returns:
            dict: 包含容量、时间戳和软删除信息的字典.

        """
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "total_size_mb": self.total_size_mb,
            "database_count": self.database_count,
            "collected_date": self.collected_date.isoformat() if self.collected_date else None,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
