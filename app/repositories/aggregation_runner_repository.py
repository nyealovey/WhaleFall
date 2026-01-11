"""聚合 runners Repository.

职责:
- 为 aggregation runners 提供聚合/统计查询能力
- 不做业务编排、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func

from app import db
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat


class AggregationRunnerRepository:
    """聚合 runner 查询 Repository."""

    @staticmethod
    def list_database_size_stat_metrics(*, instance_id: int, start_date: date, end_date: date) -> list[Any]:
        """查询指定周期内的数据库指标聚合行."""
        return (
            db.session.query(
                DatabaseSizeStat.database_name.label("database_name"),
                func.avg(DatabaseSizeStat.size_mb).label("avg_size_mb"),
                func.max(DatabaseSizeStat.size_mb).label("max_size_mb"),
                func.min(DatabaseSizeStat.size_mb).label("min_size_mb"),
                func.count(DatabaseSizeStat.id).label("data_count"),
                func.avg(DatabaseSizeStat.data_size_mb).label("avg_data_size_mb"),
                func.max(DatabaseSizeStat.data_size_mb).label("max_data_size_mb"),
                func.min(DatabaseSizeStat.data_size_mb).label("min_data_size_mb"),
            )
            .filter(
                DatabaseSizeStat.instance_id == instance_id,
                DatabaseSizeStat.collected_date >= start_date,
                DatabaseSizeStat.collected_date <= end_date,
            )
            .group_by(DatabaseSizeStat.database_name)
            .all()
        )

    @staticmethod
    def list_database_size_stat_averages(*, instance_id: int, start_date: date, end_date: date) -> list[Any]:
        """查询指定周期内各数据库的平均值行."""
        return (
            db.session.query(
                DatabaseSizeStat.database_name.label("database_name"),
                func.avg(DatabaseSizeStat.size_mb).label("avg_size_mb"),
                func.avg(DatabaseSizeStat.data_size_mb).label("avg_data_size_mb"),
            )
            .filter(
                DatabaseSizeStat.instance_id == instance_id,
                DatabaseSizeStat.collected_date >= start_date,
                DatabaseSizeStat.collected_date <= end_date,
            )
            .group_by(DatabaseSizeStat.database_name)
            .all()
        )

    @staticmethod
    def list_existing_database_aggregations(
        *,
        instance_id: int,
        period_type: str,
        period_start: date,
    ) -> list[DatabaseSizeAggregation]:
        """查询已存在的数据库级聚合记录(同实例 + 同周期类型 + 同 period_start)."""
        return (
            DatabaseSizeAggregation.query.filter(
                DatabaseSizeAggregation.instance_id == instance_id,
                DatabaseSizeAggregation.period_type == period_type,
                DatabaseSizeAggregation.period_start == period_start,
            )
            .all()
        )

    @staticmethod
    def list_instance_size_stats(*, instance_id: int, start_date: date, end_date: date) -> list[InstanceSizeStat]:
        """查询实例在指定时间段的统计记录."""
        return (
            InstanceSizeStat.query.filter(
                InstanceSizeStat.instance_id == instance_id,
                InstanceSizeStat.collected_date >= start_date,
                InstanceSizeStat.collected_date <= end_date,
                InstanceSizeStat.is_deleted.is_(False),
            )
            .all()
        )

    @staticmethod
    def get_existing_instance_aggregation(
        *,
        instance_id: int,
        period_type: str,
        period_start: date,
    ) -> InstanceSizeAggregation | None:
        """查询已存在的实例级聚合记录(可为空)."""
        return (
            InstanceSizeAggregation.query.filter(
                InstanceSizeAggregation.instance_id == instance_id,
                InstanceSizeAggregation.period_type == period_type,
                InstanceSizeAggregation.period_start == period_start,
            )
            .first()
        )

