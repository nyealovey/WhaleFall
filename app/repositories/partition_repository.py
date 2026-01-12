"""分区管理读模型 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func

from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.core.types.partition import PeriodWindow


class PartitionRepository:
    """分区管理查询 Repository."""

    @staticmethod
    def fetch_core_metric_counts(
        *,
        period_type: str,
        window: PeriodWindow,
    ) -> tuple[dict[date, int], dict[date, int], dict[date, int], dict[date, int]]:
        """获取核心指标计数(聚合与采集)."""
        db_aggs_rows = (
            DatabaseSizeAggregation.query.filter(
                DatabaseSizeAggregation.period_type == period_type,
                DatabaseSizeAggregation.period_start >= window.period_start,
                DatabaseSizeAggregation.period_start <= window.period_end,
            )
            .with_entities(
                DatabaseSizeAggregation.period_start,
                func.count(DatabaseSizeAggregation.id),
            )
            .group_by(DatabaseSizeAggregation.period_start)
            .all()
        )
        db_aggs = {period_start: int(count) for period_start, count in db_aggs_rows}

        instance_aggs_rows = (
            InstanceSizeAggregation.query.filter(
                InstanceSizeAggregation.period_type == period_type,
                InstanceSizeAggregation.period_start >= window.period_start,
                InstanceSizeAggregation.period_start <= window.period_end,
            )
            .with_entities(
                InstanceSizeAggregation.period_start,
                func.count(InstanceSizeAggregation.id),
            )
            .group_by(InstanceSizeAggregation.period_start)
            .all()
        )
        instance_aggs = {period_start: int(count) for period_start, count in instance_aggs_rows}

        db_stats_rows = (
            DatabaseSizeStat.query.filter(
                DatabaseSizeStat.collected_date >= window.stats_start,
                DatabaseSizeStat.collected_date <= window.stats_end,
            )
            .with_entities(
                DatabaseSizeStat.collected_date,
                func.count(DatabaseSizeStat.id),
            )
            .group_by(DatabaseSizeStat.collected_date)
            .all()
        )
        db_stats = {collected_date: int(count) for collected_date, count in db_stats_rows}

        instance_stats_rows = (
            InstanceSizeStat.query.filter(
                InstanceSizeStat.collected_date >= window.stats_start,
                InstanceSizeStat.collected_date <= window.stats_end,
            )
            .with_entities(
                InstanceSizeStat.collected_date,
                func.count(InstanceSizeStat.id),
            )
            .group_by(InstanceSizeStat.collected_date)
            .all()
        )
        instance_stats = {collected_date: int(count) for collected_date, count in instance_stats_rows}

        return db_aggs, instance_aggs, db_stats, instance_stats
