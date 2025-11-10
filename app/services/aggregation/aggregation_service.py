"""
聚合服务
支持数据库级与实例级的周期聚合计算
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List, Optional, Sequence

from app.errors import DatabaseError, NotFoundError, ValidationError
from app.constants import SyncStatus
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance import Instance
from app import db
from app.services.aggregation.calculator import PeriodCalculator
from app.services.aggregation.database_aggregation_runner import DatabaseAggregationRunner
from app.services.aggregation.instance_aggregation_runner import InstanceAggregationRunner
from app.services.aggregation.results import AggregationStatus, InstanceSummary, PeriodSummary


MODULE = "aggregation_service"


class AggregationService:
    """聚合服务"""
    
    def __init__(self):
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

    def _get_instance_or_raise(self, instance_id: int) -> Instance:
        instance = Instance.query.get(instance_id)
        if not instance:
            raise NotFoundError(
                message="实例不存在",
                extra={"instance_id": instance_id},
            )
        return instance

    def _ensure_partition_for_date(self, target_date: date) -> None:
        """保留接口，当前环境无需分区预处理。"""
        return None

    def _commit_with_partition_retry(self, aggregation, start_date: date) -> None:
        """提交聚合记录，移除分区重试逻辑。"""
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
        """
        计算每日统计聚合（定时任务用，处理今天的数据）
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每日统计聚合", module=MODULE)
        
        # 与容量同步任务保持一致：使用中国时区的今日数据
        start_date, end_date = self.period_calculator.get_current_period("daily")
        return self.database_runner.aggregate_period("daily", start_date, end_date)

    def aggregate_current_period(
        self,
        period_type: str = "daily",
        *,
        scope: str = "all",
        progress_callbacks: dict[str, dict[str, Callable[..., None]]] | None = None,
    ) -> Dict[str, Any]:
        """计算当前周期（含今日）统计聚合"""
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
        """
        计算每周统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每周统计聚合", module=MODULE)
        
        # 使用完整自然周（上周周一至上周周日）
        start_date, end_date = self.period_calculator.get_last_period("weekly")
        return self.database_runner.aggregate_period("weekly", start_date, end_date)
    
    def calculate_monthly_aggregations(self) -> Dict[str, Any]:
        """
        计算每月统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每月统计聚合", module=MODULE)
        
        # 获取上个月的数据（使用中国时区）
        start_date, end_date = self.period_calculator.get_last_period("monthly")
        return self.database_runner.aggregate_period("monthly", start_date, end_date)
    
    def calculate_quarterly_aggregations(self) -> Dict[str, Any]:
        """
        计算每季度统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每季度统计聚合", module=MODULE)
        
        # 获取上个季度的数据（使用中国时区）
        start_date, end_date = self.period_calculator.get_last_period("quarterly")
        return self.database_runner.aggregate_period("quarterly", start_date, end_date)

    def calculate_daily_database_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """
        为指定实例计算当日的数据库级聚合
        单实例容量同步完成后调用，避免等待全量调度任务
        """
        instance = self._get_instance_or_raise(instance_id)
        if not instance.is_active:
            log_info(
                "实例未激活，跳过日数据库聚合",
                module=MODULE,
                instance_id=instance.id,
                instance_name=instance.name,
            )
            summary = InstanceSummary(
                instance_id=instance.id,
                instance_name=instance.name,
                period_type="daily",
                message=f"实例 {instance.name} 未激活，跳过聚合",
            )
            return summary.to_dict()

        start_date, end_date = self.period_calculator.get_current_period("daily")
        summary = self.database_runner.aggregate_database_period(
            instance,
            period_type="daily",
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()

    def calculate_weekly_database_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算周数据库级聚合"""
        instance = self._get_instance_or_raise(instance_id)
        if not instance.is_active:
            log_info(
                "实例未激活，跳过周数据库聚合",
                module=MODULE,
                instance_id=instance.id,
                instance_name=instance.name,
            )
            summary = InstanceSummary(
                instance_id=instance.id,
                instance_name=instance.name,
                period_type="weekly",
                message=f"实例 {instance.name} 未激活，跳过聚合",
            )
            return summary.to_dict()

        start_date, end_date = self.period_calculator.get_last_period("weekly")
        summary = self.database_runner.aggregate_database_period(
            instance,
            period_type="weekly",
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()

    def calculate_monthly_database_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算月数据库级聚合"""
        instance = self._get_instance_or_raise(instance_id)
        if not instance.is_active:
            log_info(
                "实例未激活，跳过月数据库聚合",
                module=MODULE,
                instance_id=instance.id,
                instance_name=instance.name,
            )
            summary = InstanceSummary(
                instance_id=instance.id,
                instance_name=instance.name,
                period_type="monthly",
                message=f"实例 {instance.name} 未激活，跳过聚合",
            )
            return summary.to_dict()

        start_date, end_date = self.period_calculator.get_last_period("monthly")
        summary = self.database_runner.aggregate_database_period(
            instance,
            period_type="monthly",
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()

    def calculate_quarterly_database_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算季度数据库级聚合"""
        instance = self._get_instance_or_raise(instance_id)
        if not instance.is_active:
            log_info(
                "实例未激活，跳过季度数据库聚合",
                module=MODULE,
                instance_id=instance.id,
                instance_name=instance.name,
            )
            summary = InstanceSummary(
                instance_id=instance.id,
                instance_name=instance.name,
                period_type="quarterly",
                message=f"实例 {instance.name} 未激活，跳过聚合",
            )
            return summary.to_dict()

        start_date, end_date = self.period_calculator.get_last_period("quarterly")
        summary = self.database_runner.aggregate_database_period(
            instance,
            period_type="quarterly",
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()

    def calculate_daily_instance_aggregations(self) -> Dict[str, Any]:
        """
        计算每日实例统计聚合（定时任务用，处理今天的数据）
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每日实例统计聚合", module=MODULE)
        
        # 获取今天的数据（与容量同步任务保持一致，使用中国时区）
        start_date, end_date = self.period_calculator.get_current_period("daily")
        return self.instance_runner.aggregate_period("daily", start_date, end_date)
    
    def calculate_weekly_instance_aggregations(self) -> Dict[str, Any]:
        """
        计算每周实例统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每周实例统计聚合", module=MODULE)
        
        # 获取上周完整自然周的数据（使用中国时区）
        start_date, end_date = self.period_calculator.get_last_period("weekly")
        return self.instance_runner.aggregate_period("weekly", start_date, end_date)
    
    def calculate_monthly_instance_aggregations(self) -> Dict[str, Any]:
        """
        计算每月实例统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每月实例统计聚合", module=MODULE)
        
        # 获取上个月的数据（使用中国时区）
        start_date, end_date = self.period_calculator.get_last_period("monthly")
        return self.instance_runner.aggregate_period("monthly", start_date, end_date)
    
    def calculate_quarterly_instance_aggregations(self) -> Dict[str, Any]:
        """
        计算每季度实例统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每季度实例统计聚合", module=MODULE)
        
        # 获取上个季度的数据（使用中国时区）
        start_date, end_date = self.period_calculator.get_last_period("quarterly")
        return self.instance_runner.aggregate_period("quarterly", start_date, end_date)

    def calculate_instance_aggregations(
        self,
        instance_id: int,
        periods: Sequence[str] | None = None,
    ) -> Dict[str, Any]:
        """计算指定实例的多周期聚合"""
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
        requested: List[str] = []
        if periods:
            seen: set[str] = set()
            for period in periods:
                normalized = (period or "").strip().lower()
                if normalized in period_funcs and normalized not in seen:
                    requested.append(normalized)
                    seen.add(normalized)
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
        """为指定实例计算日统计聚合"""
        instance = self._get_instance_or_raise(instance_id)
        start_date, end_date = self.period_calculator.get_current_period("daily")
        summary = self.instance_runner.aggregate_instance_period(
            instance,
            period_type="daily",
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()

    def calculate_weekly_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算周统计聚合"""
        instance = self._get_instance_or_raise(instance_id)
        start_date, end_date = self.period_calculator.get_last_period("weekly")
        summary = self.instance_runner.aggregate_instance_period(
            instance,
            period_type="weekly",
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()

    def calculate_monthly_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算月统计聚合"""
        instance = self._get_instance_or_raise(instance_id)
        start_date, end_date = self.period_calculator.get_last_period("monthly")
        summary = self.instance_runner.aggregate_instance_period(
            instance,
            period_type="monthly",
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()

    def calculate_quarterly_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算季度统计聚合"""
        instance = self._get_instance_or_raise(instance_id)
        start_date, end_date = self.period_calculator.get_last_period("quarterly")
        summary = self.instance_runner.aggregate_instance_period(
            instance,
            period_type="quarterly",
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()

    def calculate_period_aggregations(self, period_type: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """计算指定周期的聚合数据"""
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
    
    def get_aggregations(self, instance_id: int, period_type: str, 
                        start_date: date = None, end_date: date = None,
                        database_name: str = None) -> List[Dict[str, Any]]:
        """
        获取统计聚合数据
        
        Args:
            instance_id: 实例ID
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
            database_name: 数据库名称
            
        Returns:
            List[Dict[str, Any]]: 聚合数据列表
        """
        query = DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.instance_id == instance_id,
            DatabaseSizeAggregation.period_type == period_type
        )
        
        if start_date:
            query = query.filter(DatabaseSizeAggregation.period_start >= start_date)
        if end_date:
            query = query.filter(DatabaseSizeAggregation.period_end <= end_date)
        if database_name:
            query = query.filter(DatabaseSizeAggregation.database_name == database_name)
        
        aggregations = query.order_by(DatabaseSizeAggregation.period_start.desc()).all()
        
        return [self._format_aggregation(agg) for agg in aggregations]
    
    def get_instance_aggregations(self, instance_id: int, period_type: str, 
                                start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
        """
        获取实例统计聚合数据
        
        Args:
            instance_id: 实例ID
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[Dict[str, Any]]: 实例聚合数据列表
        """
        query = InstanceSizeAggregation.query.filter(
            InstanceSizeAggregation.instance_id == instance_id,
            InstanceSizeAggregation.period_type == period_type
        )
        
        if start_date:
            query = query.filter(InstanceSizeAggregation.period_start >= start_date)
        if end_date:
            query = query.filter(InstanceSizeAggregation.period_end <= end_date)
        
        aggregations = query.order_by(InstanceSizeAggregation.period_start.desc()).all()
        
        return [self._format_instance_aggregation(agg) for agg in aggregations]
    
    def _format_aggregation(self, aggregation: DatabaseSizeAggregation) -> Dict[str, Any]:
        """
        格式化聚合数据
        
        Args:
            aggregation: 聚合数据对象
            
        Returns:
            Dict[str, Any]: 格式化后的数据
        """
        return {
            'id': aggregation.id,
            'instance_id': aggregation.instance_id,
            'database_name': aggregation.database_name,
            'period_type': aggregation.period_type,
            'period_start': aggregation.period_start.isoformat() if aggregation.period_start else None,
            'period_end': aggregation.period_end.isoformat() if aggregation.period_end else None,
            'statistics': {
                'avg_size_mb': aggregation.avg_size_mb,
                'max_size_mb': aggregation.max_size_mb,
                'min_size_mb': aggregation.min_size_mb,
                'data_count': aggregation.data_count,
                'avg_data_size_mb': aggregation.avg_data_size_mb,
                'max_data_size_mb': aggregation.max_data_size_mb,
                'min_data_size_mb': aggregation.min_data_size_mb,
                'avg_log_size_mb': aggregation.avg_log_size_mb,
                'max_log_size_mb': aggregation.max_log_size_mb,
                'min_log_size_mb': aggregation.min_log_size_mb
            },
            'changes': {
                'size_change_mb': aggregation.size_change_mb,
                'size_change_percent': float(aggregation.size_change_percent) if aggregation.size_change_percent else 0,
                'data_size_change_mb': aggregation.data_size_change_mb,
                'data_size_change_percent': float(aggregation.data_size_change_percent) if aggregation.data_size_change_percent else None,
                'log_size_change_mb': aggregation.log_size_change_mb,
                'log_size_change_percent': float(aggregation.log_size_change_percent) if aggregation.log_size_change_percent else None,
                'growth_rate': float(aggregation.growth_rate) if aggregation.growth_rate else 0
            },
            'calculated_at': aggregation.calculated_at.isoformat() if aggregation.calculated_at else None,
            'created_at': aggregation.created_at.isoformat() if aggregation.created_at else None
        }
    
    def _format_instance_aggregation(self, aggregation: InstanceSizeAggregation) -> Dict[str, Any]:
        """
        格式化实例聚合数据
        
        Args:
            aggregation: 实例聚合数据对象
            
        Returns:
            Dict[str, Any]: 格式化后的数据
        """
        return {
            'id': aggregation.id,
            'instance_id': aggregation.instance_id,
            'period_type': aggregation.period_type,
            'period_start': aggregation.period_start.isoformat() if aggregation.period_start else None,
            'period_end': aggregation.period_end.isoformat() if aggregation.period_end else None,
            'statistics': {
                'total_size_mb': aggregation.total_size_mb,
                'avg_size_mb': aggregation.avg_size_mb,
                'max_size_mb': aggregation.max_size_mb,
                'min_size_mb': aggregation.min_size_mb,
                'data_count': aggregation.data_count,
                'database_count': aggregation.database_count,
                'avg_database_count': float(aggregation.avg_database_count) if aggregation.avg_database_count else None,
                'max_database_count': aggregation.max_database_count,
                'min_database_count': aggregation.min_database_count
            },
            'changes': {
                'total_size_change_mb': aggregation.total_size_change_mb,
                'total_size_change_percent': float(aggregation.total_size_change_percent) if aggregation.total_size_change_percent else 0,
                'database_count_change': aggregation.database_count_change,
                'database_count_change_percent': float(aggregation.database_count_change_percent) if aggregation.database_count_change_percent else None,
                'growth_rate': float(aggregation.growth_rate) if aggregation.growth_rate else 0,
                'trend_direction': aggregation.trend_direction
            },
            'calculated_at': aggregation.calculated_at.isoformat() if aggregation.calculated_at else None,
            'created_at': aggregation.created_at.isoformat() if aggregation.created_at else None
        }
