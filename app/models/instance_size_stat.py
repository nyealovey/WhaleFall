"""
鲸落 - 实例大小统计模型
存储数据库实例的总大小统计数据
"""

from datetime import date
from app import db
from app.utils.timezone import now


class InstanceSizeStat(db.Model):
    """实例大小统计模型"""

    __tablename__ = "instance_size_stats"

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    total_size_mb = db.Column(db.Integer, nullable=False, default=0, comment="实例总大小（MB）")
    database_count = db.Column(db.Integer, nullable=False, default=0, comment="数据库数量")
    collected_date = db.Column(db.Date, nullable=False, index=True, comment="采集日期")
    collected_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now, comment="采集时间")
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True, comment="是否已删除")
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, comment="删除时间")
    created_at = db.Column(db.DateTime(timezone=True), default=now, comment="创建时间")
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now, comment="更新时间")

    # 关系
    instance = db.relationship("Instance", back_populates="instance_size_stats")

    def __repr__(self):
        return f"<InstanceSizeStat(instance_id={self.instance_id}, total_size_mb={self.total_size_mb}, collected_date={self.collected_date})>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'instance_id': self.instance_id,
            'total_size_mb': self.total_size_mb,
            'database_count': self.database_count,
            'collected_date': self.collected_date.isoformat() if self.collected_date else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
