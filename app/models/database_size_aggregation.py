"""
数据库大小聚合统计模型
存储每周、每月、每季度的统计信息
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    BigInteger,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.models.base import Base
import datetime


class DatabaseSizeAggregation(Base):
    """
    数据库大小聚合统计表
    存储每周、每月、每季度的统计信息
    """
    
    __tablename__ = "database_size_aggregations"
    
    id = Column(BigInteger, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False)
    database_name = Column(String(255), nullable=False, comment="数据库名称")
    
    # 统计周期
    period_type = Column(String(20), nullable=False, comment="统计周期类型：weekly, monthly, quarterly")
    period_start = Column(Date, nullable=False, comment="统计周期开始日期")
    period_end = Column(Date, nullable=False, comment="统计周期结束日期")
    
    # 统计指标
    avg_size_mb = Column(BigInteger, nullable=False, comment="平均大小（MB）")
    max_size_mb = Column(BigInteger, nullable=False, comment="最大大小（MB）")
    min_size_mb = Column(BigInteger, nullable=False, comment="最小大小（MB）")
    data_count = Column(Integer, nullable=False, comment="统计的数据点数量")
    
    # 数据大小统计（如果可获取）
    avg_data_size_mb = Column(BigInteger, nullable=True, comment="平均数据大小（MB）")
    max_data_size_mb = Column(BigInteger, nullable=True, comment="最大数据大小（MB）")
    min_data_size_mb = Column(BigInteger, nullable=True, comment="最小数据大小（MB）")
    
    # 日志大小统计（SQL Server）
    avg_log_size_mb = Column(BigInteger, nullable=True, comment="平均日志大小（MB）")
    max_log_size_mb = Column(BigInteger, nullable=True, comment="最大日志大小（MB）")
    min_log_size_mb = Column(BigInteger, nullable=True, comment="最小日志大小（MB）")
    
    # 时间字段
    calculated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, comment="计算时间")
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, comment="记录创建时间")
    
    instance = relationship("Instance", back_populates="database_size_aggregations")
    
    __table_args__ = (
        # 唯一约束
        UniqueConstraint(
            "instance_id",
            "database_name",
            "period_type",
            "period_start",
            name="uq_database_size_aggregation"
        ),
        # 查询优化索引
        Index(
            "ix_database_size_aggregations_instance_period",
            "instance_id",
            "period_type",
            "period_start",
        ),
        Index(
            "ix_database_size_aggregations_period_type",
            "period_type",
            "period_start",
        ),
    )
    
    def __repr__(self):
        return f"<DatabaseSizeAggregation(id={self.id}, instance_id={self.instance_id}, db='{self.database_name}', period={self.period_type}, avg={self.avg_size_mb})>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'instance_id': self.instance_id,
            'database_name': self.database_name,
            'period_type': self.period_type,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'avg_size_mb': self.avg_size_mb,
            'max_size_mb': self.max_size_mb,
            'min_size_mb': self.min_size_mb,
            'data_count': self.data_count,
            'avg_data_size_mb': self.avg_data_size_mb,
            'max_data_size_mb': self.max_data_size_mb,
            'min_data_size_mb': self.min_data_size_mb,
            'avg_log_size_mb': self.avg_log_size_mb,
            'max_log_size_mb': self.max_log_size_mb,
            'min_log_size_mb': self.min_log_size_mb,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
