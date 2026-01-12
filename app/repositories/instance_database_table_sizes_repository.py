"""实例详情-数据库表容量 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import func

from app.models.database_table_size_stat import DatabaseTableSizeStat
from app.core.types.instance_database_table_sizes import (
    InstanceDatabaseTableSizeEntry,
    InstanceDatabaseTableSizesQuery,
    InstanceDatabaseTableSizesResult,
)


class InstanceDatabaseTableSizesRepository:
    """实例数据库表容量快照读模型 Repository."""

    def fetch_snapshot(self, options: InstanceDatabaseTableSizesQuery) -> InstanceDatabaseTableSizesResult:
        """获取指定实例/数据库的表容量快照分页数据.

        Args:
            options: 查询参数(实例/数据库/筛选条件/分页).

        Returns:
            InstanceDatabaseTableSizesResult: 表容量快照结果.

        """
        query = DatabaseTableSizeStat.query.filter(
            DatabaseTableSizeStat.instance_id == options.instance_id,
            DatabaseTableSizeStat.database_name == options.database_name,
        )

        if options.schema_name:
            query = query.filter(DatabaseTableSizeStat.schema_name.ilike(f"%{options.schema_name}%"))

        if options.table_name:
            query = query.filter(DatabaseTableSizeStat.table_name.ilike(f"%{options.table_name}%"))

        total = query.count()

        collected_at_value = query.with_entities(
            func.max(DatabaseTableSizeStat.collected_at),
        ).scalar()
        collected_at_dt = cast(datetime | None, collected_at_value)

        rows = (
            query.order_by(
                DatabaseTableSizeStat.size_mb.desc(),
                DatabaseTableSizeStat.schema_name.asc(),
                DatabaseTableSizeStat.table_name.asc(),
            )
            .offset(options.offset)
            .limit(options.limit)
            .all()
        )

        tables = [
            InstanceDatabaseTableSizeEntry(
                schema_name=row.schema_name,
                table_name=row.table_name,
                size_mb=row.size_mb,
                data_size_mb=row.data_size_mb,
                index_size_mb=row.index_size_mb,
                row_count=row.row_count,
                collected_at=row.collected_at.isoformat() if row.collected_at else None,
            )
            for row in rows
        ]

        return InstanceDatabaseTableSizesResult(
            total=total,
            limit=options.limit,
            offset=options.offset,
            collected_at=collected_at_dt.isoformat() if collected_at_dt else None,
            tables=tables,
        )
