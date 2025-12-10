"""实例大小聚合统计模型
存储实例级别的每周、每月、每季度的统计信息.
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
from app.types import NumericLike
from app.utils.time_utils import time_utils


class InstanceSizeAggregation(db.Model):
    """实例大小聚合统计表(分区表).

    存储实例级别的每日、每周、每月、每季度的聚合统计信息.
    按 period_start 字段按月分区,支持容量变化和增长率统计.

    Attributes:
        id: 主键 ID(BigInteger).
        instance_id: 关联的实例 ID.
        period_type: 统计周期类型(daily/weekly/monthly/quarterly).
        period_start: 统计周期开始日期(用于分区).
        period_end: 统计周期结束日期.
        total_size_mb: 实例总大小(MB).
        avg_size_mb: 平均大小(MB).
        max_size_mb: 最大大小(MB).
        min_size_mb: 最小大小(MB).
        data_count: 统计的数据点数量.
        database_count: 数据库数量.
        avg_database_count: 平均数据库数量.
        max_database_count: 最大数据库数量.
        min_database_count: 最小数据库数量.
        total_size_change_mb: 总大小变化(MB).
        total_size_change_percent: 总大小变化百分比.
        database_count_change: 数据库数量变化.
        database_count_change_percent: 数据库数量变化百分比.
        growth_rate: 增长率(百分比).

    """

    __tablename__ = "instance_size_aggregations"

    id = Column(BigInteger, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False)

    # 统计周期
    period_type = Column(String(20), nullable=False, comment="统计周期类型:daily, weekly, monthly, quarterly")
    period_start = Column(Date, nullable=False, comment="统计周期开始日期(用于分区)")
    period_end = Column(Date, nullable=False, comment="统计周期结束日期")

    # 实例总大小统计
    total_size_mb = Column(BigInteger, nullable=False, comment="实例总大小(MB)")
    avg_size_mb = Column(BigInteger, nullable=False, comment="平均大小(MB)")
    max_size_mb = Column(BigInteger, nullable=False, comment="最大大小(MB)")
    min_size_mb = Column(BigInteger, nullable=False, comment="最小大小(MB)")
    data_count = Column(Integer, nullable=False, comment="统计的数据点数量")

    # 数据库数量统计
    database_count = Column(Integer, nullable=False, comment="数据库数量")
    avg_database_count = Column(Numeric(10, 2), nullable=True, comment="平均数据库数量")
    max_database_count = Column(Integer, nullable=True, comment="最大数据库数量")
    min_database_count = Column(Integer, nullable=True, comment="最小数据库数量")

    # 变化统计
    total_size_change_mb = Column(BigInteger, nullable=True, comment="总大小变化(MB)")
    total_size_change_percent = Column(Numeric(10, 2), nullable=True, comment="总大小变化百分比")
    database_count_change = Column(Integer, nullable=True, comment="数据库数量变化")
    database_count_change_percent = Column(Numeric(10, 2), nullable=True, comment="数据库数量变化百分比")

    # 增长率
    growth_rate = Column(Numeric(10, 2), nullable=True, comment="增长率(百分比)")
    trend_direction = Column(String(20), nullable=True, comment="趋势方向:growing, shrinking, stable")

    # 时间戳
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=time_utils.now, comment="计算时间")
    created_at = Column(DateTime(timezone=True), nullable=False, default=time_utils.now, comment="记录创建时间")

    instance = relationship("Instance", back_populates="instance_size_aggregations")

    __table_args__ = (
        # 分区表约束 - 主键必须包含分区键
        # 注意:在分区表中,主键约束会自动包含分区键
        # 查询优化索引
        Index(
            "ix_instance_size_aggregations_instance_period",
            "instance_id",
            "period_type",
            "period_start",
        ),
        Index(
            "ix_instance_size_aggregations_period_type",
            "period_type",
            "period_start",
        ),
        UniqueConstraint(
            "instance_id",
            "period_type",
            "period_start",
            name="uq_instance_size_aggregation",
        ),
    )

    def __repr__(self) -> str:
        """返回实例聚合记录的字符串表示.

        Returns:
            str: 展示实例、周期与容量信息的调试文本.

        """
        return (
            f"<InstanceSizeAggregation(id={self.id}, instance_id={self.instance_id}, "
            f"period={self.period_type}, total={self.total_size_mb})>"
        )

    def to_dict(self) -> dict:
        """序列化实例聚合记录.

        Returns:
            dict: 包含周期、容量与趋势字段的 JSON 友好结构.

        """
        def _to_float(value: NumericLike) -> float | None:
            return float(value) if value is not None else None

        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "period_type": self.period_type,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "total_size_mb": self.total_size_mb,
            "avg_size_mb": self.avg_size_mb,
            "max_size_mb": self.max_size_mb,
            "min_size_mb": self.min_size_mb,
            "data_count": self.data_count,
            "database_count": self.database_count,
            "avg_database_count": _to_float(self.avg_database_count),
            "max_database_count": self.max_database_count,
            "min_database_count": self.min_database_count,
            "total_size_change_mb": self.total_size_change_mb,
            "total_size_change_percent": _to_float(self.total_size_change_percent),
            "database_count_change": self.database_count_change,
            "database_count_change_percent": _to_float(self.database_count_change_percent),
            "growth_rate": _to_float(self.growth_rate),
            "trend_direction": self.trend_direction,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
