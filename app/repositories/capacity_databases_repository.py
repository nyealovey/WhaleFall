"""容量统计(数据库维度) Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import and_, desc, func, tuple_
from sqlalchemy.orm import Query, Session

from app import db
from app.core.types.capacity_databases import DatabaseAggregationsFilters, DatabaseAggregationsSummaryFilters
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase


class CapacityDatabasesRepository:
    """数据库容量聚合查询 Repository."""

    def __init__(self, *, session: Session | None = None) -> None:
        """初始化仓库并注入 SQLAlchemy session."""
        self._session = session or db.session

    def resolve_instance_database_id_by_name(
        self,
        *,
        database_name: str,
        instance_id: int | None = None,
    ) -> int | None:
        """根据数据库名称(可选实例过滤)解析 InstanceDatabase.id."""
        query = self._session.query(InstanceDatabase.id).filter(InstanceDatabase.database_name == database_name)
        if instance_id is not None:
            query = query.filter(InstanceDatabase.instance_id == instance_id)
        row = query.first()
        if row is None:
            return None
        row_id = getattr(row, "id", None)
        if row_id is None:
            return None
        return int(row_id)

    def list_aggregations(
        self,
        filters: DatabaseAggregationsFilters,
    ) -> tuple[list[tuple[DatabaseSizeAggregation, Instance]], int]:
        """分页或 TopN 查询数据库容量聚合."""
        resolved_database_name = self._resolve_database_name(filters.database_name, filters.database_id)
        query = self._apply_filters(self._base_query(), filters, resolved_database_name=resolved_database_name)

        if filters.get_all:
            base_query = (
                query.with_entities(
                    DatabaseSizeAggregation.instance_id,
                    DatabaseSizeAggregation.database_name,
                    func.max(DatabaseSizeAggregation.avg_size_mb).label("max_avg_size_mb"),
                )
                .group_by(DatabaseSizeAggregation.instance_id, DatabaseSizeAggregation.database_name)
                .subquery()
            )
            top_pairs = (
                self._session.query(base_query.c.instance_id, base_query.c.database_name)
                .order_by(desc(base_query.c.max_avg_size_mb))
                .limit(100)
                .all()
            )
            pair_values = [(row.instance_id, row.database_name) for row in top_pairs]
            if not pair_values:
                return [], 0

            rows = (
                query.filter(
                    tuple_(
                        DatabaseSizeAggregation.instance_id,
                        DatabaseSizeAggregation.database_name,
                    ).in_(pair_values),
                )
                .order_by(DatabaseSizeAggregation.period_start.asc())
                .all()
            )
            return cast("list[tuple[DatabaseSizeAggregation, Instance]]", rows), len(rows)

        ordered = query.order_by(desc(DatabaseSizeAggregation.period_start))
        total = ordered.count()
        rows = ordered.offset(max(filters.page - 1, 0) * filters.limit).limit(filters.limit).all()
        return cast("list[tuple[DatabaseSizeAggregation, Instance]]", rows), int(total)

    def summarize_latest_aggregations(
        self,
        filters: DatabaseAggregationsSummaryFilters,
    ) -> tuple[int, int, int, float, int]:
        """汇总最新周期的容量聚合统计."""
        row = self._build_latest_aggregations_summary_query(filters).one()

        total_databases = int(getattr(row, "total_databases", 0) or 0)
        total_instances = int(getattr(row, "total_instances", 0) or 0)
        total_size_mb = int(getattr(row, "total_size_mb", 0) or 0)
        avg_size_mb = float(getattr(row, "avg_size_mb", 0) or 0)
        max_size_mb = int(getattr(row, "max_size_mb", 0) or 0)
        return total_databases, total_instances, total_size_mb, avg_size_mb, max_size_mb

    def _build_latest_aggregations_summary_query(self, filters: DatabaseAggregationsSummaryFilters) -> Query[Any]:
        """构造汇总查询(最新周期数据).

        注意:
        - `database_size_aggregations` 为按 `period_start` 分区的表
        - 这里使用子查询 + join 的方式获取「每个库的最新周期记录」，避免构造超大的 tuple IN 参数列表
        """
        resolved_database_name = self._resolve_database_name(filters.database_name, filters.database_id)
        base_query = self._apply_filters(self._base_query(), filters, resolved_database_name=resolved_database_name)

        latest_subquery = (
            base_query.with_entities(
                DatabaseSizeAggregation.instance_id.label("instance_id"),
                DatabaseSizeAggregation.database_name.label("database_name"),
                DatabaseSizeAggregation.period_type.label("period_type"),
                func.max(DatabaseSizeAggregation.period_start).label("latest_period_start"),
            )
            .group_by(
                DatabaseSizeAggregation.instance_id,
                DatabaseSizeAggregation.database_name,
                DatabaseSizeAggregation.period_type,
            )
            .subquery()
        )

        join_condition = and_(
            DatabaseSizeAggregation.instance_id == latest_subquery.c.instance_id,
            DatabaseSizeAggregation.database_name == latest_subquery.c.database_name,
            DatabaseSizeAggregation.period_type == latest_subquery.c.period_type,
            DatabaseSizeAggregation.period_start == latest_subquery.c.latest_period_start,
        )

        return (
            self._session.query(
                func.count().label("total_databases"),
                func.count(func.distinct(latest_subquery.c.instance_id)).label("total_instances"),
                func.coalesce(func.sum(DatabaseSizeAggregation.avg_size_mb), 0).label("total_size_mb"),
                func.coalesce(func.avg(DatabaseSizeAggregation.avg_size_mb), 0).label("avg_size_mb"),
                func.coalesce(func.max(DatabaseSizeAggregation.max_size_mb), 0).label("max_size_mb"),
            )
            .select_from(DatabaseSizeAggregation)
            .join(latest_subquery, join_condition)
        )

    def _base_query(self) -> Query[Any]:
        join_condition = and_(
            InstanceDatabase.instance_id == DatabaseSizeAggregation.instance_id,
            InstanceDatabase.database_name == DatabaseSizeAggregation.database_name,
        )
        return (
            self._session.query(DatabaseSizeAggregation, Instance)
            .join(Instance, Instance.id == DatabaseSizeAggregation.instance_id)
            .join(InstanceDatabase, join_condition)
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                InstanceDatabase.is_active.is_(True),
            )
        )

    def _resolve_database_name(self, database_name: str | None, database_id: int | None) -> str | None:
        if database_name:
            return database_name
        if not database_id:
            return None
        record = self._session.query(InstanceDatabase).filter(InstanceDatabase.id == database_id).first()
        return record.database_name if record else None

    @staticmethod
    def _apply_filters(
        query: Query[Any],
        filters: DatabaseAggregationsFilters | DatabaseAggregationsSummaryFilters,
        *,
        resolved_database_name: str | None,
    ) -> Query[Any]:
        if filters.instance_id:
            query = query.filter(DatabaseSizeAggregation.instance_id == filters.instance_id)
        if filters.db_type:
            query = query.filter(Instance.db_type == filters.db_type)
        if resolved_database_name:
            query = query.filter(DatabaseSizeAggregation.database_name == resolved_database_name)
        if filters.period_type:
            query = query.filter(DatabaseSizeAggregation.period_type == filters.period_type)
        if filters.start_date:
            # `database_size_aggregations` 为按 `period_start` 分区的表，必须尽量使用分区键做范围过滤，
            # 否则容易触发全分区扫描(在生产数据量较大时可能导致数据库连接被中断)。
            query = query.filter(DatabaseSizeAggregation.period_start >= filters.start_date)
        if filters.end_date:
            query = query.filter(DatabaseSizeAggregation.period_end <= filters.end_date)
            # 补充分区键上界，帮助 PostgreSQL 做 partition pruning。
            query = query.filter(DatabaseSizeAggregation.period_start <= filters.end_date)
        return query
