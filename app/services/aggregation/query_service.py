"""聚合查询只读工具."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.repositories.aggregation_repository import AggregationRepository


class AggregationQueryService:
    """封装聚合记录的查询与格式化逻辑.

    提供数据库级和实例级聚合数据的查询和格式化功能.
    """

    def __init__(self, repository: AggregationRepository | None = None) -> None:
        """初始化聚合查询服务."""
        self._repository = repository or AggregationRepository()

    def get_database_aggregations(
        self,
        instance_id: int,
        period_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
        database_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取数据库级聚合数据.

        查询指定实例的数据库级聚合记录,支持按时间范围和数据库名称过滤.

        Args:
            instance_id: 实例 ID.
            period_type: 周期类型,如 'daily'、'weekly'、'monthly'、'quarterly'.
            start_date: 开始日期,可选.
            end_date: 结束日期,可选.
            database_name: 数据库名称,可选.

        Returns:
            格式化的聚合数据列表,按周期开始时间倒序排列.

        """
        aggregations = self._repository.list_database_aggregations(
            instance_id=instance_id,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            database_name=database_name,
        )
        return [self._format_database_aggregation(agg) for agg in aggregations]

    def get_instance_aggregations(
        self,
        instance_id: int,
        period_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """获取实例级聚合数据.

        查询指定实例的实例级聚合记录,支持按时间范围过滤.

        Args:
            instance_id: 实例 ID.
            period_type: 周期类型,如 'daily'、'weekly'、'monthly'、'quarterly'.
            start_date: 开始日期,可选.
            end_date: 结束日期,可选.

        Returns:
            格式化的聚合数据列表,按周期开始时间倒序排列.

        """
        aggregations = self._repository.list_instance_aggregations(
            instance_id=instance_id,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        return [self._format_instance_aggregation(agg) for agg in aggregations]

    def _format_database_aggregation(self, aggregation: DatabaseSizeAggregation) -> dict[str, Any]:
        """格式化数据库级聚合记录.

        Args:
            aggregation: 数据库级聚合对象.

        Returns:
            格式化的聚合数据字典.

        """
        return {
            "id": aggregation.id,
            "instance_id": aggregation.instance_id,
            "database_name": aggregation.database_name,
            "period_type": aggregation.period_type,
            "period_start": self._safe_iso_date(aggregation.period_start),
            "period_end": self._safe_iso_date(aggregation.period_end),
            "statistics": {
                "avg_size_mb": self._to_int(aggregation.avg_size_mb),
                "max_size_mb": self._to_int(aggregation.max_size_mb),
                "min_size_mb": self._to_int(aggregation.min_size_mb),
                "data_count": self._to_int(aggregation.data_count),
                "avg_data_size_mb": self._to_int(aggregation.avg_data_size_mb),
                "max_data_size_mb": self._to_int(aggregation.max_data_size_mb),
                "min_data_size_mb": self._to_int(aggregation.min_data_size_mb),
                "avg_log_size_mb": self._to_int(aggregation.avg_log_size_mb),
                "max_log_size_mb": self._to_int(aggregation.max_log_size_mb),
                "min_log_size_mb": self._to_int(aggregation.min_log_size_mb),
            },
            "changes": {
                "size_change_mb": self._to_int(aggregation.size_change_mb),
                "size_change_percent": self._to_float(aggregation.size_change_percent),
                "data_size_change_mb": self._to_int(aggregation.data_size_change_mb),
                "data_size_change_percent": self._to_optional_float(aggregation.data_size_change_percent),
                "log_size_change_mb": self._to_int(aggregation.log_size_change_mb),
                "log_size_change_percent": self._to_optional_float(aggregation.log_size_change_percent),
                "growth_rate": self._to_float(aggregation.growth_rate),
            },
            "calculated_at": self._safe_iso_datetime(aggregation.calculated_at),
            "created_at": self._safe_iso_datetime(aggregation.created_at),
        }

    def _format_instance_aggregation(self, aggregation: InstanceSizeAggregation) -> dict[str, Any]:
        """格式化实例级聚合记录.

        Args:
            aggregation: 实例级聚合对象.

        Returns:
            格式化的聚合数据字典.

        """
        return {
            "id": aggregation.id,
            "instance_id": aggregation.instance_id,
            "period_type": aggregation.period_type,
            "period_start": self._safe_iso_date(aggregation.period_start),
            "period_end": self._safe_iso_date(aggregation.period_end),
            "statistics": {
                "total_size_mb": self._to_int(aggregation.total_size_mb),
                "avg_size_mb": self._to_int(aggregation.avg_size_mb),
                "max_size_mb": self._to_int(aggregation.max_size_mb),
                "min_size_mb": self._to_int(aggregation.min_size_mb),
                "data_count": self._to_int(aggregation.data_count),
                "database_count": self._to_int(aggregation.database_count),
                "avg_database_count": self._to_optional_float(aggregation.avg_database_count),
                "max_database_count": self._to_int(aggregation.max_database_count),
                "min_database_count": self._to_int(aggregation.min_database_count),
            },
            "changes": {
                "total_size_change_mb": self._to_int(aggregation.total_size_change_mb),
                "total_size_change_percent": self._to_float(aggregation.total_size_change_percent),
                "database_count_change": self._to_int(aggregation.database_count_change),
                "database_count_change_percent": self._to_optional_float(aggregation.database_count_change_percent),
                "growth_rate": self._to_float(aggregation.growth_rate),
                "trend_direction": self._safe_str(aggregation.trend_direction),
            },
            "calculated_at": self._safe_iso_datetime(aggregation.calculated_at),
            "created_at": self._safe_iso_datetime(aggregation.created_at),
        }

    @staticmethod
    def _safe_iso_date(value: Any) -> str | None:
        """将日期列安全转换为 ISO 字符串."""
        if isinstance(value, date):
            return value.isoformat()
        return None

    @staticmethod
    def _safe_iso_datetime(value: Any) -> str | None:
        """将 datetime 列安全转换为 ISO 字符串."""
        if isinstance(value, datetime):
            return value.isoformat()
        return None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        """Column/Decimal 安全转换为 int."""
        if isinstance(value, (int, Decimal)):
            return int(value)
        if isinstance(value, float):
            return int(value)
        return None

    @staticmethod
    def _to_float(value: Any) -> float:
        """Column/Decimal 安全转换为 float,缺省返回 0."""
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    def _to_optional_float(self, value: Any) -> float | None:
        """允许空值的 float 转换."""
        if value is None:
            return None
        if isinstance(value, (int, float, Decimal)):
            return float(value)
        return None

    @staticmethod
    def _safe_str(value: Any) -> str | None:
        """将可选字符串字段安全提取."""
        if isinstance(value, str):
            return value
        return None


__all__ = ["AggregationQueryService"]
