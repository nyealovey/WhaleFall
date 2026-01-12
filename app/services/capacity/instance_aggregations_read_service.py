"""实例容量聚合读取 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import cast

from app.repositories.capacity_instances_repository import CapacityInstancesRepository
from app.core.types.capacity_common import CapacityInstanceRef
from app.core.types.capacity_instances import (
    InstanceAggregationsFilters,
    InstanceAggregationsItem,
    InstanceAggregationsListResult,
    InstanceAggregationsSummary,
    InstanceAggregationsSummaryFilters,
)


class InstanceAggregationsReadService:
    """实例容量聚合读取服务."""

    def __init__(self, repository: CapacityInstancesRepository | None = None) -> None:
        """初始化服务并注入仓库."""
        self._repository = repository or CapacityInstancesRepository()

    def list_aggregations(self, filters: InstanceAggregationsFilters) -> InstanceAggregationsListResult:
        """分页查询实例容量聚合."""
        rows, total = self._repository.list_aggregations(filters)

        items: list[InstanceAggregationsItem] = []
        for aggregation, instance in rows:
            aggregation_id = cast(int, aggregation.id)
            aggregation_instance_id = cast(int, aggregation.instance_id)
            period_type = cast(str, aggregation.period_type)
            period_start = cast("date | None", aggregation.period_start)
            period_end = cast("date | None", aggregation.period_end)
            total_size_mb = cast(int | None, aggregation.total_size_mb)
            avg_size_mb = cast(int | None, aggregation.avg_size_mb)
            max_size_mb = cast(int | None, aggregation.max_size_mb)
            min_size_mb = cast(int | None, aggregation.min_size_mb)
            data_count = cast(int | None, aggregation.data_count)
            database_count = cast(int | None, aggregation.database_count)
            avg_database_count = cast(Decimal | None, aggregation.avg_database_count)
            max_database_count = cast(int | None, aggregation.max_database_count)
            min_database_count = cast(int | None, aggregation.min_database_count)
            total_size_change_mb = cast(int | None, aggregation.total_size_change_mb)
            total_size_change_percent = cast(Decimal | None, aggregation.total_size_change_percent)
            database_count_change = cast(int | None, aggregation.database_count_change)
            database_count_change_percent = cast(Decimal | None, aggregation.database_count_change_percent)
            growth_rate = cast(Decimal | None, aggregation.growth_rate)
            trend_direction = cast(str | None, aggregation.trend_direction)
            calculated_at = cast("datetime | None", aggregation.calculated_at)
            created_at = cast("datetime | None", aggregation.created_at)

            instance_id = cast(int, instance.id)
            instance_name = cast(str, instance.name)
            instance_db_type = cast(str, instance.db_type)

            items.append(
                InstanceAggregationsItem(
                    id=int(aggregation_id),
                    instance_id=int(aggregation_instance_id),
                    period_type=period_type,
                    period_start=period_start.isoformat() if period_start else None,
                    period_end=period_end.isoformat() if period_end else None,
                    total_size_mb=int(total_size_mb or 0),
                    avg_size_mb=int(avg_size_mb or 0),
                    max_size_mb=int(max_size_mb or 0),
                    min_size_mb=int(min_size_mb or 0),
                    data_count=int(data_count or 0),
                    database_count=int(database_count or 0),
                    avg_database_count=(float(avg_database_count) if avg_database_count is not None else None),
                    max_database_count=(int(max_database_count) if max_database_count is not None else None),
                    min_database_count=(int(min_database_count) if min_database_count is not None else None),
                    total_size_change_mb=(int(total_size_change_mb) if total_size_change_mb is not None else None),
                    total_size_change_percent=(
                        float(total_size_change_percent) if total_size_change_percent is not None else None
                    ),
                    database_count_change=(int(database_count_change) if database_count_change is not None else None),
                    database_count_change_percent=(
                        float(database_count_change_percent) if database_count_change_percent is not None else None
                    ),
                    growth_rate=float(growth_rate) if growth_rate is not None else None,
                    trend_direction=trend_direction,
                    calculated_at=calculated_at.isoformat() if calculated_at else None,
                    created_at=created_at.isoformat() if created_at else None,
                    instance=CapacityInstanceRef(
                        id=int(instance_id),
                        name=instance_name,
                        db_type=instance_db_type,
                    ),
                ),
            )

        pages = max((total + filters.limit - 1) // filters.limit, 1)
        return InstanceAggregationsListResult(
            items=items,
            total=total,
            page=filters.page,
            pages=pages,
            limit=filters.limit,
            has_prev=filters.page > 1,
            has_next=filters.page < pages,
        )

    def build_summary(self, filters: InstanceAggregationsSummaryFilters) -> InstanceAggregationsSummary:
        """汇总实例容量概览数据."""
        total_instances, total_size_mb, avg_size_mb, max_size_mb = self._repository.summarize_latest_stats(filters)
        return InstanceAggregationsSummary(
            total_instances=total_instances,
            total_size_mb=total_size_mb,
            avg_size_mb=avg_size_mb,
            max_size_mb=max_size_mb,
            period_type=filters.period_type or "all",
            source="instance_size_stats",
        )
