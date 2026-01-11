"""聚合读模型 Repository.

职责:
- 负责聚合相关 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

from sqlalchemy import desc, func

from app import db
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance_size_aggregation import InstanceSizeAggregation


class AggregationRepository:
    """聚合读模型 Repository."""

    @staticmethod
    def has_aggregation_for_period(*, period_type: str, period_start: date) -> bool:
        """判断某周期聚合是否已存在(实例级 + 数据库级均已落库)."""
        db_exists = (
            db.session.query(DatabaseSizeAggregation.id)
            .filter(
                DatabaseSizeAggregation.period_type == period_type,
                DatabaseSizeAggregation.period_start == period_start,
            )
            .limit(1)
            .first()
            is not None
        )
        if not db_exists:
            return False

        return (
            db.session.query(InstanceSizeAggregation.id)
            .filter(
                InstanceSizeAggregation.period_type == period_type,
                InstanceSizeAggregation.period_start == period_start,
            )
            .limit(1)
            .first()
            is not None
        )

    @staticmethod
    def fetch_latest_aggregation_time() -> datetime | None:
        """获取最新聚合时间(可为空)."""
        latest = DatabaseSizeAggregation.query.order_by(desc(DatabaseSizeAggregation.calculated_at)).first()
        return cast("datetime | None", latest.calculated_at if latest else None)

    @staticmethod
    def fetch_aggregation_counts() -> dict[str, int]:
        """按周期类型统计聚合记录数量."""
        rows = (
            db.session.query(
                DatabaseSizeAggregation.period_type,
                func.count(DatabaseSizeAggregation.id).label("count"),
            )
            .group_by(DatabaseSizeAggregation.period_type)
            .all()
        )
        return {str(row.period_type): int(row.count) for row in rows}

    @staticmethod
    def list_database_aggregations(
        *,
        instance_id: int,
        period_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
        database_name: str | None = None,
    ) -> list[DatabaseSizeAggregation]:
        """查询数据库级聚合记录."""
        query = DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.instance_id == instance_id,
            DatabaseSizeAggregation.period_type == period_type,
        )

        if start_date is not None:
            query = query.filter(DatabaseSizeAggregation.period_start >= start_date)
        if end_date is not None:
            query = query.filter(DatabaseSizeAggregation.period_end <= end_date)
        if database_name:
            query = query.filter(DatabaseSizeAggregation.database_name == database_name)

        return query.order_by(DatabaseSizeAggregation.period_start.desc()).all()

    @staticmethod
    def list_instance_aggregations(
        *,
        instance_id: int,
        period_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[InstanceSizeAggregation]:
        """查询实例级聚合记录."""
        query = InstanceSizeAggregation.query.filter(
            InstanceSizeAggregation.instance_id == instance_id,
            InstanceSizeAggregation.period_type == period_type,
        )

        if start_date is not None:
            query = query.filter(InstanceSizeAggregation.period_start >= start_date)
        if end_date is not None:
            query = query.filter(InstanceSizeAggregation.period_end <= end_date)

        return query.order_by(InstanceSizeAggregation.period_start.desc()).all()

