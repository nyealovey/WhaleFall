"""容量统计(实例维度) Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import desc, func
from sqlalchemy.orm import Query, Session

from app import db
from app.models.instance import Instance
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.types.capacity_instances import InstanceAggregationsFilters, InstanceAggregationsSummaryFilters


class CapacityInstancesRepository:
    """实例容量聚合查询 Repository."""

    def __init__(self, *, session: Session | None = None) -> None:
        """初始化仓库并注入 SQLAlchemy session."""
        self._session = session or db.session

    def list_aggregations(
        self,
        filters: InstanceAggregationsFilters,
    ) -> tuple[list[tuple[InstanceSizeAggregation, Instance]], int]:
        """分页或 TopN 查询实例容量聚合."""
        query = self._apply_filters(self._base_query(), filters)

        if filters.get_all:
            subquery = (
                query.with_entities(
                    InstanceSizeAggregation.instance_id,
                    func.max(InstanceSizeAggregation.total_size_mb).label("max_total_size_mb"),
                )
                .group_by(InstanceSizeAggregation.instance_id)
                .subquery()
            )
            top_instances = (
                self._session.query(subquery.c.instance_id)
                .order_by(desc(subquery.c.max_total_size_mb))
                .limit(100)
                .all()
            )
            top_instance_ids = [row[0] for row in top_instances]
            if not top_instance_ids:
                return [], 0

            rows = (
                query.filter(InstanceSizeAggregation.instance_id.in_(top_instance_ids))
                .order_by(desc(InstanceSizeAggregation.total_size_mb))
                .all()
            )
            return cast("list[tuple[InstanceSizeAggregation, Instance]]", rows), len(rows)

        ordered = query.order_by(
            desc(InstanceSizeAggregation.period_start),
            desc(InstanceSizeAggregation.id),
        )
        total = ordered.count()
        rows = ordered.offset(max(filters.page - 1, 0) * filters.limit).limit(filters.limit).all()
        return cast("list[tuple[InstanceSizeAggregation, Instance]]", rows), int(total or 0)

    def summarize_latest_stats(
        self,
        filters: InstanceAggregationsSummaryFilters,
    ) -> tuple[int, int, float, int]:
        """统计各实例最新容量记录的汇总值."""
        base_query: Query[Any] = cast(
            Query[Any],
            self._session.query(
                InstanceSizeStat.instance_id.label("instance_id"),
                func.max(InstanceSizeStat.collected_at).label("latest_collected_at"),
            )
            .join(Instance, Instance.id == InstanceSizeStat.instance_id)
            .filter(
                InstanceSizeStat.is_deleted.is_(False),
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
            ),
        )

        if filters.instance_id:
            base_query = base_query.filter(InstanceSizeStat.instance_id == filters.instance_id)
        if filters.db_type:
            base_query = base_query.filter(Instance.db_type == filters.db_type)
        if filters.start_date:
            base_query = base_query.filter(InstanceSizeStat.collected_date >= filters.start_date)
        if filters.end_date:
            base_query = base_query.filter(InstanceSizeStat.collected_date <= filters.end_date)

        latest_subquery = base_query.group_by(InstanceSizeStat.instance_id).subquery()
        totals = (
            self._session.query(
                func.count().label("total_instances"),
                func.coalesce(func.sum(InstanceSizeStat.total_size_mb), 0).label("total_size_mb"),
                func.coalesce(func.avg(InstanceSizeStat.total_size_mb), 0).label("avg_size_mb"),
                func.coalesce(func.max(InstanceSizeStat.total_size_mb), 0).label("max_size_mb"),
            )
            .join(
                latest_subquery,
                (InstanceSizeStat.instance_id == latest_subquery.c.instance_id)
                & (InstanceSizeStat.collected_at == latest_subquery.c.latest_collected_at),
            )
            .one()
        )

        total_instances = int(getattr(totals, "total_instances", 0) or 0)
        total_size_mb = int(getattr(totals, "total_size_mb", 0) or 0)
        avg_size_mb = float(getattr(totals, "avg_size_mb", 0) or 0)
        max_size_mb = int(getattr(totals, "max_size_mb", 0) or 0)
        return total_instances, total_size_mb, avg_size_mb, max_size_mb

    def _base_query(self) -> Query[Any]:
        return (
            self._session.query(InstanceSizeAggregation, Instance)
            .join(Instance, Instance.id == InstanceSizeAggregation.instance_id)
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
            )
        )

    @staticmethod
    def _apply_filters(query: Query[Any], filters: InstanceAggregationsFilters) -> Query[Any]:
        if filters.instance_id:
            query = query.filter(InstanceSizeAggregation.instance_id == filters.instance_id)
        if filters.db_type:
            query = query.filter(Instance.db_type == filters.db_type)
        if filters.period_type:
            query = query.filter(InstanceSizeAggregation.period_type == filters.period_type)
        if filters.start_date:
            query = query.filter(InstanceSizeAggregation.period_start >= filters.start_date)
        if filters.end_date:
            query = query.filter(InstanceSizeAggregation.period_end <= filters.end_date)
        return query
