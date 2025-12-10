"""数据库大小聚合统计模型
存储每周、每月、每季度的统计信息.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app import db
from app.utils.time_utils import time_utils


class DatabaseSizeAggregation(db.Model):
    """数据库大小聚合统计表(分区表).

    存储每周、每月、每季度的数据库大小聚合统计信息.
    按 period_start 字段按月分区,支持增量/减量统计.

    Attributes:
        id: 主键 ID(BigInteger).
        instance_id: 关联的实例 ID.
        database_name: 数据库名称.
        period_type: 统计周期类型(weekly/monthly/quarterly).
        period_start: 统计周期开始日期(用于分区).
        period_end: 统计周期结束日期.
        avg_size_mb: 平均大小(MB).
        max_size_mb: 最大大小(MB).
        min_size_mb: 最小大小(MB).
        data_count: 统计的数据点数量.
        avg_data_size_mb: 平均数据大小(MB).
        max_data_size_mb: 最大数据大小(MB).
        min_data_size_mb: 最小数据大小(MB).
        avg_log_size_mb: 平均日志大小(MB,SQL Server).
        max_log_size_mb: 最大日志大小(MB,SQL Server).
        min_log_size_mb: 最小日志大小(MB,SQL Server).
        size_change_mb: 总大小变化量(MB,可为负值).
        size_change_percent: 总大小变化百分比(%,可为负值).
        data_size_change_mb: 数据大小变化量(MB,可为负值).

    """

    __tablename__ = "database_size_aggregations"

    id = Column(BigInteger, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False)
    database_name = Column(String(255), nullable=False, comment="数据库名称")

    # 统计周期
    period_type = Column(String(20), nullable=False, comment="统计周期类型:weekly, monthly, quarterly")
    period_start = Column(Date, nullable=False, comment="统计周期开始日期(用于分区)")
    period_end = Column(Date, nullable=False, comment="统计周期结束日期")

    # 统计指标
    avg_size_mb = Column(BigInteger, nullable=False, comment="平均大小(MB)")
    max_size_mb = Column(BigInteger, nullable=False, comment="最大大小(MB)")
    min_size_mb = Column(BigInteger, nullable=False, comment="最小大小(MB)")
    data_count = Column(Integer, nullable=False, comment="统计的数据点数量")

    avg_data_size_mb = Column(BigInteger, nullable=True, comment="平均数据大小(MB)")
    max_data_size_mb = Column(BigInteger, nullable=True, comment="最大数据大小(MB)")
    min_data_size_mb = Column(BigInteger, nullable=True, comment="最小数据大小(MB)")

    # 日志大小统计(SQL Server)
    avg_log_size_mb = Column(BigInteger, nullable=True, comment="平均日志大小(MB)")
    max_log_size_mb = Column(BigInteger, nullable=True, comment="最大日志大小(MB)")
    min_log_size_mb = Column(BigInteger, nullable=True, comment="最小日志大小(MB)")

    # 增量/减量统计字段
    size_change_mb = Column(BigInteger, nullable=False, default=0, comment="总大小变化量(MB,可为负值)")
    size_change_percent = Column(Numeric(10, 2), nullable=False, default=0, comment="总大小变化百分比(%,可为负值)")
    data_size_change_mb = Column(BigInteger, nullable=True, comment="数据大小变化量(MB,可为负值)")
    data_size_change_percent = Column(Numeric(10, 2), nullable=True, comment="数据大小变化百分比(%,可为负值)")
    log_size_change_mb = Column(BigInteger, nullable=True, comment="日志大小变化量(MB,可为负值)")
    log_size_change_percent = Column(Numeric(10, 2), nullable=True, comment="日志大小变化百分比(%,可为负值)")

    # 增长率字段
    growth_rate = Column(Numeric(10, 2), nullable=False, default=0, comment="增长率(%,可为负值)")

    # 时间字段
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=time_utils.now, comment="计算时间")
    created_at = Column(DateTime(timezone=True), nullable=False, default=time_utils.now, comment="记录创建时间")

    instance = relationship("Instance", back_populates="database_size_aggregations")

    __table_args__ = (
        # 分区表约束 - 主键必须包含分区键
        # 注意:在分区表中,主键约束会自动包含分区键
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
        UniqueConstraint(
            "instance_id",
            "database_name",
            "period_type",
            "period_start",
            name="uq_database_size_aggregation",
        ),
    )

    def __repr__(self) -> str:
        """返回聚合记录的调试字符串.

        Returns:
            str: 包含实例、数据库与周期信息的可读文本.

        """
        return (
            f"<DatabaseSizeAggregation(id={self.id}, instance_id={self.instance_id}, "
            f"db='{self.database_name}', period={self.period_type}, avg={self.avg_size_mb})>"
        )

    def to_dict(self) -> dict:
        """序列化聚合记录.

        将日期与 Decimal 等字段转换为 JSON 友好的基础类型,便于响应体或日志输出.

        Returns:
            dict: 包含统计周期、大小指标与增长率的字典数据.

        """
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "database_name": self.database_name,
            "period_type": self.period_type,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "avg_size_mb": self.avg_size_mb,
            "max_size_mb": self.max_size_mb,
            "min_size_mb": self.min_size_mb,
            "data_count": self.data_count,
            "avg_data_size_mb": self.avg_data_size_mb,
            "max_data_size_mb": self.max_data_size_mb,
            "min_data_size_mb": self.min_data_size_mb,
            "avg_log_size_mb": self.avg_log_size_mb,
            "max_log_size_mb": self.max_log_size_mb,
            "min_log_size_mb": self.min_log_size_mb,
            # 增量/减量统计
            "size_change_mb": self.size_change_mb,
            "size_change_percent": float(self.size_change_percent) if self.size_change_percent else 0,
            "data_size_change_mb": self.data_size_change_mb,
            "data_size_change_percent": float(self.data_size_change_percent) if self.data_size_change_percent else None,
            "log_size_change_mb": self.log_size_change_mb,
            "log_size_change_percent": float(self.log_size_change_percent) if self.log_size_change_percent else None,
            # 增长率
            "growth_rate": float(self.growth_rate) if self.growth_rate else 0,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
