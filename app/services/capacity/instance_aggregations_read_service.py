"""实例容量聚合读取 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.capacity_instances_repository import CapacityInstancesRepository
from app.types.capacity_common import CapacityInstanceRef
from app.types.capacity_instances import (
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
            items.append(
                InstanceAggregationsItem(
                    id=int(aggregation.id),
                    instance_id=int(aggregation.instance_id),
                    period_type=aggregation.period_type,
                    period_start=aggregation.period_start.isoformat() if aggregation.period_start else None,
                    period_end=aggregation.period_end.isoformat() if aggregation.period_end else None,
                    total_size_mb=int(aggregation.total_size_mb or 0),
                    avg_size_mb=int(aggregation.total_size_mb or 0),
                    max_size_mb=int(aggregation.max_size_mb or 0),
                    min_size_mb=int(aggregation.min_size_mb or 0),
                    data_count=int(aggregation.data_count or 0),
                    database_count=int(aggregation.database_count or 0),
                    avg_database_count=(
                        float(aggregation.avg_database_count) if aggregation.avg_database_count is not None else None
                    ),
                    max_database_count=(
                        int(aggregation.max_database_count) if aggregation.max_database_count is not None else None
                    ),
                    min_database_count=(
                        int(aggregation.min_database_count) if aggregation.min_database_count is not None else None
                    ),
                    total_size_change_mb=(
                        int(aggregation.total_size_change_mb) if aggregation.total_size_change_mb is not None else None
                    ),
                    total_size_change_percent=(
                        float(aggregation.total_size_change_percent)
                        if aggregation.total_size_change_percent is not None
                        else None
                    ),
                    database_count_change=(
                        int(aggregation.database_count_change)
                        if aggregation.database_count_change is not None
                        else None
                    ),
                    database_count_change_percent=(
                        float(aggregation.database_count_change_percent)
                        if aggregation.database_count_change_percent is not None
                        else None
                    ),
                    growth_rate=float(aggregation.growth_rate) if aggregation.growth_rate is not None else None,
                    trend_direction=aggregation.trend_direction,
                    calculated_at=aggregation.calculated_at.isoformat() if aggregation.calculated_at else None,
                    created_at=aggregation.created_at.isoformat() if aggregation.created_at else None,
                    instance=CapacityInstanceRef(
                        id=int(instance.id),
                        name=instance.name,
                        db_type=instance.db_type,
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
