"""分区管理 read API Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any, cast

from app.errors import SystemError, ValidationError
from app.repositories.partition_repository import PartitionRepository
from app.types.listing import PaginatedResult
from app.types.partition import (
    PartitionCoreMetricsResult,
    PartitionEntry,
    PartitionInfoSnapshot,
    PartitionStatusSnapshot,
    PeriodWindow,
)
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils


class PartitionReadService:
    """分区管理读取服务."""

    def __init__(self, repository: PartitionRepository | None = None) -> None:
        """初始化服务并注入分区仓库."""
        self._repository = repository or PartitionRepository()

    def get_partition_info_snapshot(self) -> PartitionInfoSnapshot:
        """获取分区信息快照."""
        try:
            info = self._repository.fetch_partition_info()
        except Exception as exc:
            log_error("获取分区信息失败", module="partition_read_service", exception=exc)
            raise SystemError("获取分区信息失败") from exc

        partitions = self._coerce_partitions(info.get("partitions"))
        missing_partitions, status = self._resolve_missing_partitions(partitions)

        return PartitionInfoSnapshot(
            partitions=partitions,
            total_partitions=int(info.get("total_partitions", 0) or 0),
            total_size_bytes=int(info.get("total_size_bytes", 0) or 0),
            total_size=str(info.get("total_size", "0 B")),
            total_records=int(info.get("total_records", 0) or 0),
            tables=[str(item) for item in cast(list[object], info.get("tables") or [])],
            status=status,
            missing_partitions=missing_partitions,
        )

    def get_partition_status_snapshot(self) -> PartitionStatusSnapshot:
        """获取分区状态快照."""
        try:
            info = self._repository.fetch_partition_info()
        except Exception as exc:
            log_error("获取分区状态失败", module="partition_read_service", exception=exc)
            raise SystemError("获取分区状态失败") from exc

        partitions = self._coerce_partitions(info.get("partitions"))
        missing_partitions, status = self._resolve_missing_partitions(partitions)
        return PartitionStatusSnapshot(
            status=status,
            total_partitions=int(info.get("total_partitions", 0) or 0),
            total_size=str(info.get("total_size", "0 B")),
            total_records=int(info.get("total_records", 0) or 0),
            missing_partitions=missing_partitions,
            partitions=partitions,
        )

    def list_partitions(
        self,
        *,
        page: int,
        limit: int,
        search: str,
        table_type: str,
        status_filter: str,
        sort_field: str,
        sort_order: str,
    ) -> PaginatedResult[PartitionEntry]:
        """分页列出分区条目."""
        snapshot = self.get_partition_info_snapshot()
        partitions = list(snapshot.partitions)

        normalized_table_type = table_type.strip().lower()
        if normalized_table_type:
            partitions = [item for item in partitions if item.table_type.lower() == normalized_table_type]

        normalized_status = status_filter.strip().lower()
        if normalized_status:
            partitions = [item for item in partitions if item.status.lower() == normalized_status]

        normalized_search = search.strip().lower()
        if normalized_search:
            partitions = [
                item
                for item in partitions
                if normalized_search in item.name.lower() or normalized_search in item.display_name.lower()
            ]

        sortable_fields: dict[str, Any] = {
            "name": lambda item: item.name.lower(),
            "table_type": lambda item: item.table_type.lower(),
            "size": lambda item: item.size_bytes,
            "size_bytes": lambda item: item.size_bytes,
            "record_count": lambda item: item.record_count,
            "status": lambda item: item.status.lower(),
            "date": lambda item: item.date,
        }
        resolver = sortable_fields.get(sort_field.lower(), sortable_fields["date"])
        partitions.sort(key=resolver, reverse=(sort_order.strip().lower() == "desc"))

        normalized_limit = max(limit, 1)
        total = len(partitions)
        pages = max((total + normalized_limit - 1) // normalized_limit, 1)
        normalized_page = max(min(page, pages), 1)

        start = (normalized_page - 1) * normalized_limit
        end = start + normalized_limit
        items = partitions[start:end]
        return PaginatedResult(items=items, total=total, page=normalized_page, pages=pages, limit=normalized_limit)

    def build_core_metrics(self, *, period_type: str, days: int) -> PartitionCoreMetricsResult:
        """构建分区核心指标图表数据."""
        normalized_type = self._normalize_period_type(period_type)
        requested_days = max(int(days), 1)

        today_china = time_utils.now_china().date()
        window = self._resolve_period_window(normalized_type, requested_days, today_china)

        try:
            db_aggs, instance_aggs, db_stats, instance_stats = self._repository.fetch_core_metric_counts(
                period_type=normalized_type,
                window=window,
            )
        except Exception as exc:
            log_error("获取核心聚合指标失败", module="partition_read_service", exception=exc)
            raise SystemError("获取核心聚合指标失败") from exc

        daily_metrics = self._build_daily_metrics(window, db_stats, instance_stats, db_aggs, instance_aggs)
        labels, datasets, time_range = self._compose_chart_payload(normalized_type, window, daily_metrics)

        return PartitionCoreMetricsResult(
            labels=labels,
            datasets=datasets,
            dataPointCount=len(labels),
            timeRange=time_range,
            yAxisLabel="数量",
            chartTitle=f"{normalized_type.title()}核心指标统计",
            periodType=normalized_type,
        )

    @staticmethod
    def _coerce_partitions(raw_partitions: object) -> list[PartitionEntry]:
        partitions: list[PartitionEntry] = []
        if not isinstance(raw_partitions, Iterable):
            return partitions

        for item in raw_partitions:
            if not isinstance(item, dict):
                continue
            partitions.append(
                PartitionEntry(
                    name=str(item.get("name", "")),
                    table=str(item.get("table", "")),
                    table_type=str(item.get("table_type", "")),
                    display_name=str(item.get("display_name", "")),
                    size=str(item.get("size", "")),
                    size_bytes=int(item.get("size_bytes", 0) or 0),
                    record_count=int(item.get("record_count", 0) or 0),
                    date=str(item.get("date", "")),
                    status=str(item.get("status", "")),
                ),
            )
        return partitions

    @staticmethod
    def _resolve_missing_partitions(partitions: list[PartitionEntry]) -> tuple[list[str], str]:
        current_date = time_utils.now().date()
        required_partitions: list[str] = []
        for offset in range(2):
            month_date = (current_date.replace(day=1) + timedelta(days=offset * 32)).replace(day=1)
            required_partitions.append(f"database_size_stats_{time_utils.format_china_time(month_date, '%Y_%m')}")

        existing = {partition.name for partition in partitions if partition.name}
        missing = [name for name in required_partitions if name not in existing]
        status = "healthy" if not missing else "warning"
        return missing, status

    @staticmethod
    def _normalize_period_type(requested: str) -> str:
        valid = {"daily", "weekly", "monthly", "quarterly"}
        normalized = (requested or "").strip().lower()
        if normalized not in valid:
            raise ValidationError("不支持的周期类型")
        return normalized

    @staticmethod
    def _add_months(base_date: date, months: int) -> date:
        month = base_date.month - 1 + months
        year = base_date.year + month // 12
        month = month % 12 + 1
        return date(year, month, 1)

    @classmethod
    def _period_end(cls, start_date: date, months: int) -> date:
        return cls._add_months(start_date, months) - timedelta(days=1)

    @classmethod
    def _resolve_period_window(cls, period_type: str, days: int, today: date) -> PeriodWindow:
        days = max(days, 1)
        if period_type == "daily":
            stats_end = today
            stats_start = stats_end - timedelta(days=days - 1)
            return PeriodWindow(
                period_start=stats_start,
                period_end=stats_end,
                stats_start=stats_start,
                stats_end=stats_end,
                step_mode="daily",
            )

        if period_type == "weekly":
            week_start = today - timedelta(days=today.weekday())
            period_end = week_start
            period_start = week_start - timedelta(weeks=days - 1)
            stats_end = period_end + timedelta(days=6)
            return PeriodWindow(
                period_start=period_start,
                period_end=period_end,
                stats_start=period_start,
                stats_end=stats_end,
                step_mode="weekly",
            )

        if period_type == "monthly":
            month_start = today.replace(day=1)
            period_end = month_start
            period_start = cls._add_months(month_start, -(days - 1))
            stats_end = cls._period_end(period_end, 1)
            return PeriodWindow(
                period_start=period_start,
                period_end=period_end,
                stats_start=period_start,
                stats_end=stats_end,
                step_mode="monthly",
            )

        quarter_month = ((today.month - 1) // 3) * 3 + 1
        quarter_start = date(today.year, quarter_month, 1)
        period_end = quarter_start
        period_start = cls._add_months(quarter_start, -3 * (days - 1))
        stats_end = cls._period_end(period_end, 3)
        return PeriodWindow(
            period_start=period_start,
            period_end=period_end,
            stats_start=period_start,
            stats_end=stats_end,
            step_mode="quarterly",
        )

    @classmethod
    def _build_daily_metrics(
        cls,
        window: PeriodWindow,
        db_stats: dict[date, int],
        instance_stats: dict[date, int],
        db_aggs: dict[date, int],
        instance_aggs: dict[date, int],
    ) -> defaultdict[str, dict[str, float]]:
        metrics: defaultdict[str, dict[str, float]] = defaultdict(
            lambda: {
                "instance_count": 0.0,
                "database_count": 0.0,
                "instance_aggregation_count": 0.0,
                "database_aggregation_count": 0.0,
            },
        )

        for collected_date, count in db_stats.items():
            metrics[collected_date.isoformat()]["database_count"] = float(count)

        for collected_date, count in instance_stats.items():
            metrics[collected_date.isoformat()]["instance_count"] = float(count)

        for period_start, count in db_aggs.items():
            metrics[period_start.isoformat()]["database_aggregation_count"] = float(count)

        for period_start, count in instance_aggs.items():
            metrics[period_start.isoformat()]["instance_aggregation_count"] = float(count)

        if window.step_mode != "daily":
            cls._rollup_period_metrics(window, metrics)

        return metrics

    @classmethod
    def _rollup_period_metrics(cls, window: PeriodWindow, daily_metrics: defaultdict[str, dict[str, float]]) -> None:
        buckets: defaultdict[str, dict[str, float]] = defaultdict(
            lambda: {
                "instance_count": 0.0,
                "database_count": 0.0,
                "instance_aggregation_count": 0.0,
                "database_aggregation_count": 0.0,
                "days_in_period": 0.0,
            },
        )

        for date_str, values in list(daily_metrics.items()):
            parsed = time_utils.to_china(f"{date_str}T00:00:00")
            if parsed is None:
                continue
            source_date = parsed.date()
            if window.step_mode == "weekly":
                key_date = source_date - timedelta(days=source_date.weekday())
            elif window.step_mode == "monthly":
                key_date = source_date.replace(day=1)
            else:
                quarter_month = ((source_date.month - 1) // 3) * 3 + 1
                key_date = source_date.replace(month=quarter_month, day=1)

            bucket = buckets[key_date.isoformat()]
            bucket["instance_count"] += values["instance_count"]
            bucket["database_count"] += values["database_count"]
            bucket["instance_aggregation_count"] += values["instance_aggregation_count"]
            bucket["database_aggregation_count"] += values["database_aggregation_count"]
            bucket["days_in_period"] += 1

        daily_metrics.clear()
        for key, values in buckets.items():
            if values["days_in_period"] <= 0:
                continue
            daily_metrics[key] = {
                "instance_count": round(values["instance_count"] / values["days_in_period"], 1),
                "database_count": round(values["database_count"] / values["days_in_period"], 1),
                "instance_aggregation_count": values["instance_aggregation_count"],
                "database_aggregation_count": values["database_aggregation_count"],
            }

    @classmethod
    def _compose_chart_payload(
        cls,
        period_type: str,
        window: PeriodWindow,
        daily_metrics: defaultdict[str, dict[str, float]],
    ) -> tuple[list[str], list[dict[str, Any]], str]:
        labels: list[str] = []
        instance_count_data: list[float] = []
        database_count_data: list[float] = []
        instance_aggregation_data: list[float] = []
        database_aggregation_data: list[float] = []

        cursor = window.stats_start if window.step_mode == "daily" else window.period_start
        limit_date = window.stats_end if window.step_mode == "daily" else window.period_end

        while cursor <= limit_date:
            key = cursor.isoformat()
            display_date = cls._display_label_date(cursor, window).isoformat()
            labels.append(display_date)
            values = daily_metrics.get(
                key,
                {
                    "instance_count": 0.0,
                    "database_count": 0.0,
                    "instance_aggregation_count": 0.0,
                    "database_aggregation_count": 0.0,
                },
            )
            instance_count_data.append(values["instance_count"])
            database_count_data.append(values["database_count"])
            instance_aggregation_data.append(values["instance_aggregation_count"])
            database_aggregation_data.append(values["database_aggregation_count"])

            if window.step_mode == "weekly":
                cursor += timedelta(weeks=1)
            elif window.step_mode == "monthly":
                cursor = cls._add_months(cursor, 1)
            elif window.step_mode == "quarterly":
                cursor = cls._add_months(cursor, 3)
            else:
                cursor += timedelta(days=1)

        instance_label, database_label, inst_agg_label, db_agg_label = cls._resolve_dataset_labels(period_type)

        datasets = [
            {
                "label": instance_label,
                "data": instance_count_data,
                "borderColor": "rgba(54, 162, 235, 0.7)",
                "backgroundColor": "rgba(54, 162, 235, 0.1)",
                "borderWidth": 4,
                "pointStyle": "circle",
                "tension": 0.1,
                "fill": False,
            },
            {
                "label": inst_agg_label,
                "data": instance_aggregation_data,
                "borderColor": "rgba(255, 99, 132, 0.7)",
                "backgroundColor": "rgba(255, 99, 132, 0.05)",
                "borderWidth": 3,
                "pointStyle": "triangle",
                "tension": 0.1,
                "fill": False,
            },
            {
                "label": database_label,
                "data": database_count_data,
                "borderColor": "rgba(75, 192, 192, 0.7)",
                "backgroundColor": "rgba(75, 192, 192, 0.1)",
                "borderWidth": 4,
                "pointStyle": "rect",
                "tension": 0.1,
                "fill": False,
            },
            {
                "label": db_agg_label,
                "data": database_aggregation_data,
                "borderColor": "rgba(255, 159, 64, 0.7)",
                "backgroundColor": "rgba(255, 159, 64, 0.05)",
                "borderWidth": 3,
                "pointStyle": "star",
                "tension": 0.1,
                "fill": False,
            },
        ]

        time_range = "-"
        if labels:
            time_range = f"{labels[0]} - {labels[-1]}"

        return labels, datasets, time_range

    @classmethod
    def _display_label_date(cls, source: date, window: PeriodWindow) -> date:
        if window.step_mode == "daily":
            return source
        if window.step_mode == "weekly":
            return source + timedelta(days=6)
        if window.step_mode == "monthly":
            return cls._period_end(source, 1)
        if window.step_mode == "quarterly":
            return cls._period_end(source, 3)
        return source

    @staticmethod
    def _resolve_dataset_labels(period_type: str) -> tuple[str, str, str, str]:
        mapping = {
            "daily": ("实例数总量", "数据库数总量", "实例日统计数量", "数据库日统计数量"),
            "weekly": ("实例数平均值(周)", "数据库数平均值(周)", "实例周统计数量", "数据库周统计数量"),
            "monthly": ("实例数平均值(月)", "数据库数平均值(月)", "实例月统计数量", "数据库月统计数量"),
            "quarterly": ("实例数平均值(季)", "数据库数平均值(季)", "实例季统计数量", "数据库季统计数量"),
        }
        return mapping.get(period_type, ("实例数总量", "数据库数总量", "实例统计数量", "数据库统计数量"))
