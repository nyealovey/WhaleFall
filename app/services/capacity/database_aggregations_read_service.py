"""数据库容量聚合读取 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import cast

from app.core.types.capacity_common import CapacityInstanceRef
from app.core.types.capacity_databases import (
    DatabaseAggregationsFilters,
    DatabaseAggregationsItem,
    DatabaseAggregationsListResult,
    DatabaseAggregationsSummary,
    DatabaseAggregationsSummaryFilters,
)
from app.repositories.capacity_databases_repository import CapacityDatabasesRepository


class DatabaseAggregationsReadService:
    """数据库容量聚合读取服务."""

    def __init__(self, repository: CapacityDatabasesRepository | None = None) -> None:
        """初始化服务并注入仓库."""
        self._repository = repository or CapacityDatabasesRepository()

    def list_aggregations(self, filters: DatabaseAggregationsFilters) -> DatabaseAggregationsListResult:
        """分页查询数据库容量聚合."""
        rows, total = self._repository.list_aggregations(filters)

        items: list[DatabaseAggregationsItem] = []
        for aggregation, instance in rows:
            aggregation_id = cast(int, aggregation.id)
            aggregation_instance_id = cast(int, aggregation.instance_id)
            database_name = cast(str, aggregation.database_name)
            period_type = cast(str, aggregation.period_type)
            period_start = cast("date | None", aggregation.period_start)
            period_end = cast("date | None", aggregation.period_end)
            avg_size_mb = cast(int | None, aggregation.avg_size_mb)
            max_size_mb = cast(int | None, aggregation.max_size_mb)
            min_size_mb = cast(int | None, aggregation.min_size_mb)
            data_count = cast(int | None, aggregation.data_count)
            avg_data_size_mb = cast(int | None, aggregation.avg_data_size_mb)
            max_data_size_mb = cast(int | None, aggregation.max_data_size_mb)
            min_data_size_mb = cast(int | None, aggregation.min_data_size_mb)
            avg_log_size_mb = cast(int | None, aggregation.avg_log_size_mb)
            max_log_size_mb = cast(int | None, aggregation.max_log_size_mb)
            min_log_size_mb = cast(int | None, aggregation.min_log_size_mb)
            size_change_mb = cast(int | None, aggregation.size_change_mb)
            size_change_percent = cast(Decimal | None, aggregation.size_change_percent)
            data_size_change_mb = cast(int | None, aggregation.data_size_change_mb)
            data_size_change_percent = cast(Decimal | None, aggregation.data_size_change_percent)
            log_size_change_mb = cast(int | None, aggregation.log_size_change_mb)
            log_size_change_percent = cast(Decimal | None, aggregation.log_size_change_percent)
            growth_rate = cast(Decimal | None, aggregation.growth_rate)
            calculated_at = cast("datetime | None", aggregation.calculated_at)
            created_at = cast("datetime | None", aggregation.created_at)

            instance_id = cast(int, instance.id)
            instance_name = cast(str, instance.name)
            instance_db_type = cast(str, instance.db_type)

            items.append(
                DatabaseAggregationsItem(
                    id=int(aggregation_id),
                    instance_id=int(aggregation_instance_id),
                    database_name=database_name,
                    period_type=period_type,
                    period_start=period_start.isoformat() if period_start else None,
                    period_end=period_end.isoformat() if period_end else None,
                    avg_size_mb=int(avg_size_mb or 0),
                    max_size_mb=int(max_size_mb or 0),
                    min_size_mb=int(min_size_mb or 0),
                    data_count=int(data_count or 0),
                    avg_data_size_mb=(int(avg_data_size_mb) if avg_data_size_mb is not None else None),
                    max_data_size_mb=(int(max_data_size_mb) if max_data_size_mb is not None else None),
                    min_data_size_mb=(int(min_data_size_mb) if min_data_size_mb is not None else None),
                    avg_log_size_mb=(int(avg_log_size_mb) if avg_log_size_mb is not None else None),
                    max_log_size_mb=(int(max_log_size_mb) if max_log_size_mb is not None else None),
                    min_log_size_mb=(int(min_log_size_mb) if min_log_size_mb is not None else None),
                    size_change_mb=int(size_change_mb or 0),
                    size_change_percent=float(size_change_percent) if size_change_percent is not None else 0.0,
                    data_size_change_mb=(int(data_size_change_mb) if data_size_change_mb is not None else None),
                    data_size_change_percent=(
                        float(data_size_change_percent) if data_size_change_percent is not None else None
                    ),
                    log_size_change_mb=(int(log_size_change_mb) if log_size_change_mb is not None else None),
                    log_size_change_percent=(
                        float(log_size_change_percent) if log_size_change_percent is not None else None
                    ),
                    growth_rate=float(growth_rate) if growth_rate is not None else 0.0,
                    calculated_at=calculated_at.isoformat() if calculated_at else None,
                    created_at=created_at.isoformat() if created_at else None,
                    instance=CapacityInstanceRef(
                        id=int(instance_id),
                        name=instance_name,
                        db_type=instance_db_type,
                    ),
                ),
            )

        if filters.get_all:
            return DatabaseAggregationsListResult(
                items=items,
                total=len(items),
                page=1,
                pages=1,
                limit=len(items),
                has_prev=False,
                has_next=False,
            )

        pages = (total + filters.limit - 1) // filters.limit if total else 0
        return DatabaseAggregationsListResult(
            items=items,
            total=total,
            page=filters.page,
            pages=pages,
            limit=filters.limit,
            has_prev=filters.page > 1,
            has_next=filters.page < pages,
        )

    def build_summary(self, filters: DatabaseAggregationsSummaryFilters) -> DatabaseAggregationsSummary:
        """汇总数据库容量概览数据."""
        total_databases, total_instances, total_size_mb, avg_size_mb, max_size_mb = (
            self._repository.summarize_latest_aggregations(filters)
        )
        return DatabaseAggregationsSummary(
            total_databases=total_databases,
            total_instances=total_instances,
            total_size_mb=total_size_mb,
            avg_size_mb=avg_size_mb,
            max_size_mb=max_size_mb,
            growth_rate=0.0,
        )
