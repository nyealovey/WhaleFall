"""Database-level aggregation runner."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import DatabaseError
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.services.aggregation.callbacks import RunnerCallbacks
from app.services.aggregation.results import AggregationStatus, InstanceSummary, PeriodSummary
from app.utils.structlog_config import log_debug, log_error, log_info, log_warning
from app.utils.time_utils import time_utils

AGGREGATION_RUNNER_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SQLAlchemyError,
    RuntimeError,
    ValueError,
    TypeError,
    ConnectionError,
)


@dataclass(slots=True)
class DatabaseAggregationContext:
    """描述数据库聚合所需的上下文信息."""

    instance_id: int
    instance_name: str | None
    database_name: str
    period_type: str
    start_date: date
    end_date: date


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from datetime import date

    from app.services.aggregation.calculator import PeriodCalculator


class DatabaseAggregationRunner:
    """负责数据库级聚合的执行.

    从数据库容量统计数据中计算各周期的聚合指标,包括平均值、最大值、
    最小值、变化量和增长率等.

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
        commit_with_partition_retry: Callable[[DatabaseSizeAggregation, date], None],
        period_calculator: PeriodCalculator,
        module: str,
    ) -> None:
        """初始化数据库聚合执行器.

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
        """安全执行回调.

        Args:
            callback: 可选回调函数.
            *args: 传递给回调的参数.

        Returns:
            None

        """
        if callback is None:
            return
        try:
            callback(*args)
        except AGGREGATION_RUNNER_EXCEPTIONS as exc:  # pragma: no cover - 防御性处理
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
        """聚合所有激活实例在指定周期内的数据库统计.

        遍历所有活跃实例,为每个实例的每个数据库计算指定周期的聚合指标.

        Args:
            period_type: 周期类型,如 'daily'、'weekly'、'monthly'、'quarterly'.
            start_date: 周期开始日期.
            end_date: 周期结束日期.
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
                stats = self._query_database_stats(instance.id, start_date, end_date)
                if not stats:
                    summary.skipped_instances += 1
                    log_warning(
                        "实例在周期内没有数据库容量数据,跳过聚合",
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
                        "message": f"实例 {instance.name} 在 {period_range} 没有数据库容量数据,跳过聚合",
                        "errors": [],
                        "period_type": period_type,
                        "period_start": start_date.isoformat(),
                        "period_end": end_date.isoformat(),
                        "instance_id": instance.id,
                        "instance_name": instance.name,
                    }
                    self._invoke_callback(callback_set.on_instance_complete, instance, result_payload)
                    continue

                grouped = self._group_by_database(stats)
                for database_name, db_stats in grouped.items():
                    context = DatabaseAggregationContext(
                        instance_id=instance.id,
                        instance_name=instance.name,
                        database_name=database_name,
                        period_type=period_type,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    self._persist_database_aggregation(context, db_stats)
                    summary.total_records += 1

                summary.processed_instances += 1
                log_debug(
                    "实例数据库聚合计算完成",
                    module=self._module,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                    database_count=len(grouped),
                )
                result_payload = {
                    "status": AggregationStatus.COMPLETED.value,
                    "processed_records": len(grouped),
                    "message": f"实例 {instance.name} 的 {period_type} 数据库聚合完成 (处理 {len(grouped)} 个数据库)",
                    "errors": [],
                    "period_type": period_type,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                }
                self._invoke_callback(callback_set.on_instance_complete, instance, result_payload)
            except AGGREGATION_RUNNER_EXCEPTIONS as exc:  # pragma: no cover - 防御性日志
                db.session.rollback()
                summary.failed_instances += 1
                summary.errors.append(f"实例 {instance.name} 聚合失败: {exc}")
                log_error(
                    "实例数据库聚合执行失败",
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
                self._invoke_callback(callback_set.on_instance_error, instance, error_payload)

        total_instances = len(instances)
        if summary.status is AggregationStatus.COMPLETED:
            summary.message = f"{period_type} 聚合完成:处理 {summary.processed_instances}/{total_instances} 个实例"
        elif summary.status is AggregationStatus.SKIPPED:
            summary.message = f"{period_type} 聚合没有可处理的数据"
        else:
            summary.message = f"{period_type} 聚合完成,{summary.failed_instances} 个实例失败"

        return {
            **summary.to_dict(),
            "total_instances": total_instances,
        }

    def aggregate_database_period(
        self,
        instance: Instance,
        *,
        period_type: str,
        start_date: date,
        end_date: date,
    ) -> InstanceSummary:
        """为指定实例计算指定周期的数据库级聚合.

        Args:
            instance: 数据库实例对象.
            period_type: 周期类型.
            start_date: 周期开始日期.
            end_date: 周期结束日期.

        Returns:
            实例聚合汇总信息.

        """
        stats = self._query_database_stats(instance.id, start_date, end_date)

        extra_details = {
            "period_type": period_type,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        }
        if start_date == end_date:
            extra_details["period_date"] = start_date.isoformat()

        if not stats:
            period_range = f"{start_date.isoformat()} 至 {end_date.isoformat()}"
            log_warning(
                "实例在指定周期没有数据库容量数据,跳过聚合",
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
                message=f"实例 {instance.name} 在 {period_range} 没有数据库容量数据,跳过聚合",
                extra=extra_details,
            )

        grouped = self._group_by_database(stats)
        processed = 0
        for database_name, db_stats in grouped.items():
            context = DatabaseAggregationContext(
                instance_id=instance.id,
                instance_name=instance.name,
                database_name=database_name,
                period_type=period_type,
                start_date=start_date,
                end_date=end_date,
            )
            self._persist_database_aggregation(
                context=context,
                stats=db_stats,
            )
            processed += 1

        log_info(
            "实例数据库周期聚合已更新",
            module=self._module,
            instance_id=instance.id,
            instance_name=instance.name,
            period_type=period_type,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            processed_databases=processed,
        )
        return InstanceSummary(
            instance_id=instance.id,
            instance_name=instance.name,
            period_type=period_type,
            processed_records=processed,
            message=f"实例 {instance.name} 的 {period_type} 数据库聚合已更新 ({processed} 个数据库)",
            extra=extra_details,
        )

    def aggregate_daily_for_instance(self, instance: Instance, target_date: date) -> InstanceSummary:
        """为指定实例计算当天数据库级聚合.

        Args:
            instance: 数据库实例对象.
            target_date: 目标日期.

        Returns:
            实例聚合汇总信息.

        """
        return self.aggregate_database_period(
            instance,
            period_type="daily",
            start_date=target_date,
            end_date=target_date,
        )

    def _query_database_stats(self, instance_id: int, start_date: date, end_date: date) -> list[DatabaseSizeStat]:
        """查询实例在指定时间范围内的容量数据.

        Args:
            instance_id: 实例 ID.
            start_date: 起始日期.
            end_date: 截止日期.

        Returns:
            list[DatabaseSizeStat]: 匹配的统计记录.

        """
        return DatabaseSizeStat.query.filter(
            DatabaseSizeStat.instance_id == instance_id,
            DatabaseSizeStat.collected_date >= start_date,
            DatabaseSizeStat.collected_date <= end_date,
        ).all()

    def _group_by_database(self, stats: Iterable[DatabaseSizeStat]) -> dict[str, list[DatabaseSizeStat]]:
        """按数据库名称分组统计数据.

        Args:
            stats: 统计记录列表.

        Returns:
            dict[str, list[DatabaseSizeStat]]: 以数据库名为键的分组结果.

        """
        grouped: dict[str, list[DatabaseSizeStat]] = defaultdict(list)
        for stat in stats:
            grouped[stat.database_name].append(stat)
        return grouped

    def _persist_database_aggregation(
        self,
        context: DatabaseAggregationContext,
        stats: list[DatabaseSizeStat],
    ) -> None:
        """保存单个数据库的聚合结果.

        Args:
            context: 包含实例/数据库/周期范围的聚合上下文.
            stats: 用于计算的容量记录列表.

        Returns:
            None

        """
        start_date = context.start_date
        try:
            self._ensure_partition_for_date(start_date)

            sizes = [stat.size_mb for stat in stats]
            data_sizes = [stat.data_size_mb for stat in stats if stat.data_size_mb is not None]

            aggregation = DatabaseSizeAggregation.query.filter(
                DatabaseSizeAggregation.instance_id == context.instance_id,
                DatabaseSizeAggregation.database_name == context.database_name,
                DatabaseSizeAggregation.period_type == context.period_type,
                DatabaseSizeAggregation.period_start == context.start_date,
            ).first()

            if aggregation is None:
                aggregation = DatabaseSizeAggregation(
                    instance_id=context.instance_id,
                    database_name=context.database_name,
                    period_type=context.period_type,
                    period_start=context.start_date,
                    period_end=context.end_date,
                )

            aggregation.avg_size_mb = int(sum(sizes) / len(sizes))
            aggregation.max_size_mb = max(sizes)
            aggregation.min_size_mb = min(sizes)
            aggregation.data_count = len(stats)

            if data_sizes:
                aggregation.avg_data_size_mb = int(sum(data_sizes) / len(data_sizes))
                aggregation.max_data_size_mb = max(data_sizes)
                aggregation.min_data_size_mb = min(data_sizes)
            else:
                aggregation.avg_data_size_mb = None
                aggregation.max_data_size_mb = None
                aggregation.min_data_size_mb = None

            aggregation.avg_log_size_mb = None
            aggregation.max_log_size_mb = None
            aggregation.min_log_size_mb = None

            self._apply_change_statistics(aggregation=aggregation, context=context)

            aggregation.calculated_at = time_utils.now()

            if aggregation.id is None:
                db.session.add(aggregation)

            self._commit_with_partition_retry(aggregation, start_date)

            log_debug(
                "数据库聚合数据保存完成",
                module=self._module,
                instance_id=context.instance_id,
                instance_name=context.instance_name,
                database_name=context.database_name,
                period_type=context.period_type,
                start_date=context.start_date.isoformat(),
                end_date=context.end_date.isoformat(),
            )
        except DatabaseError:
            raise
        except SQLAlchemyError as exc:  # pragma: no cover - defensive logging
            db.session.rollback()
            log_error(
                "计算数据库聚合失败",
                module=self._module,
                exception=exc,
                instance_id=context.instance_id,
                instance_name=context.instance_name,
                database_name=context.database_name,
                period_type=context.period_type,
            )
            raise DatabaseError(
                message="数据库聚合计算失败",
                extra={
                    "instance_id": context.instance_id,
                    "database_name": context.database_name,
                    "period_type": context.period_type,
                    "start_date": context.start_date.isoformat(),
                    "end_date": context.end_date.isoformat(),
                },
            ) from exc
        except AGGREGATION_RUNNER_EXCEPTIONS as exc:  # pragma: no cover - 防御性日志
            db.session.rollback()
            log_error(
                "数据库聚合出现未知异常",
                module=self._module,
                exception=exc,
                instance_id=context.instance_id,
                instance_name=context.instance_name,
                database_name=context.database_name,
                period_type=context.period_type,
            )
            raise DatabaseError(
                message="数据库聚合计算失败",
                extra={
                    "instance_id": context.instance_id,
                    "database_name": context.database_name,
                    "period_type": context.period_type,
                    "start_date": context.start_date.isoformat(),
                    "end_date": context.end_date.isoformat(),
                },
            ) from exc

    def _apply_change_statistics(
        self,
        *,
        aggregation: DatabaseSizeAggregation,
        context: DatabaseAggregationContext,
    ) -> None:
        """计算相邻周期的增量统计.

        Args:
            aggregation: 即将保存的聚合实例.
            context: 聚合上下文,包含实例、数据库及周期范围.

        Returns:
            None

        """
        try:
            prev_start, prev_end = self._period_calculator.get_previous_period(
                context.period_type,
                context.start_date,
                context.end_date,
            )

            prev_stats = DatabaseSizeStat.query.filter(
                DatabaseSizeStat.instance_id == context.instance_id,
                DatabaseSizeStat.database_name == context.database_name,
                DatabaseSizeStat.collected_date >= prev_start,
                DatabaseSizeStat.collected_date <= prev_end,
            ).all()

            if not prev_stats:
                aggregation.size_change_mb = 0
                aggregation.size_change_percent = 0
                aggregation.data_size_change_mb = 0
                aggregation.data_size_change_percent = 0
                aggregation.log_size_change_mb = 0
                aggregation.log_size_change_percent = 0
                aggregation.trend_direction = "stable"
                aggregation.growth_rate = 0
                return

            prev_sizes = [stat.size_mb for stat in prev_stats]
            prev_avg_size = sum(prev_sizes) / len(prev_sizes)

            prev_data_sizes = [stat.data_size_mb for stat in prev_stats if stat.data_size_mb is not None]
            prev_avg_data_size = sum(prev_data_sizes) / len(prev_data_sizes) if prev_data_sizes else None

            size_change_mb = aggregation.avg_size_mb - prev_avg_size
            aggregation.size_change_mb = int(size_change_mb)
            aggregation.size_change_percent = round(
                (size_change_mb / prev_avg_size * 100) if prev_avg_size > 0 else 0,
                2,
            )

            if prev_avg_data_size is not None and aggregation.avg_data_size_mb is not None:
                data_size_change_mb = aggregation.avg_data_size_mb - prev_avg_data_size
                aggregation.data_size_change_mb = int(data_size_change_mb)
                aggregation.data_size_change_percent = round(
                    (data_size_change_mb / prev_avg_data_size * 100) if prev_avg_data_size > 0 else 0,
                    2,
                )
            else:
                aggregation.data_size_change_mb = 0
                aggregation.data_size_change_percent = 0

            aggregation.log_size_change_mb = None
            aggregation.log_size_change_percent = None
            aggregation.growth_rate = aggregation.size_change_percent
        except AGGREGATION_RUNNER_EXCEPTIONS as exc:  # pragma: no cover - 防御性日志
            log_error(
                "计算数据库增量统计失败,使用默认值",
                module=self._module,
                exception=exc,
                instance_id=context.instance_id,
                database_name=context.database_name,
                period_type=context.period_type,
            )
            aggregation.size_change_mb = 0
            aggregation.size_change_percent = 0
            aggregation.data_size_change_mb = 0
            aggregation.data_size_change_percent = 0
            aggregation.log_size_change_mb = 0
            aggregation.log_size_change_percent = 0
            aggregation.growth_rate = 0


__all__ = ["DatabaseAggregationRunner"]
