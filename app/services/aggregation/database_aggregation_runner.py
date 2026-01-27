"""Database-level aggregation runner."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance import Instance
from app.repositories.aggregation_runner_repository import AggregationRunnerRepository
from app.repositories.instances_repository import InstancesRepository
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
class DatabasePeriodMetrics:
    """数据库在周期内的聚合指标."""

    database_name: str
    avg_size_mb: int
    max_size_mb: int
    min_size_mb: int
    data_count: int
    avg_data_size_mb: int | None
    max_data_size_mb: int | None
    min_data_size_mb: int | None


if TYPE_CHECKING:
    from collections.abc import Callable
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
        commit_with_partition_retry: Callable[[date], None],
        period_calculator: PeriodCalculator,
        module: str,
        repository: AggregationRunnerRepository | None = None,
    ) -> None:
        """初始化数据库聚合执行器.

        Args:
            ensure_partition_for_date: 确保分区存在的回调函数.
            commit_with_partition_retry: 提交数据的回调函数.
            period_calculator: 周期计算器实例.
            module: 模块名称.
            repository: 聚合执行仓库(可选,用于依赖注入).

        """
        self._ensure_partition_for_date = ensure_partition_for_date
        self._commit_with_partition_retry = commit_with_partition_retry
        self._period_calculator = period_calculator
        self._module = module
        self._repository = repository or AggregationRunnerRepository()

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
        except AGGREGATION_RUNNER_EXCEPTIONS as exc:
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
            callbacks: 回调集合,用于实例开始/完成/错误时的钩子,可选.
            on_instance_start: 实例开始处理时的回调函数,可选.
            on_instance_complete: 实例处理完成时的回调函数,可选.
            on_instance_error: 实例处理失败时的回调函数,可选.

        Returns:
            周期聚合结果字典,包含处理统计和错误信息.

        """
        instances = InstancesRepository.list_active_instances()
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
                    processed = self._aggregate_databases_for_instance(
                        instance=instance,
                        period_type=period_type,
                        start_date=start_date,
                        end_date=end_date,
                    )
                if processed == 0:
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

                summary.total_records += processed
                summary.processed_instances += 1
                log_debug(
                    "实例数据库聚合计算完成",
                    module=self._module,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                    database_count=processed,
                )
                result_payload = {
                    "status": AggregationStatus.COMPLETED.value,
                    "processed_records": processed,
                    "message": f"实例 {instance.name} 的 {period_type} 数据库聚合完成 (处理 {processed} 个数据库)",
                    "errors": [],
                    "period_type": period_type,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                }
                self._invoke_callback(callback_set.on_instance_complete, instance, result_payload)
            except AGGREGATION_RUNNER_EXCEPTIONS as exc:
                summary.failed_instances += 1
                summary.errors.append(f"实例 {instance.name} 聚合失败: {exc}")
                log_error(
                    "实例数据库聚合执行失败",
                    module=self._module,
                    exception=self._to_exception(exc),
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                )
                error_payload = {
                    "status": AggregationStatus.FAILED.value,
                    "message": f"实例 {instance.name} 的 {period_type} 数据库聚合失败",
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
        extra_details = {
            "period_type": period_type,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        }
        if start_date == end_date:
            extra_details["period_date"] = start_date.isoformat()

        with db.session.begin_nested():
            processed = self._aggregate_databases_for_instance(
                instance=instance,
                period_type=period_type,
                start_date=start_date,
                end_date=end_date,
            )
        if processed == 0:
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

    def _query_database_period_metrics(
        self,
        *,
        instance_id: int,
        start_date: date,
        end_date: date,
    ) -> list[DatabasePeriodMetrics]:
        """查询指定周期的数据库聚合指标.

        通过数据库侧聚合计算 avg/max/min/count,避免拉取大量明细记录再在 Python 中分组.

        Args:
            instance_id: 实例 ID.
            start_date: 周期开始日期.
            end_date: 周期结束日期.

        Returns:
            list[DatabasePeriodMetrics]: 每个数据库的聚合指标列表.

        """
        rows = self._repository.list_database_size_stat_metrics(
            instance_id=instance_id,
            start_date=start_date,
            end_date=end_date,
        )

        metrics: list[DatabasePeriodMetrics] = []
        for row in rows:
            database_name = str(row.database_name) if row.database_name is not None else ""
            metrics.append(
                DatabasePeriodMetrics(
                    database_name=database_name,
                    avg_size_mb=self._to_int_value(row.avg_size_mb),
                    max_size_mb=self._to_int_value(row.max_size_mb),
                    min_size_mb=self._to_int_value(row.min_size_mb),
                    data_count=int(row.data_count) if row.data_count is not None else 0,
                    avg_data_size_mb=self._to_optional_int(row.avg_data_size_mb),
                    max_data_size_mb=self._to_optional_int(row.max_data_size_mb),
                    min_data_size_mb=self._to_optional_int(row.min_data_size_mb),
                ),
            )

        return metrics

    def _query_previous_period_averages(
        self,
        *,
        instance_id: int,
        period_type: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, tuple[float, float | None]]:
        """查询上一周期各数据库的平均值,用于计算增量指标."""
        prev_start, prev_end = self._period_calculator.get_previous_period(period_type, start_date, end_date)
        rows = self._repository.list_database_size_stat_averages(
            instance_id=instance_id,
            start_date=prev_start,
            end_date=prev_end,
        )

        averages: dict[str, tuple[float, float | None]] = {}
        for row in rows:
            database_name = str(row.database_name) if row.database_name is not None else ""
            avg_size = self._to_float(row.avg_size_mb)
            avg_data_size = self._to_float(row.avg_data_size_mb) if row.avg_data_size_mb is not None else None
            averages[database_name] = (avg_size, avg_data_size)
        return averages

    def _aggregate_databases_for_instance(
        self,
        *,
        instance: Instance,
        period_type: str,
        start_date: date,
        end_date: date,
    ) -> int:
        """为单实例执行数据库级聚合并返回处理的数据库数量."""
        metrics = self._query_database_period_metrics(
            instance_id=instance.id,
            start_date=start_date,
            end_date=end_date,
        )
        if not metrics:
            return 0

        self._ensure_partition_for_date(start_date)

        existing = self._repository.list_existing_database_aggregations(
            instance_id=instance.id,
            period_type=period_type,
            period_start=start_date,
        )
        existing_by_db: dict[str, DatabaseSizeAggregation] = {cast(str, agg.database_name): agg for agg in existing}

        previous_averages = self._query_previous_period_averages(
            instance_id=instance.id,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )

        for metric in metrics:
            aggregation = existing_by_db.get(metric.database_name)
            if aggregation is None:
                aggregation = DatabaseSizeAggregation()
                agg_any_new = cast(Any, aggregation)
                agg_any_new.instance_id = instance.id
                agg_any_new.database_name = metric.database_name
                agg_any_new.period_type = period_type
                agg_any_new.period_start = start_date
                agg_any_new.period_end = end_date
                db.session.add(aggregation)

            agg_any = cast(Any, aggregation)
            agg_any.avg_size_mb = metric.avg_size_mb
            agg_any.max_size_mb = metric.max_size_mb
            agg_any.min_size_mb = metric.min_size_mb
            agg_any.data_count = metric.data_count

            agg_any.avg_data_size_mb = metric.avg_data_size_mb
            agg_any.max_data_size_mb = metric.max_data_size_mb
            agg_any.min_data_size_mb = metric.min_data_size_mb

            agg_any.avg_log_size_mb = None
            agg_any.max_log_size_mb = None
            agg_any.min_log_size_mb = None

            prev_values = previous_averages.get(metric.database_name)
            prev_avg_size_mb = prev_values[0] if prev_values else None
            prev_avg_data_size_mb = prev_values[1] if prev_values else None
            self._apply_change_statistics_from_previous(
                aggregation=aggregation,
                prev_avg_size_mb=prev_avg_size_mb,
                prev_avg_data_size_mb=prev_avg_data_size_mb,
            )

            agg_any.calculated_at = time_utils.now()

        self._commit_with_partition_retry(start_date)

        log_debug(
            "实例数据库聚合数据提交完成",
            module=self._module,
            instance_id=instance.id,
            instance_name=instance.name,
            period_type=period_type,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            processed_databases=len(metrics),
        )

        return len(metrics)

    def _apply_change_statistics_from_previous(
        self,
        *,
        aggregation: DatabaseSizeAggregation,
        prev_avg_size_mb: float | None,
        prev_avg_data_size_mb: float | None,
    ) -> None:
        """根据上一周期平均值计算增量统计."""
        try:
            agg_any = cast(Any, aggregation)
            if prev_avg_size_mb is None:
                agg_any.size_change_mb = 0
                agg_any.size_change_percent = 0
                agg_any.data_size_change_mb = 0
                agg_any.data_size_change_percent = 0
                agg_any.log_size_change_mb = 0
                agg_any.log_size_change_percent = 0
                agg_any.trend_direction = "stable"
                agg_any.growth_rate = 0
                return

            current_avg_size = self._to_float(aggregation.avg_size_mb)
            size_change_mb = current_avg_size - prev_avg_size_mb
            agg_any.size_change_mb = int(size_change_mb)
            agg_any.size_change_percent = round(
                (size_change_mb / prev_avg_size_mb * 100) if prev_avg_size_mb > 0 else 0,
                2,
            )

            current_avg_data = self._to_float(aggregation.avg_data_size_mb)
            if prev_avg_data_size_mb is not None and aggregation.avg_data_size_mb is not None:
                data_size_change_mb = current_avg_data - prev_avg_data_size_mb
                agg_any.data_size_change_mb = int(data_size_change_mb)
                agg_any.data_size_change_percent = round(
                    (data_size_change_mb / prev_avg_data_size_mb * 100) if prev_avg_data_size_mb > 0 else 0,
                    2,
                )
            else:
                agg_any.data_size_change_mb = 0
                agg_any.data_size_change_percent = 0

            agg_any.log_size_change_mb = None
            agg_any.log_size_change_percent = None
            agg_any.growth_rate = agg_any.size_change_percent
        except AGGREGATION_RUNNER_EXCEPTIONS as exc:
            log_error(
                "计算数据库增量统计失败,使用默认值",
                module=self._module,
                exception=self._to_exception(exc),
            )
            agg_any = cast(Any, aggregation)
            agg_any.size_change_mb = 0
            agg_any.size_change_percent = 0
            agg_any.data_size_change_mb = 0
            agg_any.data_size_change_percent = 0
            agg_any.log_size_change_mb = 0
            agg_any.log_size_change_percent = 0
            agg_any.growth_rate = 0

    @staticmethod
    def _to_float(value: Any) -> float:
        """将数值或 Decimal 转换为 float,过滤 ColumnElement."""
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    @staticmethod
    def _to_int_value(value: Any) -> int:
        """将可能的列值转换为整数."""
        if isinstance(value, Decimal):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        return 0

    @staticmethod
    def _to_optional_int(value: Any) -> int | None:
        """将可能的列值转换为可选整数,用于处理 nullable 聚合列."""
        if value is None:
            return None
        return DatabaseAggregationRunner._to_int_value(value)

    @staticmethod
    def _to_exception(exc: BaseException) -> Exception:
        """规范化日志异常类型."""
        if isinstance(exc, Exception):
            return exc
        return Exception(str(exc))


__all__ = ["DatabaseAggregationRunner"]
