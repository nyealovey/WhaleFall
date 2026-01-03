"""数据库容量聚合读取 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.capacity_databases_repository import CapacityDatabasesRepository
from app.types.capacity_common import CapacityInstanceRef
from app.types.capacity_databases import (
    DatabaseAggregationsFilters,
    DatabaseAggregationsItem,
    DatabaseAggregationsListResult,
    DatabaseAggregationsSummary,
    DatabaseAggregationsSummaryFilters,
)


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
            items.append(
                DatabaseAggregationsItem(
                    id=int(aggregation.id),
                    instance_id=int(aggregation.instance_id),
                    database_name=aggregation.database_name,
                    period_type=aggregation.period_type,
                    period_start=aggregation.period_start.isoformat() if aggregation.period_start else None,
                    period_end=aggregation.period_end.isoformat() if aggregation.period_end else None,
                    avg_size_mb=int(aggregation.avg_size_mb or 0),
                    max_size_mb=int(aggregation.max_size_mb or 0),
                    min_size_mb=int(aggregation.min_size_mb or 0),
                    data_count=int(aggregation.data_count or 0),
                    avg_data_size_mb=(
                        int(aggregation.avg_data_size_mb) if aggregation.avg_data_size_mb is not None else None
                    ),
                    max_data_size_mb=(
                        int(aggregation.max_data_size_mb) if aggregation.max_data_size_mb is not None else None
                    ),
                    min_data_size_mb=(
                        int(aggregation.min_data_size_mb) if aggregation.min_data_size_mb is not None else None
                    ),
                    avg_log_size_mb=(
                        int(aggregation.avg_log_size_mb) if aggregation.avg_log_size_mb is not None else None
                    ),
                    max_log_size_mb=(
                        int(aggregation.max_log_size_mb) if aggregation.max_log_size_mb is not None else None
                    ),
                    min_log_size_mb=(
                        int(aggregation.min_log_size_mb) if aggregation.min_log_size_mb is not None else None
                    ),
                    size_change_mb=int(aggregation.size_change_mb or 0),
                    size_change_percent=float(aggregation.size_change_percent or 0),
                    data_size_change_mb=(
                        int(aggregation.data_size_change_mb) if aggregation.data_size_change_mb is not None else None
                    ),
                    data_size_change_percent=(
                        float(aggregation.data_size_change_percent)
                        if aggregation.data_size_change_percent is not None
                        else None
                    ),
                    log_size_change_mb=(
                        int(aggregation.log_size_change_mb) if aggregation.log_size_change_mb is not None else None
                    ),
                    log_size_change_percent=(
                        float(aggregation.log_size_change_percent)
                        if aggregation.log_size_change_percent is not None
                        else None
                    ),
                    growth_rate=float(aggregation.growth_rate or 0),
                    calculated_at=aggregation.calculated_at.isoformat() if aggregation.calculated_at else None,
                    created_at=aggregation.created_at.isoformat() if aggregation.created_at else None,
                    instance=CapacityInstanceRef(
                        id=int(instance.id),
                        name=instance.name,
                        db_type=instance.db_type,
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
