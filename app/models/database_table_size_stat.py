"""数据库表容量快照模型.

存储每个实例下指定数据库的表级别容量快照,仅保留最新数据(不保留历史).
"""

from typing import TYPE_CHECKING, Unpack

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.types.orm_kwargs import DatabaseTableSizeStatOrmFields


class DatabaseTableSizeStat(db.Model):
    """数据库表容量快照模型.

    Attributes:
        id: 主键 ID(BigInteger).
        instance_id: 关联的实例 ID.
        database_name: 数据库名称.
        schema_name: Schema 名称.
        table_name: 表名称.
        size_mb: 表总大小(MB).
        data_size_mb: 数据大小(MB,如果可获取).
        index_size_mb: 索引大小(MB,如果可获取).
        row_count: 行数(可选,尽力而为).
        collected_at: 采集时间戳.
        created_at: 记录创建时间.
        updated_at: 记录更新时间.

    """

    __tablename__ = "database_table_size_stats"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False)
    database_name = Column(String(255), nullable=False, comment="数据库名称")
    schema_name = Column(String(255), nullable=False, comment="Schema 名称")
    table_name = Column(String(255), nullable=False, comment="表名称")
    size_mb = Column(BigInteger, nullable=False, comment="表总大小(MB)")
    data_size_mb = Column(BigInteger, nullable=True, comment="数据大小(MB),如果可获取")
    index_size_mb = Column(BigInteger, nullable=True, comment="索引大小(MB),如果可获取")
    row_count = Column(BigInteger, nullable=True, comment="行数(可选,尽力而为)")
    collected_at = Column(DateTime(timezone=True), nullable=False, default=time_utils.now, comment="采集时间戳")
    created_at = Column(DateTime(timezone=True), nullable=False, default=time_utils.now, comment="记录创建时间")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=time_utils.now,
        onupdate=time_utils.now,
        comment="记录更新时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "instance_id",
            "database_name",
            "schema_name",
            "table_name",
            name="uq_database_table_size_stats_key",
        ),
        Index(
            "ix_database_table_size_stats_instance_database",
            "instance_id",
            "database_name",
        ),
        Index(
            "ix_database_table_size_stats_instance_database_size",
            "instance_id",
            "database_name",
            "size_mb",
        ),
    )

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[DatabaseTableSizeStatOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...

    def __repr__(self) -> str:
        return (
            f"<DatabaseTableSizeStat(id={self.id}, instance_id={self.instance_id}, "
            f"db='{self.database_name}', schema='{self.schema_name}', table='{self.table_name}', "
            f"size_mb={self.size_mb})>"
        )
