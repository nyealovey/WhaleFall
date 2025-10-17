"""
数据库大小统计聚合服务
支持每周、每月、每季度的统计聚合计算
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.errors import DatabaseError, NotFoundError, ValidationError
from app.utils.structlog_config import log_debug, log_error, log_info, log_warning
from app.utils.time_utils import time_utils
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError
from app.models.database_size_stat import DatabaseSizeStat
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.models.instance import Instance
from app import db
from app.services.partition_management_service import PartitionManagementService


MODULE = "database_size_aggregation_service"


class AggregationStatus(str, Enum):
    """聚合任务执行状态"""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(slots=True)
class PeriodSummary:
    """按周期聚合的汇总结果"""

    period_type: str
    start_date: date
    end_date: date
    processed_instances: int = 0
    total_records: int = 0
    failed_instances: int = 0
    skipped_instances: int = 0
    errors: list[str] = field(default_factory=list)
    message: str | None = None

    @property
    def status(self) -> AggregationStatus:
        if self.failed_instances > 0:
            return AggregationStatus.FAILED
        if self.processed_instances == 0:
            return AggregationStatus.SKIPPED
        return AggregationStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "period_type": self.period_type,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "processed_instances": self.processed_instances,
            "total_records": self.total_records,
            "failed_instances": self.failed_instances,
            "skipped_instances": self.skipped_instances,
            "errors": self.errors,
            "message": self.message,
        }


@dataclass(slots=True)
class InstanceSummary:
    """单个实例的聚合情况"""

    instance_id: int
    instance_name: str | None
    period_type: str
    processed_records: int = 0
    errors: list[str] = field(default_factory=list)
    message: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> AggregationStatus:
        if self.errors:
            return AggregationStatus.FAILED
        if self.processed_records == 0:
            return AggregationStatus.SKIPPED
        return AggregationStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status.value,
            "instance_id": self.instance_id,
            "instance_name": self.instance_name,
            "period_type": self.period_type,
            "processed_records": self.processed_records,
        }
        if self.errors:
            payload["errors"] = list(self.errors)
        if self.message:
            payload["message"] = self.message
        if self.extra:
            payload.update(self.extra)
        return payload


class DatabaseSizeAggregationService:
    """数据库大小统计聚合服务"""
    
    def __init__(self):
        self.period_types = ['daily', 'weekly', 'monthly', 'quarterly']
        self._partition_cache: Set[Tuple[int, int]] = set()

    def _ensure_partition_for_date(self, target_date: date) -> None:
        """
        确保目标日期所在月份的分区已创建
        """
        bind = db.session.get_bind()
        if not bind or bind.dialect.name != "postgresql":
            return

        month_key = (target_date.year, target_date.month)
        if month_key in self._partition_cache:
            log_debug(
                "聚合分区已存在，使用缓存",
                module=MODULE,
                target_month=time_utils.format_china_time(target_date, "%Y-%m"),
            )
            return

        try:
            partition_service = PartitionManagementService()
            partition_service.create_partition(target_date)
            self._partition_cache.add(month_key)
            log_info(
                "聚合分区已确保存在",
                module=MODULE,
                target_month=time_utils.format_china_time(target_date, "%Y-%m"),
            )
        except DatabaseError as exc:  # pragma: no cover - 分区创建失败只记录告警
            log_warning(
                "创建聚合分区失败，将在后续重试",
                module=MODULE,
                target_month=time_utils.format_china_time(target_date, "%Y-%m"),
                error=exc.message,
            )
        except Exception as exc:  # pragma: no cover - 记录警告不影响主流程
            log_warning(
                "创建聚合分区出现未知异常，将在后续重试",
                module=MODULE,
                target_month=time_utils.format_china_time(target_date, "%Y-%m"),
                exception=exc,
            )

    def _commit_with_partition_retry(self, aggregation, start_date: date) -> None:
        """
        提交聚合记录，如因缺少分区失败则尝试创建分区后重试
        """
        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            message = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            if "no partition of relation" not in message:
                log_error(
                    "提交聚合结果失败",
                    module=MODULE,
                    exception=exc,
                    start_date=start_date.isoformat(),
                )
                raise DatabaseError(
                    message="提交聚合结果失败",
                    extra={"start_date": start_date.isoformat()},
                ) from exc

            log_warning(
                "聚合提交缺少分区，尝试自动创建",
                module=MODULE,
                start_date=start_date.isoformat(),
            )
            self._ensure_partition_for_date(start_date)

            db.session.merge(aggregation)
            try:
                db.session.commit()
            except Exception as retry_exc:  # pragma: no cover - 防御性捕获
                db.session.rollback()
                log_error(
                    "分区创建后提交聚合结果仍失败",
                    module=MODULE,
                    exception=retry_exc,
                    start_date=start_date.isoformat(),
                )
                raise DatabaseError(
                    message="聚合结果提交失败",
                    extra={"start_date": start_date.isoformat()},
                ) from retry_exc
    
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
        target_date = time_utils.now_china().date()
        
        start_date = target_date
        end_date = target_date
        
        return self._calculate_aggregations('daily', start_date, end_date)

    def calculate_daily_database_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """
        为指定实例计算当日的数据库级聚合
        单实例容量同步完成后调用，避免等待全量调度任务
        """
        instance = Instance.query.get(instance_id)
        if not instance:
            raise NotFoundError(
                message="实例不存在",
                extra={"instance_id": instance_id},
            )
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

        target_date = time_utils.now_china().date()
        stats = DatabaseSizeStat.query.filter(
            DatabaseSizeStat.instance_id == instance_id,
            DatabaseSizeStat.collected_date == target_date,
        ).all()

        if not stats:
            log_warning(
                "实例在目标日期没有数据库容量数据，跳过聚合",
                module=MODULE,
                instance_id=instance.id,
                instance_name=instance.name,
                period_type="daily",
                date=target_date.isoformat(),
            )
            summary = InstanceSummary(
                instance_id=instance.id,
                instance_name=instance.name,
                period_type="daily",
                message=f"实例 {instance.name} 在 {target_date} 没有数据库容量数据，跳过聚合",
            )
            return summary.to_dict()

        db_groups: Dict[str, List[DatabaseSizeStat]] = {}
        for stat in stats:
            db_groups.setdefault(stat.database_name, []).append(stat)

        processed = 0
        for db_name, db_stats in db_groups.items():
            self._calculate_database_aggregation(
                instance_id,
                db_name,
                "daily",
                target_date,
                target_date,
                db_stats,
            )
            processed += 1

        summary = InstanceSummary(
            instance_id=instance.id,
            instance_name=instance.name,
            period_type="daily",
            processed_records=processed,
            message=f"实例 {instance.name} 的数据库聚合已更新 ({processed} 个数据库)",
        )
        log_info(
            "实例日数据库聚合已更新",
            module=MODULE,
            instance_id=instance.id,
            instance_name=instance.name,
            processed_databases=processed,
        )
        return summary.to_dict()
    
    def calculate_today_aggregations(self) -> Dict[str, Any]:
        """
        计算今日统计聚合（手动触发用，处理今天的数据）
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算今日统计聚合", module=MODULE)
        
        # 获取今天的数据进行聚合（使用中国时区）
        end_date = time_utils.now_china().date()
        start_date = end_date  # 同一天，处理今天的数据
        
        return self._calculate_aggregations('daily', start_date, end_date)
    
    def calculate_weekly_aggregations(self) -> Dict[str, Any]:
        """
        计算每周统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每周统计聚合", module=MODULE)
        
        # 使用完整自然周（上周周一至上周周日）
        today = time_utils.now_china().date()
        days_since_monday = today.weekday()
        start_date = today - timedelta(days=days_since_monday + 7)
        end_date = start_date + timedelta(days=6)
        
        return self._calculate_aggregations('weekly', start_date, end_date)
    
    def calculate_monthly_aggregations(self) -> Dict[str, Any]:
        """
        计算每月统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每月统计聚合", module=MODULE)
        
        # 获取上个月的数据（使用中国时区）
        today = time_utils.now_china().date()
        if today.month == 1:
            start_date = date(today.year - 1, 12, 1)
            end_date = date(today.year - 1, 12, 31)
        else:
            start_date = date(today.year, today.month - 1, 1)
            end_date = date(today.year, today.month, 1) - timedelta(days=1)
        
        return self._calculate_aggregations('monthly', start_date, end_date)
    
    def calculate_quarterly_aggregations(self) -> Dict[str, Any]:
        """
        计算每季度统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每季度统计聚合", module=MODULE)
        
        # 获取上个季度的数据（使用中国时区）
        today = time_utils.now_china().date()
        quarter = (today.month - 1) // 3 + 1
        
        if quarter == 1:
            # 上个季度是去年Q4
            start_date = date(today.year - 1, 10, 1)
            end_date = date(today.year - 1, 12, 31)
        else:
            # 上个季度是今年Q(quarter-1)
            quarter_start_month = (quarter - 2) * 3 + 1
            start_date = date(today.year, quarter_start_month, 1)
            end_month = quarter_start_month + 3
            if end_month > 12:
                end_date = date(today.year + 1, end_month - 12, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, end_month, 1) - timedelta(days=1)
        
        return self._calculate_aggregations('quarterly', start_date, end_date)
    
    def calculate_daily_instance_aggregations(self) -> Dict[str, Any]:
        """
        计算每日实例统计聚合（定时任务用，处理今天的数据）
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每日实例统计聚合", module=MODULE)
        
        # 获取今天的数据（与容量同步任务保持一致，使用中国时区）
        end_date = time_utils.now_china().date()
        start_date = end_date  # 同一天，处理今天的数据
        
        return self._calculate_instance_aggregations('daily', start_date, end_date)
    
    def calculate_today_instance_aggregations(self) -> Dict[str, Any]:
        """
        计算今日实例统计聚合（手动触发用，处理今天的数据）
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算今日实例统计聚合", module=MODULE)
        
        # 获取今天的数据进行聚合（使用中国时区）
        end_date = time_utils.now_china().date()
        start_date = end_date  # 同一天，处理今天的数据
        
        return self._calculate_instance_aggregations('daily', start_date, end_date)
    
    def calculate_weekly_instance_aggregations(self) -> Dict[str, Any]:
        """
        计算每周实例统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每周实例统计聚合", module=MODULE)
        
        # 获取上周完整自然周的数据（使用中国时区）
        today = time_utils.now_china().date()
        # weekday: Monday=0 ... Sunday=6
        days_since_monday = today.weekday()
        # 上周周一 = 今天减去本周已过天数再减去7天
        start_date = today - timedelta(days=days_since_monday + 7)
        end_date = start_date + timedelta(days=6)
        
        return self._calculate_instance_aggregations('weekly', start_date, end_date)
    
    def calculate_monthly_instance_aggregations(self) -> Dict[str, Any]:
        """
        计算每月实例统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每月实例统计聚合", module=MODULE)
        
        # 获取上个月的数据（使用中国时区）
        today = time_utils.now_china().date()
        if today.month == 1:
            start_date = date(today.year - 1, 12, 1)
            end_date = date(today.year - 1, 12, 31)
        else:
            start_date = date(today.year, today.month - 1, 1)
            end_date = date(today.year, today.month, 1) - timedelta(days=1)
        
        return self._calculate_instance_aggregations('monthly', start_date, end_date)
    
    def calculate_quarterly_instance_aggregations(self) -> Dict[str, Any]:
        """
        计算每季度实例统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        log_info("开始计算每季度实例统计聚合", module=MODULE)
        
        # 获取上个季度的数据（使用中国时区）
        today = time_utils.now_china().date()
        quarter = (today.month - 1) // 3 + 1
        
        if quarter == 1:
            # 上个季度是去年Q4
            start_date = date(today.year - 1, 10, 1)
            end_date = date(today.year - 1, 12, 31)
        else:
            # 上个季度是今年Q(quarter-1)
            quarter_start_month = (quarter - 2) * 3 + 1
            start_date = date(today.year, quarter_start_month, 1)
            end_date = date(today.year, quarter_start_month + 2, 1) - timedelta(days=1)
        
        return self._calculate_instance_aggregations('quarterly', start_date, end_date)

    def calculate_instance_aggregations(self, instance_id: int) -> Dict[str, Any]:
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

        period_results: dict[str, dict[str, Any]] = {}
        failed_periods: set[str] = set()
        processed_periods = 0
        skipped_periods = 0

        for period, func in period_funcs.items():
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
        return self._calculate_aggregations(normalized, start_date, end_date)
    
    def _calculate_instance_aggregations(self, period_type: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        计算指定周期的实例统计聚合
        
        Args:
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        instances = Instance.query.filter_by(is_active=True).all()
        summary = PeriodSummary(
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )

        for instance in instances:
            try:
                stats = InstanceSizeStat.query.filter(
                    InstanceSizeStat.instance_id == instance.id,
                    InstanceSizeStat.collected_date >= start_date,
                    InstanceSizeStat.collected_date <= end_date,
                    InstanceSizeStat.is_deleted == False,
                ).all()

                if not stats:
                    summary.skipped_instances += 1
                    log_warning(
                        "实例在周期内没有实例大小统计数据，跳过实例聚合",
                        module=MODULE,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        period_type=period_type,
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(),
                    )
                    continue

                self._calculate_instance_aggregation(
                    instance.id,
                    period_type,
                    start_date,
                    end_date,
                    stats,
                )
                summary.total_records += 1
                summary.processed_instances += 1
                log_debug(
                    "实例聚合计算完成",
                    module=MODULE,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                )
            except Exception as exc:  # pragma: no cover - 防御性日志
                db.session.rollback()
                summary.failed_instances += 1
                summary.errors.append(
                    f"实例 {instance.name} 聚合失败: {exc}",
                )
                log_error(
                    "实例聚合计算失败",
                    module=MODULE,
                    exception=exc,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                )

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
    
    def _calculate_instance_aggregation(self, instance_id: int, period_type: str, 
                                      start_date: date, end_date: date, 
                                      stats: List[InstanceSizeStat]) -> None:
        """
        计算单个实例的统计聚合
        
        Args:
            instance_id: 实例ID
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
            stats: 实例大小统计数据列表
        """
        try:
            self._ensure_partition_for_date(start_date)

            # 按日期分组统计数据
            daily_groups = {}
            for stat in stats:
                collected_date = stat.collected_date
                if collected_date not in daily_groups:
                    daily_groups[collected_date] = []
                daily_groups[collected_date].append(stat)
            
            # 计算每日的实例总大小和数据库数量
            daily_totals = []
            daily_db_counts = []
            
            for collected_date, day_stats in daily_groups.items():
                # 计算当日实例总大小（已经是实例级别的总大小）
                daily_total_size = sum(stat.total_size_mb for stat in day_stats)
                daily_totals.append(daily_total_size)
                
                # 计算当日数据库数量（已经是实例级别的数据库数量）
                daily_db_count = sum(stat.database_count for stat in day_stats)
                daily_db_counts.append(daily_db_count)
            
            # 检查是否已存在该周期的聚合数据
            existing = InstanceSizeAggregation.query.filter(
                InstanceSizeAggregation.instance_id == instance_id,
                InstanceSizeAggregation.period_type == period_type,
                InstanceSizeAggregation.period_start == start_date
            ).first()
            
            if existing:
                # 更新现有记录
                aggregation = existing
            else:
                # 创建新记录
                aggregation = InstanceSizeAggregation(
                    instance_id=instance_id,
                    period_type=period_type,
                    period_start=start_date,
                    period_end=end_date
                )
            
            # 更新统计指标
            aggregation.total_size_mb = int(sum(daily_totals) / len(daily_totals))  # 平均总大小
            # 计算平均每个数据库的容量
            if sum(daily_db_counts) > 0:
                avg_size_per_db = sum(daily_totals) / sum(daily_db_counts)
                aggregation.avg_size_mb = int(avg_size_per_db)
            else:
                aggregation.avg_size_mb = 0
            aggregation.max_size_mb = max(daily_totals)                             # 最大大小
            aggregation.min_size_mb = min(daily_totals)                             # 最小大小
            aggregation.data_count = len(daily_totals)                              # 数据点数量
            
            # 数据库数量统计
            aggregation.database_count = int(sum(daily_db_counts) / len(daily_db_counts))  # 平均数据库数量
            aggregation.avg_database_count = sum(daily_db_counts) / len(daily_db_counts)   # 平均数据库数量
            aggregation.max_database_count = max(daily_db_counts)                          # 最大数据库数量
            aggregation.min_database_count = min(daily_db_counts)                          # 最小数据库数量
            
            # 计算增量/减量统计
            self._calculate_instance_change_statistics(aggregation, instance_id, period_type, start_date, end_date)
            
            aggregation.calculated_at = time_utils.now()
            
            if not existing:
                db.session.add(aggregation)
            
            self._commit_with_partition_retry(aggregation, start_date)
            
            log_debug(
                "实例聚合数据保存完成",
                module=MODULE,
                instance_id=instance_id,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            
        except Exception as exc:
            db.session.rollback()
            log_error(
                "计算实例聚合失败",
                module=MODULE,
                exception=exc,
                instance_id=instance_id,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
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
    
    def _calculate_instance_change_statistics(self, aggregation, instance_id: int, 
                                            period_type: str, start_date: date, end_date: date) -> None:
        """
        计算实例增量/减量统计
        
        Args:
            aggregation: 聚合数据对象
            instance_id: 实例ID
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
        """
        try:
            # 计算上一个周期的日期范围
            prev_start_date, prev_end_date = self._get_previous_period_dates(period_type, start_date, end_date)
            
            # 获取上一个周期的实例大小统计数据
            prev_stats = InstanceSizeStat.query.filter(
                InstanceSizeStat.instance_id == instance_id,
                InstanceSizeStat.collected_date >= prev_start_date,
                InstanceSizeStat.collected_date <= prev_end_date,
                InstanceSizeStat.is_deleted == False
            ).all()
            
            if not prev_stats:
                # 没有上一个周期的数据，设置为0
                aggregation.total_size_change_mb = 0
                aggregation.total_size_change_percent = 0
                aggregation.database_count_change = 0
                aggregation.database_count_change_percent = 0
                aggregation.growth_rate = 0
                aggregation.trend_direction = "stable"
                return
            
            # 计算上一个周期的平均值
            prev_daily_groups = {}
            for stat in prev_stats:
                collected_date = stat.collected_date
                if collected_date not in prev_daily_groups:
                    prev_daily_groups[collected_date] = []
                prev_daily_groups[collected_date].append(stat)
            
            prev_daily_totals = []
            prev_daily_db_counts = []
            
            for collected_date, day_stats in prev_daily_groups.items():
                daily_total_size = sum(stat.total_size_mb for stat in day_stats)
                prev_daily_totals.append(daily_total_size)
                
                daily_db_count = sum(stat.database_count for stat in day_stats)
                prev_daily_db_counts.append(daily_db_count)
            
            prev_avg_total_size = sum(prev_daily_totals) / len(prev_daily_totals)
            prev_avg_db_count = sum(prev_daily_db_counts) / len(prev_daily_db_counts)
            
            # 计算变化量（当前 - 上一个周期）
            # 使用实例总容量的均值进行变化对比，确保量纲一致
            total_size_change_mb = aggregation.total_size_mb - prev_avg_total_size
            aggregation.total_size_change_mb = int(total_size_change_mb)
            aggregation.total_size_change_percent = round((total_size_change_mb / prev_avg_total_size * 100) if prev_avg_total_size > 0 else 0, 2)
            
            # 数据库数量变化
            db_count_change = aggregation.avg_database_count - prev_avg_db_count
            aggregation.database_count_change = int(db_count_change)
            aggregation.database_count_change_percent = round((db_count_change / prev_avg_db_count * 100) if prev_avg_db_count > 0 else 0, 2)
            
            # 设置增长率
            aggregation.growth_rate = aggregation.total_size_change_percent
            
            # 设置趋势方向
            if aggregation.total_size_change_percent > 5:
                aggregation.trend_direction = "growing"
            elif aggregation.total_size_change_percent < -5:
                aggregation.trend_direction = "shrinking"
            else:
                aggregation.trend_direction = "stable"
            
        except Exception as exc:
            log_error(
                "计算实例增量/减量统计失败，使用默认值",
                module=MODULE,
                exception=exc,
                instance_id=instance_id,
                period_type=period_type,
            )
            # 设置默认值
            aggregation.total_size_change_mb = 0
            aggregation.total_size_change_percent = 0
            aggregation.database_count_change = 0
            aggregation.database_count_change_percent = 0
            aggregation.growth_rate = 0
            aggregation.trend_direction = "stable"
    
    def _calculate_aggregations(self, period_type: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        计算指定周期的统计聚合
        
        Args:
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        instances = Instance.query.filter_by(is_active=True).all()
        summary = PeriodSummary(
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )

        for instance in instances:
            try:
                stats = DatabaseSizeStat.query.filter(
                    DatabaseSizeStat.instance_id == instance.id,
                    DatabaseSizeStat.collected_date >= start_date,
                    DatabaseSizeStat.collected_date <= end_date,
                ).all()

                if not stats:
                    summary.skipped_instances += 1
                    log_warning(
                        "实例在周期内没有数据库容量数据，跳过聚合",
                        module=MODULE,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        period_type=period_type,
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(),
                    )
                    continue

                db_groups: dict[str, list[DatabaseSizeStat]] = {}
                for stat in stats:
                    db_groups.setdefault(stat.database_name, []).append(stat)

                for db_name, db_stats in db_groups.items():
                    self._calculate_database_aggregation(
                        instance.id,
                        db_name,
                        period_type,
                        start_date,
                        end_date,
                        db_stats,
                    )
                    summary.total_records += 1

                summary.processed_instances += 1
                log_debug(
                    "实例数据库聚合计算完成",
                    module=MODULE,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                    database_count=len(db_groups),
                )
            except Exception as exc:  # pragma: no cover - 防御性日志
                db.session.rollback()
                summary.failed_instances += 1
                summary.errors.append(f"实例 {instance.name} 聚合失败: {exc}")
                log_error(
                    "实例数据库聚合执行失败",
                    module=MODULE,
                    exception=exc,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    period_type=period_type,
                )

        total_instances = len(instances)
        if summary.status is AggregationStatus.COMPLETED:
            summary.message = (
                f"{period_type} 聚合完成：处理 {summary.processed_instances}/{total_instances} 个实例"
            )
        elif summary.status is AggregationStatus.SKIPPED:
            summary.message = f"{period_type} 聚合没有可处理的数据"
        else:
            summary.message = (
                f"{period_type} 聚合完成，{summary.failed_instances} 个实例失败"
            )

        return {
            **summary.to_dict(),
            "total_instances": total_instances,
        }
    
    def _calculate_database_aggregation(self, instance_id: int, database_name: str, 
                                      period_type: str, start_date: date, end_date: date, 
                                      stats: List[DatabaseSizeStat]) -> None:
        """
        计算单个数据库的统计聚合
        
        Args:
            instance_id: 实例ID
            database_name: 数据库名称
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
            stats: 统计数据列表
        """
        try:
            self._ensure_partition_for_date(start_date)

            # 计算基本统计
            sizes = [stat.size_mb for stat in stats]
            data_sizes = [stat.data_size_mb for stat in stats if stat.data_size_mb is not None]
            # 不再计算日志大小统计
            
            # 检查是否已存在该周期的聚合数据
            existing = DatabaseSizeAggregation.query.filter(
                DatabaseSizeAggregation.instance_id == instance_id,
                DatabaseSizeAggregation.database_name == database_name,
                DatabaseSizeAggregation.period_type == period_type,
                DatabaseSizeAggregation.period_start == start_date
            ).first()
            
            if existing:
                # 更新现有记录
                aggregation = existing
            else:
                # 创建新记录
                aggregation = DatabaseSizeAggregation(
                    instance_id=instance_id,
                    database_name=database_name,
                    period_type=period_type,
                    period_start=start_date,
                    period_end=end_date
                )
            
            # 更新统计指标
            aggregation.avg_size_mb = int(sum(sizes) / len(sizes))
            aggregation.max_size_mb = max(sizes)
            aggregation.min_size_mb = min(sizes)
            aggregation.data_count = len(stats)
            
            # 数据大小统计
            if data_sizes:
                aggregation.avg_data_size_mb = int(sum(data_sizes) / len(data_sizes))
                aggregation.max_data_size_mb = max(data_sizes)
                aggregation.min_data_size_mb = min(data_sizes)
            
            # 不计算日志大小统计，直接设置为 None
            aggregation.avg_log_size_mb = None
            aggregation.max_log_size_mb = None
            aggregation.min_log_size_mb = None
            
            # 计算增量/减量统计
            self._calculate_change_statistics(aggregation, instance_id, database_name, period_type, start_date, end_date)
            
            aggregation.calculated_at = time_utils.now()
            
            if not existing:
                db.session.add(aggregation)
            
            self._commit_with_partition_retry(aggregation, start_date)

            log_debug(
                "数据库聚合数据保存完成",
                module=MODULE,
                instance_id=instance_id,
                database_name=database_name,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        except Exception as exc:
            db.session.rollback()
            log_error(
                "计算数据库聚合失败",
                module=MODULE,
                exception=exc,
                instance_id=instance_id,
                database_name=database_name,
                period_type=period_type,
            )
            raise DatabaseError(
                message="数据库聚合计算失败",
                extra={
                    "instance_id": instance_id,
                    "database_name": database_name,
                    "period_type": period_type,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            ) from exc
    
    def _calculate_change_statistics(self, aggregation, instance_id: int, database_name: str, 
                                   period_type: str, start_date: date, end_date: date) -> None:
        """
        计算增量/减量统计
        
        Args:
            aggregation: 聚合数据对象
            instance_id: 实例ID
            database_name: 数据库名称
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
        """
        try:
            # 计算上一个周期的日期范围
            prev_start_date, prev_end_date = self._get_previous_period_dates(period_type, start_date, end_date)
            
            # 获取上一个周期的数据
            prev_stats = DatabaseSizeStat.query.filter(
                DatabaseSizeStat.instance_id == instance_id,
                DatabaseSizeStat.database_name == database_name,
                DatabaseSizeStat.collected_date >= prev_start_date,
                DatabaseSizeStat.collected_date <= prev_end_date
            ).all()
            
            if not prev_stats:
                # 没有上一个周期的数据，设置为0
                aggregation.size_change_mb = 0
                aggregation.size_change_percent = 0
                aggregation.data_size_change_mb = 0
                aggregation.data_size_change_percent = 0
                aggregation.log_size_change_mb = 0
                aggregation.log_size_change_percent = 0
                aggregation.trend_direction = "stable"
                aggregation.growth_rate = 0
                return
            
            # 计算上一个周期的平均值
            prev_sizes = [stat.size_mb for stat in prev_stats]
            prev_avg_size = sum(prev_sizes) / len(prev_sizes)
            
            prev_data_sizes = [stat.data_size_mb for stat in prev_stats if stat.data_size_mb is not None]
            prev_avg_data_size = sum(prev_data_sizes) / len(prev_data_sizes) if prev_data_sizes else None
            
            # 不再计算日志大小变化
            
            # 计算变化量（当前 - 上一个周期）
            size_change_mb = aggregation.avg_size_mb - prev_avg_size
            aggregation.size_change_mb = int(size_change_mb)
            aggregation.size_change_percent = round((size_change_mb / prev_avg_size * 100) if prev_avg_size > 0 else 0, 2)
            
            # 数据大小变化
            if prev_avg_data_size is not None and aggregation.avg_data_size_mb is not None:
                data_size_change_mb = aggregation.avg_data_size_mb - prev_avg_data_size
                aggregation.data_size_change_mb = int(data_size_change_mb)
                aggregation.data_size_change_percent = round((data_size_change_mb / prev_avg_data_size * 100) if prev_avg_data_size > 0 else 0, 2)
            
            # 不计算日志大小变化，直接设置为 None
            aggregation.log_size_change_mb = None
            aggregation.log_size_change_percent = None
            
            # 设置增长率（简化，不判断趋势方向）
            aggregation.growth_rate = aggregation.size_change_percent
            
        except Exception as exc:
            log_error(
                "计算数据库增量统计失败，使用默认值",
                module=MODULE,
                exception=exc,
                instance_id=instance_id,
                database_name=database_name,
                period_type=period_type,
            )
            # 设置默认值
            aggregation.size_change_mb = 0
            aggregation.size_change_percent = 0
            aggregation.data_size_change_mb = 0
            aggregation.data_size_change_percent = 0
            aggregation.log_size_change_mb = 0
            aggregation.log_size_change_percent = 0
            aggregation.growth_rate = 0
    
    def _get_previous_period_dates(self, period_type: str, start_date: date, end_date: date) -> tuple:
        """
        获取上一个周期的日期范围
        
        Args:
            period_type: 统计周期类型
            start_date: 当前周期开始日期
            end_date: 当前周期结束日期
            
        Returns:
            tuple: (上一个周期开始日期, 上一个周期结束日期)
        """
        if period_type == "daily":
            # 前一天（支持当天数据聚合的情况）
            if start_date == end_date:
                # 如果是同一天，前一天就是昨天
                prev_end_date = start_date - timedelta(days=1)
                prev_start_date = prev_end_date
            else:
                # 如果是多天，前一天是开始日期的前一天
                period_duration = end_date - start_date
                prev_end_date = start_date - timedelta(days=1)
                prev_start_date = prev_end_date - period_duration
        elif period_type == "weekly":
            # 上一周
            period_duration = end_date - start_date
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - period_duration
        elif period_type == "monthly":
            # 上一个月
            if start_date.month == 1:
                prev_start_date = date(start_date.year - 1, 12, 1)
                prev_end_date = date(start_date.year - 1, 12, 31)
            else:
                prev_start_date = date(start_date.year, start_date.month - 1, 1)
                prev_end_date = date(start_date.year, start_date.month, 1) - timedelta(days=1)
        elif period_type == "quarterly":
            # 上一个季度
            quarter = (start_date.month - 1) // 3 + 1
            if quarter == 1:
                prev_start_date = date(start_date.year - 1, 10, 1)
                prev_end_date = date(start_date.year - 1, 12, 31)
            else:
                prev_quarter_start_month = (quarter - 2) * 3 + 1
                prev_start_date = date(start_date.year, prev_quarter_start_month, 1)
                prev_end_date = date(start_date.year, prev_quarter_start_month + 2, 1) - timedelta(days=1)
        else:
            # 默认返回相同周期
            period_duration = end_date - start_date
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - period_duration
        
        return prev_start_date, prev_end_date
    
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
    
    def get_trends_analysis(self, instance_id: int, period_type: str, 
                           months: int = 12) -> Dict[str, Any]:
        """
        获取趋势分析数据
        
        Args:
            instance_id: 实例ID
            period_type: 统计周期类型
            months: 返回最近几个月的数据
            
        Returns:
            Dict[str, Any]: 趋势分析数据
        """
        try:
            # 计算开始日期（使用中国时区）
            end_date = time_utils.now_china().date()
            start_date = end_date - timedelta(days=months * 30)
            
            # 获取聚合数据
            aggregations = self.get_aggregations(instance_id, period_type, start_date, end_date)
            
            if not aggregations:
                return {
                    'trends': [],
                    'summary': {
                        'total_growth_rate': 0,
                        'largest_database': None,
                        'fastest_growing': None
                    }
                }
            
            # 按周期分组
            trends = {}
            for agg in aggregations:
                period = agg['period_start'][:7]  # YYYY-MM
                if period not in trends:
                    trends[period] = {
                        'period': period,
                        'total_size_mb': 0,
                        'databases': []
                    }
                
                trends[period]['total_size_mb'] += agg['statistics']['avg_size_mb']
                trends[period]['databases'].append({
                    'database_name': agg['database_name'],
                    'avg_size_mb': agg['statistics']['avg_size_mb'],
                    'growth_rate': 0  # 需要计算
                })
            
            # 计算增长率
            periods = sorted(trends.keys())
            for i, period in enumerate(periods):
                if i > 0:
                    prev_period = periods[i-1]
                    for db in trends[period]['databases']:
                        prev_db = next((d for d in trends[prev_period]['databases'] 
                                      if d['database_name'] == db['database_name']), None)
                        if prev_db:
                            growth_rate = ((db['avg_size_mb'] - prev_db['avg_size_mb']) / 
                                         prev_db['avg_size_mb'] * 100) if prev_db['avg_size_mb'] > 0 else 0
                            db['growth_rate'] = round(growth_rate, 2)
            
            # 计算总体统计
            total_growth_rate = 0
            largest_database = None
            fastest_growing = None
            max_size = 0
            max_growth = 0
            
            for period_data in trends.values():
                for db in period_data['databases']:
                    if db['avg_size_mb'] > max_size:
                        max_size = db['avg_size_mb']
                        largest_database = db['database_name']
                    
                    if abs(db['growth_rate']) > max_growth:
                        max_growth = abs(db['growth_rate'])
                        fastest_growing = db['database_name']
            
            # 计算总体增长率（简化计算）
            if len(periods) > 1:
                first_period = trends[periods[0]]['total_size_mb']
                last_period = trends[periods[-1]]['total_size_mb']
                total_growth_rate = ((last_period - first_period) / first_period * 100) if first_period > 0 else 0
            
            return {
                'trends': list(trends.values()),
                'summary': {
                    'total_growth_rate': round(total_growth_rate, 2),
                    'largest_database': largest_database,
                    'fastest_growing': fastest_growing
                }
            }
            
        except Exception as exc:
            log_error(
                "获取趋势分析数据失败",
                module=MODULE,
                exception=exc,
                instance_id=instance_id,
                period_type=period_type,
            )
            return {
                'trends': [],
                'summary': {
                    'total_growth_rate': 0,
                    'largest_database': None,
                    'fastest_growing': None
                }
            }
    
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

    def _summarize_instance_period(
        self,
        instance: Instance,
        *,
        period_type: str,
        start_date: date,
        end_date: date,
    ) -> InstanceSummary:
        """聚合单个实例的指定周期，并返回汇总信息"""
        stats = InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance.id,
            InstanceSizeStat.collected_date >= start_date,
            InstanceSizeStat.collected_date <= end_date,
            InstanceSizeStat.is_deleted == False,
        ).all()

        extra_details = {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        }
        if start_date == end_date:
            extra_details["period_date"] = start_date.isoformat()

        if not stats:
            log_warning(
                "实例在指定周期没有统计数据，跳过实例聚合",
                module=MODULE,
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

        self._calculate_instance_aggregation(instance.id, period_type, start_date, end_date, stats)
        log_info(
            "实例周期聚合已更新",
            module=MODULE,
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
    
    def calculate_daily_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算日统计聚合"""
        instance = Instance.query.get(instance_id)
        if not instance:
            raise NotFoundError(
                message="实例不存在",
                extra={"instance_id": instance_id},
            )

        target_date = time_utils.now_china().date()
        summary = self._summarize_instance_period(
            instance,
            period_type="daily",
            start_date=target_date,
            end_date=target_date,
        )
        return summary.to_dict()
    
    def calculate_weekly_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算周统计聚合"""
        instance = Instance.query.get(instance_id)
        if not instance:
            raise NotFoundError(
                message="实例不存在",
                extra={"instance_id": instance_id},
            )

        today = time_utils.now_china().date()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)

        summary = self._summarize_instance_period(
            instance,
            period_type="weekly",
            start_date=last_monday,
            end_date=last_sunday,
        )
        return summary.to_dict()
    
    def calculate_monthly_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算月统计聚合"""
        instance = Instance.query.get(instance_id)
        if not instance:
            raise NotFoundError(
                message="实例不存在",
                extra={"instance_id": instance_id},
            )

        today = time_utils.now_china().date()
        if today.month == 1:
            last_month = 12
            last_year = today.year - 1
        else:
            last_month = today.month - 1
            last_year = today.year

        start_date = date(last_year, last_month, 1)
        if last_month == 12:
            end_date = date(last_year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(last_year, last_month + 1, 1) - timedelta(days=1)

        summary = self._summarize_instance_period(
            instance,
            period_type="monthly",
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()
    
    def calculate_quarterly_aggregations_for_instance(self, instance_id: int) -> Dict[str, Any]:
        """为指定实例计算季度统计聚合"""
        instance = Instance.query.get(instance_id)
        if not instance:
            raise NotFoundError(
                message="实例不存在",
                extra={"instance_id": instance_id},
            )

        today = time_utils.now_china().date()
        current_quarter = (today.month - 1) // 3 + 1

        if current_quarter == 1:
            quarter_start_month = 10
            year = today.year - 1
        else:
            quarter_start_month = ((current_quarter - 2) * 3) + 1
            year = today.year

        start_date = date(year, quarter_start_month, 1)
        end_month = quarter_start_month + 3
        if end_month > 12:
            end_date = date(year + 1, end_month - 12, 1) - timedelta(days=1)
        else:
            end_date = date(year, end_month, 1) - timedelta(days=1)

        summary = self._summarize_instance_period(
            instance,
            period_type="quarterly",
            start_date=start_date,
            end_date=end_date,
        )
        return summary.to_dict()
