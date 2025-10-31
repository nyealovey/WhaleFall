"""
Instance-level aggregation runner.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import DatabaseError
from app.models.instance import Instance
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.services.aggregation.calculator import PeriodCalculator
from app.services.aggregation.results import AggregationStatus, InstanceSummary, PeriodSummary
from app.utils.structlog_config import log_debug, log_error, log_info, log_warning
from app.utils.time_utils import time_utils


class InstanceAggregationRunner:
    """负责实例级聚合的执行。"""

    def __init__(
        self,
        *,
        ensure_partition_for_date: Callable[[date], None],
        commit_with_partition_retry: Callable[[InstanceSizeAggregation, date], None],
        period_calculator: PeriodCalculator,
        module: str,
    ) -> None:
        self._ensure_partition_for_date = ensure_partition_for_date
        self._commit_with_partition_retry = commit_with_partition_retry
        self._period_calculator = period_calculator
        self._module = module

    def _invoke_callback(self, callback: Optional[Callable[..., None]], *args) -> None:
        if callback is None:
            return
        try:
            callback(*args)
        except Exception as exc:  # pragma: no cover
            log_warning(
                "聚合回调执行失败",
                module=self._module,
                callback=getattr(callback, "__name__", repr(callback)),
                error=str(exc),
            )

    def aggregate_period(
        self,
        period_type: str,
        start_date: date,
        end_date: date,
        *,
        on_instance_start: Callable[[Instance], None] | None = None,
        on_instance_complete: Callable[[Instance, dict[str, Any]], None] | None = None,
        on_instance_error: Callable[[Instance, dict[str, Any]], None] | None = None,
    ) -> Dict[str, Any]:
        """聚合所有激活实例在指定周期内的实例统计。"""
        instances = Instance.query.filter_by(is_active=True).all()
        summary = PeriodSummary(
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )

        for instance in instances:
            self._invoke_callback(on_instance_start, instance)
            try:
                stats = self._query_instance_stats(instance.id, start_date, end_date)
                if not stats:
                    summary.skipped_instances += 1
                    log_warning(
                        "实例在周期内没有实例大小统计数据，跳过实例聚合",
                        module=self._module,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        period_type=period_type,
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(),
                    )
                    result_payload = {
                        "status": AggregationStatus.SKIPPED.value,
                        "processed_records": 0,
                        "message": (
                            f"实例 {instance.name} 在 {start_date.isoformat()} 至 {end_date.isoformat()} "
                            f"没有实例统计数据，跳过聚合"
                        ),
                        "errors": [],
                        "period_type": period_type,
                        "period_start": start_date.isoformat(),
                        "period_end": end_date.isoformat(),
                        "instance_id": instance.id,
                        "instance_name": instance.name,
                    }
                    self._invoke_callback(on_instance_complete, instance, result_payload)
                    continue

                self._persist_instance_aggregation(
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                    start_date=start_date,
                    end_date=end_date,
                    stats=stats,
                )
                summary.total_records += 1
                summary.processed_instances += 1
                log_debug(
                    "实例聚合计算完成",
                    module=self._module,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                )
                result_payload = {
                    "status": AggregationStatus.COMPLETED.value,
                    "processed_records": len(stats),
                    "message": (
                        f"实例 {instance.name} 的 {period_type} 实例聚合完成 "
                        f"(处理 {len(stats)} 条记录)"
                    ),
                    "errors": [],
                    "period_type": period_type,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                }
                self._invoke_callback(on_instance_complete, instance, result_payload)
            except Exception as exc:  # pragma: no cover - 防御性日志
                db.session.rollback()
                summary.failed_instances += 1
                summary.errors.append(f"实例 {instance.name} 聚合失败: {exc}")
                log_error(
                    "实例聚合计算失败",
                    module=self._module,
                    exception=exc,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                )
                error_payload = {
                    "status": AggregationStatus.FAILED.value,
                    "error": str(exc),
                    "errors": [str(exc)],
                    "period_type": period_type,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                }
                self._invoke_callback(on_instance_error, instance, error_payload)

        total_instances = len(instances)
        if summary.status is AggregationStatus.COMPLETED:
            summary.message = (
                f"{period_type} 实例聚合完成：处理 {summary.processed_instances}/{total_instances} 个实例"
            )
        elif summary.status is AggregationStatus.SKIPPED:
            summary.message = f"{period_type} 实例聚合没有可处理的实例"
        else:
            summary.message = (
                f"{period_type} 实例聚合完成，{summary.failed_instances} 个实例失败"
            )

        return {
            **summary.to_dict(),
            "total_instances": total_instances,
        }

    def aggregate_instance_period(
        self,
        instance: Instance,
        *,
        period_type: str,
        start_date: date,
        end_date: date,
    ) -> InstanceSummary:
        """聚合单个实例的指定周期，并返回汇总信息。"""
        stats = self._query_instance_stats(instance.id, start_date, end_date)

        extra_details = {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        }
        if start_date == end_date:
            extra_details["period_date"] = start_date.isoformat()

        if not stats:
            log_warning(
                "实例在指定周期没有统计数据，跳过实例聚合",
                module=self._module,
                instance_id=instance.id,
                instance_name=instance.name,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            return InstanceSummary(
                instance_id=instance.id,
                instance_name=instance.name,
                period_type=period_type,
                message=f"实例 {instance.name} 在 {start_date} 到 {end_date} 没有统计数据，跳过聚合",
                extra=extra_details,
            )

        self._persist_instance_aggregation(
            instance_id=instance.id,
            instance_name=instance.name,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            stats=stats,
        )
        log_info(
            "实例周期聚合已更新",
            module=self._module,
            instance_id=instance.id,
            instance_name=instance.name,
            period_type=period_type,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        return InstanceSummary(
            instance_id=instance.id,
            instance_name=instance.name,
            period_type=period_type,
            processed_records=1,
            message=f"实例 {instance.name} 的 {period_type} 聚合已更新",
            extra=extra_details,
        )

    def _query_instance_stats(self, instance_id: int, start_date: date, end_date: date) -> List[InstanceSizeStat]:
        return InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance_id,
            InstanceSizeStat.collected_date >= start_date,
            InstanceSizeStat.collected_date <= end_date,
            InstanceSizeStat.is_deleted == False,
        ).all()

    def _persist_instance_aggregation(
        self,
        *,
        instance_id: int,
        instance_name: str | None,
        period_type: str,
        start_date: date,
        end_date: date,
        stats: List[InstanceSizeStat],
    ) -> None:
        try:
            self._ensure_partition_for_date(start_date)

            grouped = defaultdict(list)
            for stat in stats:
                grouped[stat.collected_date].append(stat)

            daily_totals: List[float] = []
            daily_db_counts: List[int] = []

            for day_stats in grouped.values():
                daily_totals.append(sum(stat.total_size_mb for stat in day_stats))
                daily_db_counts.append(sum(stat.database_count for stat in day_stats))

            aggregation = InstanceSizeAggregation.query.filter(
                InstanceSizeAggregation.instance_id == instance_id,
                InstanceSizeAggregation.period_type == period_type,
                InstanceSizeAggregation.period_start == start_date,
            ).first()

            if aggregation is None:
                aggregation = InstanceSizeAggregation(
                    instance_id=instance_id,
                    period_type=period_type,
                    period_start=start_date,
                    period_end=end_date,
                )

            aggregation.total_size_mb = int(sum(daily_totals) / len(daily_totals))
            if sum(daily_db_counts) > 0:
                aggregation.avg_size_mb = int(sum(daily_totals) / sum(daily_db_counts))
            else:
                aggregation.avg_size_mb = 0
            aggregation.max_size_mb = max(daily_totals)
            aggregation.min_size_mb = min(daily_totals)
            aggregation.data_count = len(daily_totals)

            aggregation.database_count = int(sum(daily_db_counts) / len(daily_db_counts))
            aggregation.avg_database_count = sum(daily_db_counts) / len(daily_db_counts)
            aggregation.max_database_count = max(daily_db_counts)
            aggregation.min_database_count = min(daily_db_counts)

            self._apply_change_statistics(
                aggregation=aggregation,
                instance_id=instance_id,
                period_type=period_type,
                start_date=start_date,
                end_date=end_date,
            )

            aggregation.calculated_at = time_utils.now()

            if aggregation.id is None:
                db.session.add(aggregation)

            self._commit_with_partition_retry(aggregation, start_date)

            log_debug(
                "实例聚合数据保存完成",
                module=self._module,
                instance_id=instance_id,
                instance_name=instance_name,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        except DatabaseError:
            raise
        except SQLAlchemyError as exc:  # pragma: no cover - defensive logging
            db.session.rollback()
            log_error(
                "实例聚合失败",
                module=self._module,
                exception=exc,
                instance_id=instance_id,
                instance_name=instance_name,
                period_type=period_type,
            )
            raise DatabaseError(
                message="实例聚合计算失败",
                extra={
                    "instance_id": instance_id,
                    "period_type": period_type,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive logging
            db.session.rollback()
            log_error(
                "实例聚合出现未知异常",
                module=self._module,
                exception=exc,
                instance_id=instance_id,
                instance_name=instance_name,
                period_type=period_type,
            )
            raise DatabaseError(
                message="实例聚合计算失败",
                extra={
                    "instance_id": instance_id,
                    "period_type": period_type,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            ) from exc

    def _apply_change_statistics(
        self,
        *,
        aggregation: InstanceSizeAggregation,
        instance_id: int,
        period_type: str,
        start_date: date,
        end_date: date,
    ) -> None:
        try:
            prev_start, prev_end = self._period_calculator.get_previous_period(
                period_type, start_date, end_date
            )

            prev_stats = InstanceSizeStat.query.filter(
                InstanceSizeStat.instance_id == instance_id,
                InstanceSizeStat.collected_date >= prev_start,
                InstanceSizeStat.collected_date <= prev_end,
                InstanceSizeStat.is_deleted == False,
            ).all()

            if not prev_stats:
                aggregation.total_size_change_mb = 0
                aggregation.total_size_change_percent = 0
                aggregation.database_count_change = 0
                aggregation.database_count_change_percent = 0
                aggregation.growth_rate = 0
                aggregation.trend_direction = "stable"
                return

            grouped = defaultdict(list)
            for stat in prev_stats:
                grouped[stat.collected_date].append(stat)

            prev_daily_totals = [
                sum(stat.total_size_mb for stat in day_stats) for day_stats in grouped.values()
            ]
            prev_daily_db_counts = [
                sum(stat.database_count for stat in day_stats) for day_stats in grouped.values()
            ]

            prev_avg_total = sum(prev_daily_totals) / len(prev_daily_totals)
            prev_avg_db_count = sum(prev_daily_db_counts) / len(prev_daily_db_counts)

            total_size_change_mb = aggregation.total_size_mb - prev_avg_total
            aggregation.total_size_change_mb = int(total_size_change_mb)
            aggregation.total_size_change_percent = round(
                (total_size_change_mb / prev_avg_total * 100) if prev_avg_total > 0 else 0,
                2,
            )

            db_count_change = aggregation.avg_database_count - prev_avg_db_count
            aggregation.database_count_change = int(db_count_change)
            aggregation.database_count_change_percent = round(
                (db_count_change / prev_avg_db_count * 100) if prev_avg_db_count > 0 else 0,
                2,
            )

            aggregation.growth_rate = aggregation.total_size_change_percent

            if aggregation.total_size_change_percent > 5:
                aggregation.trend_direction = "growing"
            elif aggregation.total_size_change_percent < -5:
                aggregation.trend_direction = "shrinking"
            else:
                aggregation.trend_direction = "stable"
        except Exception as exc:  # pragma: no cover - defensive logging
            log_error(
                "计算实例增量统计失败，使用默认值",
                module=self._module,
                exception=exc,
                instance_id=instance_id,
                period_type=period_type,
            )
            aggregation.total_size_change_mb = 0
            aggregation.total_size_change_percent = 0
            aggregation.database_count_change = 0
            aggregation.database_count_change_percent = 0
            aggregation.growth_rate = 0
            aggregation.trend_direction = "stable"


__all__ = ["InstanceAggregationRunner"]
