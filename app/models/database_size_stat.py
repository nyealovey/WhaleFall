"""
数据库大小统计模型
存储每个数据库在特定时间点的大小统计信息
支持 PostgreSQL 分区表，按日期分区
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    BigInteger,
    Boolean,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app import db
import datetime


class DatabaseSizeStat(db.Model):
    """
    存储每个数据库在特定时间点的大小统计信息。
    支持 PostgreSQL 分区表，按日期分区。
    """

    __tablename__ = "database_size_stats"

    id = Column(BigInteger, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False)
    database_name = Column(String(255), nullable=False, comment="数据库名称")
    size_mb = Column(BigInteger, nullable=False, comment="数据库总大小（MB）")
    data_size_mb = Column(
        BigInteger, nullable=True, comment="数据部分大小（MB），如果可获取"
    )
    log_size_mb = Column(
        BigInteger, nullable=True, comment="日志部分大小（MB），如果可获取（SQL Server）"
    )
    collected_date = Column(Date, nullable=False, comment="采集日期（用于分区）")
    collected_at = Column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, comment="采集时间戳"
    )
    is_deleted = Column(
        Boolean, nullable=False, default=False, comment="是否已删除（软删除）"
    )
    deleted_at = Column(
        DateTime, nullable=True, comment="删除时间"
    )
    created_at = Column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, comment="记录创建时间"
    )

    instance = relationship("Instance", back_populates="database_size_stats")

    __table_args__ = (
        # 分区表约束
        Index(
            "ix_database_size_stats_collected_date",
            "collected_date",
        ),
        # 每日唯一性约束
        UniqueConstraint(
            "instance_id",
            "database_name", 
            "collected_date",
            name="uq_daily_database_size"
        ),
        # 查询优化索引
        Index(
            "ix_database_size_stats_instance_date",
            "instance_id",
            "collected_date",
        ),
    )

    def __repr__(self):
        return f"<DatabaseSizeStat(id={self.id}, instance_id={self.instance_id}, db='{self.database_name}', size_mb={self.size_mb}, date={self.collected_date})>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'instance_id': self.instance_id,
            'database_name': self.database_name,
            'size_mb': self.size_mb,
            'data_size_mb': self.data_size_mb,
            'log_size_mb': self.log_size_mb,
            'collected_date': self.collected_date.isoformat() if self.collected_date else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
