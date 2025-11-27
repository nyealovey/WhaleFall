"""聚合服务。

支持数据库级与实例级的周期聚合计算，包括日、周、月、季度四种周期类型。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List, Sequence

from app.errors import DatabaseError, NotFoundError, ValidationError
from app.constants import SyncStatus
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError
from app.models.instance import Instance
from app import db
from app.services.aggregation.calculator import PeriodCalculator
from app.services.aggregation.database_aggregation_runner import DatabaseAggregationRunner
from app.services.aggregation.instance_aggregation_runner import InstanceAggregationRunner
from app.services.aggregation.query_service import AggregationQueryService
from app.services.aggregation.results import AggregationStatus, InstanceSummary, PeriodSummary


MODULE = "aggregation_service"


class AggregationService:
    """聚合服务。

    提供数据库级和实例级的周期聚合计算功能，支持日、周、月、季度四种周期类型。

    Attributes:
        period_types: 支持的周期类型列表。
        period_calculator: 周期计算器。
        database_runner: 数据库级聚合执行器。
        instance_runner: 实例级聚合执行器。
        query_service: 聚合查询服务。

    Example:
        >>> service = AggregationService()
        >>> result = service.calculate_daily_aggregations()
        >>> result['status']
        'completed'
    """
    
    def __init__(self) -> None:
        """初始化聚合服务。"""
        self.period_types = ['daily', 'weekly', 'monthly', 'quarterly']
        self.period_calculator = PeriodCalculator()
        self.database_runner = DatabaseAggregationRunner(
            ensure_partition_for_date=self._ensure_partition_for_date,
            commit_with_partition_retry=self._commit_with_partition_retry,
            period_calculator=self.period_calculator,
            module=MODULE,
        )
        self.instance_runner = InstanceAggregationRunner(
            ensure_partition_for_date=self._ensure_partition_for_date,
            commit_with_partition_retry=self._commit_with_partition_retry,
            period_calculator=self.period_calculator,
            module=MODULE,
        )
        self.query_service = AggregationQueryService()
        self._database_methods = {
            "daily": self.calculate_daily_aggregations,
            "weekly": self.calculate_weekly_aggregations,
            "monthly": self.calculate_monthly_aggregations,
            "quarterly": self.calculate_quarterly_aggregations,
        }

    def _get_instance_or_raise(self, instance_id: int) -> Instance:
        """根据 ID 获取实例，若不存在则抛错。

        Args:
            instance_id: 实例 ID。

        Returns:
            Instance: 匹配到的实例对象。

        Raises:
            NotFoundError: 当实例不存在时抛出。
        """
        instance = Instance.query.get(instance_id)
        if not instance:
            raise NotFoundError(
                message="实例不存在",
                extra={"instance_id": instance_id},
            )
        return instance

    def _ensure_partition_for_date(self, target_date: date) -> None:
        """保留接口，当前环境无需分区预处理。

        Args:
            target_date: 聚合目标日期。

        Returns:
            None
        """
        return None

    def _commit_with_partition_retry(self, aggregation, start_date: date) -> None:
        """提交聚合记录，移除分区重试逻辑。

        Args:
            aggregation: 聚合结果对象，仅用于错误日志。
            start_date: 聚合周期开始日期。

        Returns:
            None

        Raises:
            DatabaseError: 当提交失败时抛出。
        """
        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            message = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            log_error(
                "提交聚合结果失败",
                module=MODULE,
                exception=exc,
                start_date=start_date.isoformat(),
            )
            raise DatabaseError(
                message="提交聚合结果失败",
                extra={"start_date": start_date.isoformat(), "error": message},
            ) from exc
        except Exception as exc:  # pragma: no cover - 防御性捕获
            db.session.rollback()
            log_error(
                "提交聚合结果出现未知异常",
                module=MODULE,
                exception=exc,
                start_date=start_date.isoformat(),
            )
            raise DatabaseError(
                message="提交聚合结果失败",
                extra={"start_date": start_date.isoformat(), "error": str(exc)},
            ) from exc

    def _period_range(self, period_type: str, *, use_current_period: bool) -> tuple[date, date]:
        """根据周期类型返回起止日期。"""
        return (
            self.period_calculator.get_current_period(period_type)
            if use_current_period
            else self.period_calculator.get_last_period(period_type)
        )

    def _aggregate_database_for_instance(
        self,
        instance_id: int,
        period_type: str,
        *,
        use_current_period: bool,
    ) -> Dict[str, Any]:
        """对指定实例执行数据库级聚合。

        Args:
            instance_id: 实例 ID。
            period_type: 周期类型。
            use_current_period: 是否使用当前周期（否则使用上一周期）。

        Returns:
            dict[str, Any]: 聚合摘要。
        """
        instance = self._get_instance_or_raise(instance_id)
        if not instance.is_active:
            return self._inactive_instance_summary(instance, period_type)

        start_date, end_date = self._period_range(period_type, use_current_period=use_current_period)
        summary = self.database_runner.aggregate_database_period(
            instance,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()

    def _aggregate_instance_for_instance(
        self,
        instance_id: int,
        period_type: str,
        *,
        use_current_period: bool,
    ) -> Dict[str, Any]:
        """对指定实例执行实例级聚合。"""
        instance = self._get_instance_or_raise(instance_id)
        start_date, end_date = self._period_range(period_type, use_current_period=use_current_period)
        summary = self.instance_runner.aggregate_instance_period(
            instance,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()

    def _inactive_instance_summary(self, instance: Instance, period_type: str) -> Dict[str, Any]:
        """构造实例未激活时的聚合摘要。

        Args:
            instance: 目标实例。
            period_type: 周期类型。

        Returns:
            dict[str, Any]: 标记为跳过的聚合摘要。
        """
        log_info(
            "实例未激活，跳过聚合",
            module=MODULE,
            instance_id=instance.id,
            instance_name=instance.name,
            period_type=period_type,
        )
        summary = InstanceSummary(
            instance_id=instance.id,
            instance_name=instance.name,
            period_type=period_type,
            message=f"实例 {instance.name} 未激活，跳过聚合",
        )
        return summary.to_dict()

    def _aggregate_period(
        self,
        *,
        runner,
        period_type: str,
        use_current_period: bool,
        log_message: str,
    ) -> Dict[str, Any]:
        """统一执行指定周期的聚合。

        Args:
            runner: 数据库或实例聚合执行器。
            period_type: 周期类型。
            use_current_period: 是否使用当前周期。
            log_message: 日志描述。

        Returns:
            dict[str, Any]: 聚合结果摘要。
        """
        log_info(log_message, module=MODULE)
        start_date, end_date = self._period_range(period_type, use_current_period=use_current_period)
        return runner.aggregate_period(period_type, start_date, end_date)

    def _normalize_periods(self, periods: Sequence[str] | None) -> list[str]:
        """标准化周期参数列表。

        Args:
            periods: 可能包含重复或未知周期的列表。

        Returns:
            list[str]: 过滤后的周期名称列表。
        """
        if not periods:
            return list(self.period_types)

        seen: set[str] = set()
        normalized: list[str] = []
        for item in periods:
            key = (item or "").strip().lower()
            if key in self.period_types and key not in seen:
                normalized.append(key)
                seen.add(key)
        return normalized

    def aggregate_database_periods(self, periods: Sequence[str] | None = None) -> dict[str, Dict[str, Any]]:
        """计算数据库级聚合结果。

        Args:
            periods: 指定的周期名称列表，如 day/week/month；为空时默认全部。

        Returns:
            dict[str, Dict[str, Any]]: key 为周期名称，value 为聚合结果字典。
        """

        normalized = self._normalize_periods(periods)
        results: dict[str, Dict[str, Any]] = {}

        for period in normalized:
            method = self._database_methods.get(period)
            if method is None:
                continue
            try:
                period_result = method()
            except Exception as exc:  # pragma: no cover - 防御性日志
                log_error(
                    "数据库级聚合执行失败",
                    module=MODULE,
                    period_type=period,
                    exception=exc,
                )
                period_result = {
                    "status": AggregationStatus.FAILED.value,
                    "error": str(exc),
                    "errors": [str(exc)],
                    "period_type": period,
                }
            period_result.setdefault("period_type", period)
            results[period] = period_result

        return results
    
    def calculate_all_aggregations(self) -> Dict[str, Any]:
        """
        计算所有实例的统计聚合数据
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算所有实例的统计聚合数据", module=MODULE)

        period_results = {
            "daily": self.calculate_daily_aggregations(),
            "weekly": self.calculate_weekly_aggregations(),
            "monthly": self.calculate_monthly_aggregations(),
            "quarterly": self.calculate_quarterly_aggregations(),
        }

        instance_results = {
            "daily": self.calculate_daily_instance_aggregations(),
            "weekly": self.calculate_weekly_instance_aggregations(),
            "monthly": self.calculate_monthly_instance_aggregations(),
            "quarterly": self.calculate_quarterly_instance_aggregations(),
        }

        total_processed = sum(r.get("processed_instances", 0) for r in period_results.values())
        total_failures = sum(r.get("failed_instances", 0) for r in period_results.values())
        total_records = sum(r.get("total_records", 0) for r in period_results.values())

        total_instance_processed = sum(r.get("processed_instances", 0) for r in instance_results.values())
        total_instance_failures = sum(r.get("failed_instances", 0) for r in instance_results.values())
        total_instance_records = sum(r.get("total_records", 0) for r in instance_results.values())

        failed_periods = [
            period for period, result in period_results.items() if result.get("status") == AggregationStatus.FAILED.value
        ]
        failed_instance_periods = [
            period
            for period, result in instance_results.items()
            if result.get("status") == AggregationStatus.FAILED.value
        ]

        overall_status = (
            AggregationStatus.FAILED
            if failed_periods or failed_instance_periods
            else AggregationStatus.COMPLETED
        )

        message = (
            "统计聚合执行完成"
            if overall_status is AggregationStatus.COMPLETED
            else "统计聚合执行完成，但存在失败的周期"
        )

        log_info(
            "统计聚合计算完成",
            module=MODULE,
            status=overall_status.value,
            total_processed=total_processed,
            total_failures=total_failures,
            total_records=total_records,
            instance_processed=total_instance_processed,
            instance_failures=total_instance_failures,
            instance_records=total_instance_records,
        )

        return {
            "status": overall_status.value,
            "message": message,
            "period_summaries": period_results,
            "instance_summaries": instance_results,
            "metrics": {
                "database": {
                    "processed_instances": total_processed,
                    "failed_instances": total_failures,
                    "total_records": total_records,
                },
                "instance": {
                    "processed_instances": total_instance_processed,
                    "failed_instances": total_instance_failures,
                    "total_records": total_instance_records,
                },
            },
        }
    
    def calculate_daily_aggregations(self) -> Dict[str, Any]:
        """计算每日统计聚合（处理今日数据）。

        Returns:
            dict[str, Any]: 聚合执行结果。
        """
        return self._aggregate_period(
            runner=self.database_runner,
            period_type="daily",
            use_current_period=True,
            log_message="开始计算每日统计聚合",
        )

    def aggregate_current_period(
        self,
        period_type: str = "daily",
        *,
        scope: str = "all",
        progress_callbacks: dict[str, dict[str, Callable[..., None]]] | None = None,
    ) -> Dict[str, Any]:
        """计算当前周期（含今日）统计聚合。

        Args:
            period_type: 周期类型（daily/weekly/...）。
            scope: 运行范围（database/instance/all）。
            progress_callbacks: 可选回调字典。

        Returns:
            dict[str, Any]: 包含数据库与实例聚合摘要的结果。
        """
        normalized = (period_type or "").lower()
        if normalized not in self.period_types:
            raise ValidationError(
                message="不支持的聚合周期",
                extra={"period_type": period_type},
            )
        normalized_scope = (scope or "all").lower()
        allowed_scopes = {"all", "instance", "database"}
        if normalized_scope not in allowed_scopes:
            raise ValidationError(
                message="不支持的聚合范围",
                extra={"scope": scope},
            )

        run_database = normalized_scope in {"all", "database"}
        run_instance = normalized_scope in {"all", "instance"}

        if not (run_database or run_instance):
            raise ValidationError(
                message="聚合范围为空",
                extra={"scope": scope},
            )

        start_date, end_date = self.period_calculator.get_current_period(normalized)
        log_info(
            "开始计算当前周期统计聚合",
            module=MODULE,
            period_type=normalized,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            scope=normalized_scope,
        )
        callbacks = progress_callbacks or {}
        db_callbacks = callbacks.get("database", {})
        instance_callbacks = callbacks.get("instance", {})

        database_result: dict[str, Any] | None = None
        if run_database:
            database_result = self.database_runner.aggregate_period(
                normalized,
                start_date,
                end_date,
                on_instance_start=db_callbacks.get("on_start"),
                on_instance_complete=db_callbacks.get("on_complete"),
                on_instance_error=db_callbacks.get("on_error"),
            )

        instance_result: dict[str, Any] | None = None
        if run_instance:
            instance_result = self.instance_runner.aggregate_period(
                normalized,
                start_date,
                end_date,
                on_instance_start=instance_callbacks.get("on_start"),
                on_instance_complete=instance_callbacks.get("on_complete"),
                on_instance_error=instance_callbacks.get("on_error"),
            )

        summaries: list[dict[str, Any]] = []
        if database_result:
            summaries.append(database_result)
        if instance_result:
            summaries.append(instance_result)

        statuses = {
            (summary.get("status") or AggregationStatus.FAILED.value).lower()
            for summary in summaries
        }

        if not statuses:
            overall_status = AggregationStatus.SKIPPED
            message = "未执行任何聚合任务"
        elif AggregationStatus.FAILED.value in statuses:
            overall_status = AggregationStatus.FAILED
            message = "当前周期聚合完成，但存在失败的子任务"
        elif statuses == {AggregationStatus.SKIPPED.value}:
            overall_status = AggregationStatus.SKIPPED
            message = "当前周期没有可处理的数据"
        else:
            overall_status = AggregationStatus.COMPLETED
            message = "当前周期聚合完成"

        return {
            "status": overall_status.value,
            "message": message,
            "period_type": normalized,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "scope": normalized_scope,
            "database_summary": database_result,
            "instance_summary": instance_result,
        }

    def calculate_weekly_aggregations(self) -> Dict[str, Any]:
        """计算每周统计聚合。

        Returns:
            dict[str, Any]: 聚合执行结果。
        """
        return self._aggregate_period(
            runner=self.database_runner,
            period_type="weekly",
            use_current_period=False,
            log_message="开始计算每周统计聚合",
        )
    
    def calculate_monthly_aggregations(self) -> Dict[str, Any]:
        """计算每月统计聚合。

        Returns:
            dict[str, Any]: 聚合执行结果。
        """
        return self._aggregate_period(
            runner=self.database_runner,
            period_type="monthly",
            use_current_period=False,
            log_message="开始计算每月统计聚合",
        )
    
    def calculate_quarterly_aggregations(self) -> Dict[str, Any]:
        """计算每季度统计聚合。

        Returns:
            dict[str, Any]: 聚合执行结果。
        """
        return self._aggregate_period(
            runner=self.database_runner,
            period_type="quarterly",
            use_current_period=False,
            log_message="开始计算每季度统计聚合",
        )

    def calculate_daily_database_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算当日数据库聚合。

        Args:
            instance_id: 实例 ID。

        Returns:
            dict[str, Any]: 聚合摘要。
        """
        return self._aggregate_database_for_instance(
            instance_id,
            "daily",
            use_current_period=True,
        )

    def calculate_weekly_database_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算周数据库聚合。

        Args:
            instance_id: 实例 ID。

        Returns:
            dict[str, Any]: 聚合摘要。
        """
        return self._aggregate_database_for_instance(
            instance_id,
            "weekly",
            use_current_period=False,
        )

    def calculate_monthly_database_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算月数据库聚合。

        Args:
            instance_id: 实例 ID。

        Returns:
            dict[str, Any]: 聚合摘要。
        """
        return self._aggregate_database_for_instance(
            instance_id,
            "monthly",
            use_current_period=False,
        )

    def calculate_quarterly_database_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算季度数据库聚合。

        Args:
            instance_id: 实例 ID。

        Returns:
            dict[str, Any]: 聚合摘要。
        """
        return self._aggregate_database_for_instance(
            instance_id,
            "quarterly",
            use_current_period=False,
        )

    def calculate_daily_instance_aggregations(self) -> Dict[str, Any]:
        """计算每日实例统计聚合。

        Returns:
            dict[str, Any]: 聚合执行结果。
        """
        return self._aggregate_period(
            runner=self.instance_runner,
            period_type="daily",
            use_current_period=True,
            log_message="开始计算每日实例统计聚合",
        )
    
    def calculate_weekly_instance_aggregations(self) -> Dict[str, Any]:
        """计算每周实例统计聚合。

        Returns:
            dict[str, Any]: 聚合执行结果。
        """
        return self._aggregate_period(
            runner=self.instance_runner,
            period_type="weekly",
            use_current_period=False,
            log_message="开始计算每周实例统计聚合",
        )
    
    def calculate_monthly_instance_aggregations(self) -> Dict[str, Any]:
        """计算每月实例统计聚合。

        Returns:
            dict[str, Any]: 聚合执行结果。
        """
        return self._aggregate_period(
            runner=self.instance_runner,
            period_type="monthly",
            use_current_period=False,
            log_message="开始计算每月实例统计聚合",
        )
    
    def calculate_quarterly_instance_aggregations(self) -> Dict[str, Any]:
        """计算每季度实例统计聚合。

        Returns:
            dict[str, Any]: 聚合执行结果。
        """
        return self._aggregate_period(
            runner=self.instance_runner,
            period_type="quarterly",
            use_current_period=False,
            log_message="开始计算每季度实例统计聚合",
        )

    def calculate_instance_aggregations(
        self,
        instance_id: int,
        periods: Sequence[str] | None = None,
    ) -> Dict[str, Any]:
        """计算指定实例的多周期聚合。

        Args:
            instance_id: 实例 ID。
            periods: 指定需要计算的周期列表。

        Returns:
            dict[str, Any]: 各周期的聚合摘要。
        """
        instance = Instance.query.get(instance_id)
        if not instance:
            raise NotFoundError(
                message="实例不存在",
                extra={"instance_id": instance_id},
            )

        period_funcs = {
            "daily": self.calculate_daily_aggregations_for_instance,
            "weekly": self.calculate_weekly_aggregations_for_instance,
            "monthly": self.calculate_monthly_aggregations_for_instance,
            "quarterly": self.calculate_quarterly_aggregations_for_instance,
        }
        requested = self._normalize_periods(periods)
        if not requested:
            requested = list(period_funcs.keys())

        period_results: dict[str, dict[str, Any]] = {}
        failed_periods: set[str] = set()
        processed_periods = 0
        skipped_periods = 0

        for period in requested:
            func = period_funcs[period]
            try:
                result = func(instance_id)
            except Exception as exc:  # pragma: no cover - 防御性日志
                log_error(
                    "实例周期聚合执行失败",
                    module=MODULE,
                    exception=exc,
                    instance_id=instance_id,
                    instance_name=instance.name,
                    period_type=period,
                )
                summary = InstanceSummary(
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period,
                    errors=[str(exc)],
                    message=f"{period} 聚合失败: {exc}",
                ).to_dict()
                failed_periods.add(period)
            else:
                summary = result

            period_results[period] = summary
            status = summary.get("status")
            if status == AggregationStatus.COMPLETED.value:
                processed_periods += 1
            elif status == AggregationStatus.SKIPPED.value:
                skipped_periods += 1
            elif status == AggregationStatus.FAILED.value:
                failed_periods.add(period)

        if failed_periods:
            overall_status = AggregationStatus.FAILED
            message = f"实例聚合完成，但以下周期失败: {', '.join(sorted(failed_periods))}"
        elif processed_periods == 0:
            overall_status = AggregationStatus.SKIPPED
            message = "实例聚合没有可处理的数据"
        else:
            overall_status = AggregationStatus.COMPLETED
            message = "实例多周期聚合完成"

        return {
            "status": overall_status.value,
            "instance_id": instance.id,
            "instance_name": instance.name,
            "message": message,
            "periods": period_results,
            "metrics": {
                "processed_periods": processed_periods,
                "skipped_periods": skipped_periods,
            },
        }

    def calculate_daily_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算日统计聚合。

        Args:
            instance_id: 实例 ID。

        Returns:
            dict[str, Any]: 聚合摘要。
        """
        return self._aggregate_instance_for_instance(
            instance_id,
            "daily",
            use_current_period=True,
        )

    def calculate_weekly_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算周统计聚合。"""
        return self._aggregate_instance_for_instance(
            instance_id,
            "weekly",
            use_current_period=False,
        )

    def calculate_monthly_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算月统计聚合。

        Args:
            instance_id: 实例 ID。

        Returns:
            dict[str, Any]: 聚合摘要。
        """
        return self._aggregate_instance_for_instance(
            instance_id,
            "monthly",
            use_current_period=False,
        )

    def calculate_quarterly_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算季度统计聚合。"""
        return self._aggregate_instance_for_instance(
            instance_id,
            "quarterly",
            use_current_period=False,
        )

    def calculate_period_aggregations(self, period_type: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """计算指定时间范围的聚合数据。

        Args:
            period_type: 周期类型。
            start_date: 起始日期。
            end_date: 结束日期。

        Returns:
            dict[str, Any]: 聚合执行结果。
        """
        normalized = (period_type or "").lower()
        if normalized not in self.period_types:
            raise ValidationError(
                message="不支持的聚合周期",
                extra={"period_type": period_type},
            )
        if start_date > end_date:
            raise ValidationError(
                message="开始日期不能晚于结束日期",
                extra={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            )

        log_info(
            "执行指定时间范围的统计聚合",
            module=MODULE,
            period_type=normalized,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        return self.database_runner.aggregate_period(normalized, start_date, end_date)
    
    def get_aggregations(
        self,
        instance_id: int,
        period_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
        database_name: str | None = None,
    ) -> List[Dict[str, Any]]:
        """获取数据库级聚合数据。

        Args:
            instance_id: 实例 ID。
            period_type: 周期类型。
            start_date: 起始日期，可选。
            end_date: 结束日期，可选。
            database_name: 数据库名称筛选，可选。

        Returns:
            list[dict[str, Any]]: 聚合结果列表。
        """
        return self.query_service.get_database_aggregations(
            instance_id=instance_id,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            database_name=database_name,
        )

    def get_instance_aggregations(
        self,
        instance_id: int,
        period_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> List[Dict[str, Any]]:
        """获取实例整体聚合数据。

        Args:
            instance_id: 实例 ID。
            period_type: 周期类型。
            start_date: 起始日期，可选。
            end_date: 结束日期，可选。

        Returns:
            list[dict[str, Any]]: 聚合结果列表。
        """
        return self.query_service.get_instance_aggregations(
            instance_id=instance_id,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
