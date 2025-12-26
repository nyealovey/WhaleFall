"""Instance-level aggregation runner."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import DatabaseError
from app.models.instance import Instance
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.services.aggregation.callbacks import RunnerCallbacks
from app.services.aggregation.results import AggregationStatus, InstanceSummary, PeriodSummary
from app.utils.structlog_config import log_debug, log_error, log_info, log_warning
from app.utils.time_utils import time_utils

POSITIVE_GROWTH_THRESHOLD = 5
NEGATIVE_GROWTH_THRESHOLD = -5

AGGREGATION_RUNNER_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SQLAlchemyError,
    RuntimeError,
    ValueError,
    TypeError,
    ConnectionError,
)


@dataclass(slots=True)
class InstanceAggregationContext:
    """实例聚合所需的上下文信息."""

    instance_id: int
    instance_name: str | None
    period_type: str
    start_date: date
    end_date: date


if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date

    from app.services.aggregation.calculator import PeriodCalculator


class InstanceAggregationRunner:
    """负责实例级聚合的执行.

    从实例容量统计数据中计算各周期的聚合指标,包括总容量、平均值、
    数据库数量变化和增长趋势等.

    Attributes:
        _ensure_partition_for_date: 确保分区存在的回调函数.
        _commit_with_partition_retry: 提交数据的回调函数.
        _period_calculator: 周期计算器.
        _module: 模块名称,用于日志记录.

    """

    def __init__(
        self,
        *,
        ensure_partition_for_date: Callable[[date], None],
        commit_with_partition_retry: Callable[[date], None],
        period_calculator: PeriodCalculator,
        module: str,
    ) -> None:
        """初始化实例聚合执行器.

        Args:
            ensure_partition_for_date: 确保分区存在的回调函数.
            commit_with_partition_retry: 提交数据的回调函数.
            period_calculator: 周期计算器实例.
            module: 模块名称.

        """
        self._ensure_partition_for_date = ensure_partition_for_date
        self._commit_with_partition_retry = commit_with_partition_retry
        self._period_calculator = period_calculator
        self._module = module

    def _invoke_callback(self, callback: Callable[..., None] | None, *args: object) -> None:
        """安全地执行回调.

        Args:
            callback: 可选回调.
            *args: 传递给回调的参数.

        Returns:
            None

        """
        if callback is None:
            return
        try:
            callback(*args)
        except AGGREGATION_RUNNER_EXCEPTIONS as exc:  # pragma: no cover
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
        callbacks: RunnerCallbacks | None = None,
    ) -> dict[str, Any]:
        """聚合所有激活实例在指定周期内的实例统计.

        遍历所有活跃实例,为每个实例计算指定周期的整体聚合指标.

        Args:
            period_type: 周期类型,如 'daily'、'weekly'、'monthly'、'quarterly'.
            start_date: 周期开始日期.
            end_date: 周期结束日期.
            callbacks: 回调集合,用于实例开始/完成/错误时的钩子,可选.
            on_instance_start: 实例开始处理时的回调函数,可选.
            on_instance_complete: 实例处理完成时的回调函数,可选.
            on_instance_error: 实例处理失败时的回调函数,可选.

        Returns:
            周期聚合结果字典,包含处理统计和错误信息.

        """
        instances = Instance.query.filter_by(is_active=True).all()
        summary = PeriodSummary(
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )

        callback_set = callbacks or RunnerCallbacks()

        for instance in instances:
            self._invoke_callback(callback_set.on_instance_start, instance)
            try:
                with db.session.begin_nested():
                    stats = self._query_instance_stats(instance.id, start_date, end_date)
                    if stats:
                        context = InstanceAggregationContext(
                            instance_id=instance.id,
                            instance_name=instance.name,
                            period_type=period_type,
                            start_date=start_date,
                            end_date=end_date,
                        )
                        self._persist_instance_aggregation(context=context, stats=stats)

                if not stats:
                    summary.skipped_instances += 1
                    log_warning(
                        "实例在周期内没有实例大小统计数据,跳过实例聚合",
                        module=self._module,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        period_type=period_type,
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(),
                    )
                    period_range = f"{start_date.isoformat()} 至 {end_date.isoformat()}"
                    result_payload = {
                        "status": AggregationStatus.SKIPPED.value,
                        "processed_records": 0,
                        "message": f"实例 {instance.name} 在 {period_range} 没有实例统计数据,跳过聚合",
                        "errors": [],
                        "period_type": period_type,
                        "period_start": start_date.isoformat(),
                        "period_end": end_date.isoformat(),
                        "instance_id": instance.id,
                        "instance_name": instance.name,
                    }
                    self._invoke_callback(callback_set.on_instance_complete, instance, result_payload)
                    continue

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
                    "message": f"实例 {instance.name} 的 {period_type} 实例聚合完成 (处理 {len(stats)} 条记录)",
                    "errors": [],
                    "period_type": period_type,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                }
                self._invoke_callback(callback_set.on_instance_complete, instance, result_payload)
            except AGGREGATION_RUNNER_EXCEPTIONS as exc:  # pragma: no cover - 防御性日志
                summary.failed_instances += 1
                summary.errors.append(f"实例 {instance.name} 聚合失败: {exc}")
                log_error(
                    "实例聚合计算失败",
                    module=self._module,
                    exception=self._to_exception(exc),
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                )
                error_payload = {
                    "status": AggregationStatus.FAILED.value,
                    "message": f"实例 {instance.name} 的 {period_type} 聚合失败",
                    "error": str(exc),
                    "errors": [str(exc)],
                    "period_type": period_type,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                }
                self._invoke_callback(callback_set.on_instance_error, instance, error_payload)

        total_instances = len(instances)
        if summary.status is AggregationStatus.COMPLETED:
            summary.message = f"{period_type} 实例聚合完成:处理 {summary.processed_instances}/{total_instances} 个实例"
        elif summary.status is AggregationStatus.SKIPPED:
            summary.message = f"{period_type} 实例聚合没有可处理的实例"
        else:
            summary.message = f"{period_type} 实例聚合完成,{summary.failed_instances} 个实例失败"

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
        """聚合单个实例的指定周期,并返回汇总信息.

        Args:
            instance: 数据库实例对象.
            period_type: 周期类型.
            start_date: 周期开始日期.
            end_date: 周期结束日期.

        Returns:
            实例聚合汇总信息.

        """
        stats = self._query_instance_stats(instance.id, start_date, end_date)

        extra_details = {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        }
        if start_date == end_date:
            extra_details["period_date"] = start_date.isoformat()

        if not stats:
            log_warning(
                "实例在指定周期没有统计数据,跳过实例聚合",
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
                message=f"实例 {instance.name} 在 {start_date} 到 {end_date} 没有统计数据,跳过聚合",
                extra=extra_details,
            )

        context = InstanceAggregationContext(
            instance_id=instance.id,
            instance_name=instance.name,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        with db.session.begin_nested():
            self._persist_instance_aggregation(context=context, stats=stats)
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

    def _query_instance_stats(self, instance_id: int, start_date: date, end_date: date) -> list[InstanceSizeStat]:
        """查询实例在指定时间段的统计记录.

        Args:
            instance_id: 实例 ID.
            start_date: 起始日期.
            end_date: 截止日期.

        Returns:
            list[InstanceSizeStat]: 匹配的统计记录.

        """
        return InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance_id,
            InstanceSizeStat.collected_date >= start_date,
            InstanceSizeStat.collected_date <= end_date,
            InstanceSizeStat.is_deleted.is_(False),
        ).all()

    def _persist_instance_aggregation(
        self,
        *,
        context: InstanceAggregationContext,
        stats: list[InstanceSizeStat],
    ) -> None:
        """保存实例聚合结果.

        Args:
            context: 聚合上下文,包含实例信息与周期范围.
            stats: 用于计算的统计记录列表.

        Returns:
            None

        """
        try:
            self._ensure_partition_for_date(context.start_date)

            grouped = defaultdict(list)
            for stat in stats:
                grouped[stat.collected_date].append(stat)

            daily_totals: list[float] = []
            daily_db_counts: list[int] = []

            for day_stats in grouped.values():
                daily_totals.append(sum(stat.total_size_mb for stat in day_stats))
                daily_db_counts.append(sum(stat.database_count for stat in day_stats))

            aggregation = InstanceSizeAggregation.query.filter(
                InstanceSizeAggregation.instance_id == context.instance_id,
                InstanceSizeAggregation.period_type == context.period_type,
                InstanceSizeAggregation.period_start == context.start_date,
            ).first()

            if aggregation is None:
                aggregation = InstanceSizeAggregation()
                agg_any_new = cast(Any, aggregation)
                agg_any_new.instance_id = context.instance_id
                agg_any_new.period_type = context.period_type
                agg_any_new.period_start = context.start_date
                agg_any_new.period_end = context.end_date

            agg_any = cast(Any, aggregation)
            normalized_totals = [float(total) for total in daily_totals]
            total_size = float(sum(normalized_totals) / len(normalized_totals))
            agg_any.total_size_mb = int(total_size)
            if sum(daily_db_counts) > 0:
                agg_any.avg_size_mb = int(sum(normalized_totals) / sum(daily_db_counts))
            else:
                agg_any.avg_size_mb = 0
            agg_any.max_size_mb = int(max(normalized_totals))
            agg_any.min_size_mb = int(min(normalized_totals))
            agg_any.data_count = len(normalized_totals)

            agg_any.database_count = int(sum(daily_db_counts) / len(daily_db_counts))
            agg_any.avg_database_count = float(sum(daily_db_counts) / len(daily_db_counts))
            agg_any.max_database_count = int(max(daily_db_counts))
            agg_any.min_database_count = int(min(daily_db_counts))

            self._apply_change_statistics(aggregation=aggregation, context=context)

            agg_any.calculated_at = time_utils.now()

            if aggregation.id is None:
                db.session.add(aggregation)

            self._commit_with_partition_retry(context.start_date)

            log_debug(
                "实例聚合数据保存完成",
                module=self._module,
                instance_id=context.instance_id,
                instance_name=context.instance_name,
                period_type=context.period_type,
                start_date=context.start_date.isoformat(),
                end_date=context.end_date.isoformat(),
            )
        except DatabaseError:
            raise
        except SQLAlchemyError as exc:  # pragma: no cover - defensive logging
            log_error(
                "实例聚合失败",
                module=self._module,
                exception=exc,
                instance_id=context.instance_id,
                instance_name=context.instance_name,
                period_type=context.period_type,
            )
            raise DatabaseError(
                message="实例聚合计算失败",
                extra={
                    "instance_id": context.instance_id,
                    "period_type": context.period_type,
                    "start_date": context.start_date.isoformat(),
                    "end_date": context.end_date.isoformat(),
                },
            ) from exc
        except AGGREGATION_RUNNER_EXCEPTIONS as exc:  # pragma: no cover - defensive logging
            log_error(
                "实例聚合出现未知异常",
                module=self._module,
                exception=self._to_exception(exc),
                instance_id=context.instance_id,
                instance_name=context.instance_name,
                period_type=context.period_type,
            )
            raise DatabaseError(
                message="实例聚合计算失败",
                extra={
                    "instance_id": context.instance_id,
                    "period_type": context.period_type,
                    "start_date": context.start_date.isoformat(),
                    "end_date": context.end_date.isoformat(),
                },
            ) from exc

    def _apply_change_statistics(
        self,
        *,
        aggregation: InstanceSizeAggregation,
        context: InstanceAggregationContext,
    ) -> None:
        """计算实例聚合的增量统计.

        Args:
            aggregation: 聚合记录.
            context: 聚合上下文,包含实例与周期信息.

        Returns:
            None

        """
        try:
            prev_start, prev_end = self._period_calculator.get_previous_period(
                context.period_type,
                context.start_date,
                context.end_date,
            )

            prev_stats = InstanceSizeStat.query.filter(
                InstanceSizeStat.instance_id == context.instance_id,
                InstanceSizeStat.collected_date >= prev_start,
                InstanceSizeStat.collected_date <= prev_end,
                InstanceSizeStat.is_deleted.is_(False),
            ).all()

            agg_any = cast(Any, aggregation)
            if not prev_stats:
                agg_any.total_size_change_mb = 0
                agg_any.total_size_change_percent = 0
                agg_any.database_count_change = 0
                agg_any.database_count_change_percent = 0
                agg_any.growth_rate = 0
                agg_any.trend_direction = "stable"
                return

            grouped = defaultdict(list)
            for stat in prev_stats:
                grouped[stat.collected_date].append(stat)

            prev_daily_totals = [sum(stat.total_size_mb for stat in day_stats) for day_stats in grouped.values()]
            prev_daily_db_counts = [sum(stat.database_count for stat in day_stats) for day_stats in grouped.values()]

            prev_avg_total = sum(prev_daily_totals) / len(prev_daily_totals)
            prev_avg_db_count = sum(prev_daily_db_counts) / len(prev_daily_db_counts)

            current_total = self._to_float(aggregation.total_size_mb)
            total_size_change_mb = current_total - prev_avg_total
            agg_any.total_size_change_mb = int(total_size_change_mb)
            agg_any.total_size_change_percent = round(
                (total_size_change_mb / prev_avg_total * 100) if prev_avg_total > 0 else 0,
                2,
            )

            current_avg_db = self._to_float(aggregation.avg_database_count)
            db_count_change = current_avg_db - prev_avg_db_count
            agg_any.database_count_change = int(db_count_change)
            agg_any.database_count_change_percent = round(
                (db_count_change / prev_avg_db_count * 100) if prev_avg_db_count > 0 else 0,
                2,
            )

            agg_any.growth_rate = agg_any.total_size_change_percent

            if agg_any.total_size_change_percent > POSITIVE_GROWTH_THRESHOLD:
                agg_any.trend_direction = "growing"
            elif agg_any.total_size_change_percent < NEGATIVE_GROWTH_THRESHOLD:
                agg_any.trend_direction = "shrinking"
            else:
                agg_any.trend_direction = "stable"
        except AGGREGATION_RUNNER_EXCEPTIONS as exc:  # pragma: no cover - defensive logging
            log_error(
                "计算实例增量统计失败,使用默认值",
                module=self._module,
                exception=self._to_exception(exc),
                instance_id=context.instance_id,
                period_type=context.period_type,
            )
            agg_any = cast(Any, aggregation)
            agg_any.total_size_change_mb = 0
            agg_any.total_size_change_percent = 0
            agg_any.database_count_change = 0
            agg_any.database_count_change_percent = 0
            agg_any.growth_rate = 0
            agg_any.trend_direction = "stable"

    @staticmethod
    def _to_float(value: Any) -> float:
        """将列值安全转换为 float."""
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    @staticmethod
    def _to_exception(exc: BaseException) -> Exception:
        """将 BaseException 归一为 Exception 便于日志记录."""
        if isinstance(exc, Exception):
            return exc
        return Exception(str(exc))


__all__ = ["InstanceAggregationRunner"]
