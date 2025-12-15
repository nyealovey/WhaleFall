"""数据库大小统计模型.

存储每个数据库在特定时间点的大小统计信息。
支持 PostgreSQL 分区表,并按日期进行分区管理。
"""

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app import db
from app.utils.time_utils import time_utils


class DatabaseSizeStat(db.Model):
    """数据库大小统计模型.

    存储每个数据库在特定时间点的大小统计信息.
    支持 PostgreSQL 分区表,按日期(collected_date)分区.

    Attributes:
        id: 主键 ID(BigInteger).
        instance_id: 关联的实例 ID.
        database_name: 数据库名称.
        size_mb: 数据库总大小(MB).
        data_size_mb: 数据部分大小(MB,如果可获取).
        log_size_mb: 日志部分大小(MB,SQL Server 特有).
        collected_date: 采集日期(用于分区).
        collected_at: 采集时间戳.
        created_at: 记录创建时间.
        updated_at: 记录更新时间.
        instance: 关联的实例对象.

    """

    __tablename__ = "database_size_stats"

    id = Column(BigInteger, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False)
    database_name = Column(String(255), nullable=False, comment="数据库名称")
    size_mb = Column(BigInteger, nullable=False, comment="数据库总大小(MB)")
    data_size_mb = Column(
        BigInteger,
        nullable=True,
        comment="数据部分大小(MB),如果可获取",
    )
    log_size_mb = Column(
        BigInteger,
        nullable=True,
        comment="日志部分大小(MB),如果可获取(SQL Server)",
    )
    collected_date = Column(Date, nullable=False, comment="采集日期(用于分区)")
    collected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=time_utils.now,
        comment="采集时间戳",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=time_utils.now,
        comment="记录创建时间",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=time_utils.now,
        onupdate=time_utils.now,
        comment="记录更新时间",
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
            name="uq_daily_database_size",
        ),
        # 查询优化索引
        Index(
            "ix_database_size_stats_instance_date",
            "instance_id",
            "collected_date",
        ),
    )

    def __repr__(self) -> str:
        """返回统计记录的文本表示.

        Returns:
            str: 包含实例与采集日期的调试信息.

        """
        return (
            f"<DatabaseSizeStat(id={self.id}, instance_id={self.instance_id}, "
            f"db='{self.database_name}', size_mb={self.size_mb}, date={self.collected_date})>"
        )

    def to_dict(self) -> dict:
        """序列化统计记录.

        将日期与时间字段转换为 ISO 字符串,以便 API 响应或任务日志消费.

        Returns:
            dict: 含大小指标与采集时间的序列化结果.

        """
        collected_date = self.collected_date.isoformat() if self.collected_date is not None else None
        collected_at = self.collected_at.isoformat() if self.collected_at is not None else None
        created_at = self.created_at.isoformat() if self.created_at is not None else None
        updated_at = self.updated_at.isoformat() if self.updated_at is not None else None

        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "database_name": self.database_name,
            "size_mb": self.size_mb,
            "data_size_mb": self.data_size_mb,
            "log_size_mb": self.log_size_mb,
            "collected_date": collected_date,
            "collected_at": collected_at,
            "created_at": created_at,
            "updated_at": updated_at,
        }
