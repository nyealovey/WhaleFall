"""聚合查询只读工具。"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance_size_aggregation import InstanceSizeAggregation


class AggregationQueryService:
    """封装聚合记录的查询与格式化逻辑。"""

    def get_database_aggregations(
        self,
        instance_id: int,
        period_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
        database_name: str | None = None,
    ) -> List[Dict[str, Any]]:
        query = DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.instance_id == instance_id,
            DatabaseSizeAggregation.period_type == period_type,
        )

        if start_date:
            query = query.filter(DatabaseSizeAggregation.period_start >= start_date)
        if end_date:
            query = query.filter(DatabaseSizeAggregation.period_end <= end_date)
        if database_name:
            query = query.filter(DatabaseSizeAggregation.database_name == database_name)

        aggregations = query.order_by(DatabaseSizeAggregation.period_start.desc()).all()
        return [self._format_database_aggregation(agg) for agg in aggregations]

    def get_instance_aggregations(
        self,
        instance_id: int,
        period_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> List[Dict[str, Any]]:
        query = InstanceSizeAggregation.query.filter(
            InstanceSizeAggregation.instance_id == instance_id,
            InstanceSizeAggregation.period_type == period_type,
        )

        if start_date:
            query = query.filter(InstanceSizeAggregation.period_start >= start_date)
        if end_date:
            query = query.filter(InstanceSizeAggregation.period_end <= end_date)

        aggregations = query.order_by(InstanceSizeAggregation.period_start.desc()).all()
        return [self._format_instance_aggregation(agg) for agg in aggregations]

    def _format_database_aggregation(self, aggregation: DatabaseSizeAggregation) -> Dict[str, Any]:
        return {
            "id": aggregation.id,
            "instance_id": aggregation.instance_id,
            "database_name": aggregation.database_name,
            "period_type": aggregation.period_type,
            "period_start": aggregation.period_start.isoformat() if aggregation.period_start else None,
            "period_end": aggregation.period_end.isoformat() if aggregation.period_end else None,
            "statistics": {
                "avg_size_mb": aggregation.avg_size_mb,
                "max_size_mb": aggregation.max_size_mb,
                "min_size_mb": aggregation.min_size_mb,
                "data_count": aggregation.data_count,
                "avg_data_size_mb": aggregation.avg_data_size_mb,
                "max_data_size_mb": aggregation.max_data_size_mb,
                "min_data_size_mb": aggregation.min_data_size_mb,
                "avg_log_size_mb": aggregation.avg_log_size_mb,
                "max_log_size_mb": aggregation.max_log_size_mb,
                "min_log_size_mb": aggregation.min_log_size_mb,
            },
            "changes": {
                "size_change_mb": aggregation.size_change_mb,
                "size_change_percent": float(aggregation.size_change_percent) if aggregation.size_change_percent else 0,
                "data_size_change_mb": aggregation.data_size_change_mb,
                "data_size_change_percent": float(aggregation.data_size_change_percent)
                if aggregation.data_size_change_percent
                else None,
                "log_size_change_mb": aggregation.log_size_change_mb,
                "log_size_change_percent": float(aggregation.log_size_change_percent)
                if aggregation.log_size_change_percent
                else None,
                "growth_rate": float(aggregation.growth_rate) if aggregation.growth_rate else 0,
            },
            "calculated_at": aggregation.calculated_at.isoformat() if aggregation.calculated_at else None,
            "created_at": aggregation.created_at.isoformat() if aggregation.created_at else None,
        }

    def _format_instance_aggregation(self, aggregation: InstanceSizeAggregation) -> Dict[str, Any]:
        return {
            "id": aggregation.id,
            "instance_id": aggregation.instance_id,
            "period_type": aggregation.period_type,
            "period_start": aggregation.period_start.isoformat() if aggregation.period_start else None,
            "period_end": aggregation.period_end.isoformat() if aggregation.period_end else None,
            "statistics": {
                "total_size_mb": aggregation.total_size_mb,
                "avg_size_mb": aggregation.avg_size_mb,
                "max_size_mb": aggregation.max_size_mb,
                "min_size_mb": aggregation.min_size_mb,
                "data_count": aggregation.data_count,
                "database_count": aggregation.database_count,
                "avg_database_count": float(aggregation.avg_database_count) if aggregation.avg_database_count else None,
                "max_database_count": aggregation.max_database_count,
                "min_database_count": aggregation.min_database_count,
            },
            "changes": {
                "total_size_change_mb": aggregation.total_size_change_mb,
                "total_size_change_percent": float(aggregation.total_size_change_percent)
                if aggregation.total_size_change_percent
                else 0,
                "database_count_change": aggregation.database_count_change,
                "database_count_change_percent": float(aggregation.database_count_change_percent)
                if aggregation.database_count_change_percent
                else None,
                "growth_rate": float(aggregation.growth_rate) if aggregation.growth_rate else 0,
                "trend_direction": aggregation.trend_direction,
            },
            "calculated_at": aggregation.calculated_at.isoformat() if aggregation.calculated_at else None,
            "created_at": aggregation.created_at.isoformat() if aggregation.created_at else None,
        }


__all__ = ["AggregationQueryService"]
