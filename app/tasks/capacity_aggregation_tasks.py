"""
数据库大小统计聚合定时任务
负责计算每周、每月、每季度的统计聚合数据
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Set

from app import db
from app.config import Config
from app.constants import SyncStatus, TaskStatus
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.services.aggregation.aggregation_service import AggregationService
from app.models.instance import Instance
from app.utils.structlog_config import log_error, log_info

STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"
TASK_MODULE = "aggregation_tasks"
PERIOD_ORDER = ["daily", "weekly", "monthly", "quarterly"]


@dataclass(frozen=True)
class PeriodConfig:
    key: str
    instance_method: str
    database_method: str


PERIOD_CONFIGS: dict[str, PeriodConfig] = {
    cfg.key: cfg
    for cfg in [
        PeriodConfig(
            "daily",
            "calculate_daily_aggregations_for_instance",
            "calculate_daily_aggregations",
        ),
        PeriodConfig(
            "weekly",
            "calculate_weekly_aggregations_for_instance",
            "calculate_weekly_aggregations",
        ),
        PeriodConfig(
            "monthly",
            "calculate_monthly_aggregations_for_instance",
            "calculate_monthly_aggregations",
        ),
        PeriodConfig(
            "quarterly",
            "calculate_quarterly_aggregations_for_instance",
            "calculate_quarterly_aggregations",
        ),
    ]
}


def _select_periods(requested: Optional[Sequence[str]], logger) -> List[str]:
    """根据请求的周期返回有效周期列表"""
    if requested is None:
        return PERIOD_ORDER.copy()

    normalized: List[str] = []
    unknown: List[str] = []
    seen: set[str] = set()
    for item in requested:
        key = (item or "").strip().lower()
        if not key:
            continue
        if key in PERIOD_CONFIGS:
            if key not in seen:
                normalized.append(key)
                seen.add(key)
        else:
            unknown.append(item)

    if unknown:
        logger.warning(
            "忽略未知聚合周期",
            module="aggregation_sync",
            unknown_periods=unknown,
        )

    ordered = [period for period in PERIOD_ORDER if period in normalized]
    return ordered


def _extract_processed_records(result: dict[str, Any] | None) -> int:
    if not result:
        return 0
    return int(
        result.get("processed_records")
        or result.get("total_records")
        or result.get("aggregations_created")
        or 0
    )


def _extract_error_message(result: dict[str, Any] | None) -> str:
    if not result:
        return "无返回结果"
    errors = result.get("errors")
    if isinstance(errors, list) and errors:
        return "; ".join(str(err) for err in errors)
    return result.get("error") or result.get("message") or "未知错误"


def calculate_database_size_aggregations(
    manual_run: bool = False,
    periods: Optional[List[str]] = None,
    created_by: int | None = None,
) -> Dict[str, Any]:
    """
    计算数据库大小统计聚合（拆分为日/周/月/季四个阶段顺序执行）

    Args:
        manual_run: 是否手动触发执行
        periods: 需要执行的聚合周期列表（daily/weekly/monthly/quarterly），默认全部
    """
    from app import create_app
    from app.services.sync_session_service import sync_session_service
    from app.utils.time_utils import time_utils
    from app.utils.structlog_config import get_sync_logger

    app = create_app()
    with app.app_context():
        sync_logger = get_sync_logger()
        session = None
        try:
            sync_logger.info("开始执行数据库大小统计聚合任务", module="aggregation_sync")

            if not getattr(Config, "AGGREGATION_ENABLED", True):
                sync_logger.info("数据库大小统计聚合功能已禁用", module="aggregation_sync")
                return {
                    "status": STATUS_SKIPPED,
                    "message": "统计聚合功能已禁用",
                    "metrics": {
                        "aggregations_created": 0,
                        "processed_instances": 0,
                    },
                    "periods_executed": [],
                }

            active_instances = Instance.query.filter_by(is_active=True).all()
            if not active_instances:
                sync_logger.warning("没有找到活跃的数据库实例", module="aggregation_sync")
                return {
                    "status": STATUS_SKIPPED,
                    "message": "没有活跃的数据库实例需要聚合",
                    "metrics": {
                        "aggregations_created": 0,
                        "processed_instances": 0,
                    },
                    "periods_executed": [],
                }

            selected_periods = _select_periods(periods, sync_logger)
            if not selected_periods:
                sync_logger.warning(
                    "未选择任何有效的聚合周期，任务直接完成",
                    module="aggregation_sync",
                    requested_periods=periods,
                )
                return {
                    "status": STATUS_SKIPPED,
                    "message": "未选择有效的聚合周期，未执行统计任务",
                    "metrics": {
                        "aggregations_created": 0,
                        "processed_instances": 0,
                    },
                    "periods_executed": [],
                }

            sync_logger.info(
                "找到活跃实例，准备创建同步会话",
                module="aggregation_sync",
                instance_count=len(active_instances),
                manual_run=manual_run,
                periods=selected_periods,
            )

            if manual_run:
                sync_type = SyncOperationType.MANUAL_TASK.value
            else:
                created_by = None
                sync_type = SyncOperationType.SCHEDULED_TASK.value

            session = sync_session_service.create_session(
                sync_type=sync_type,
                sync_category=SyncCategory.AGGREGATION.value,
                created_by=created_by,
            )

            sync_logger.info(
                "聚合同步会话已创建",
                module="aggregation_sync",
                session_id=session.session_id,
                instance_count=len(active_instances),
                manual_run=manual_run,
                created_by=created_by,
                periods=selected_periods,
            )

            instance_ids = [inst.id for inst in active_instances]
            records = sync_session_service.add_instance_records(
                session.session_id,
                instance_ids,
                sync_category=SyncCategory.AGGREGATION.value,
            )
            session.total_instances = len(active_instances)

            records_by_instance = {record.instance_id: record for record in records}

            started_record_ids: Set[int] = set()
            finalized_record_ids: Set[int] = set()

            service = AggregationService()
            instance_details: dict[int, dict[str, Any]] = {}
            successful_instances = 0
            failed_instances = 0
            total_instance_aggregations = 0

            for instance in active_instances:
                record = records_by_instance.get(instance.id)
                if record:
                    if sync_session_service.start_instance_sync(record.id):
                        started_record_ids.add(record.id)
                else:
                    sync_logger.warning(
                        "未找到实例的同步记录，跳过开始标记",
                        module="aggregation_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        instance_name=instance.name,
                    )

                try:
                    service_summary = service.calculate_instance_aggregations(
                        instance.id,
                        periods=selected_periods,
                    )
                    period_results = service_summary.get("periods", {}) or {}
                except Exception as period_exc:  # pragma: no cover - 防御性日志
                    sync_logger.error(
                        "实例聚合执行异常",
                        module="aggregation_sync",
                        instance_id=instance.id,
                        instance_name=instance.name,
                        error=str(period_exc),
                    )
                    period_results = {
                        period_name: {
                            "status": STATUS_FAILED,
                            "instance_id": instance.id,
                            "instance_name": instance.name,
                            "period_type": period_name,
                            "errors": [str(period_exc)],
                            "error": str(period_exc),
                        }
                        for period_name in selected_periods
                    }

                filtered_period_results: dict[str, Dict[str, Any]] = {}
                instance_errors: List[str] = []
                aggregated_count = 0

                for period_name in selected_periods:
                    result = period_results.get(period_name)
                    if result is None:
                        result = {
                            "status": STATUS_FAILED,
                            "errors": ["聚合服务未返回结果"],
                            "instance_id": instance.id,
                            "instance_name": instance.name,
                            "period_type": period_name,
                        }
                    filtered_period_results[period_name] = result

                    status = (result.get("status") or STATUS_FAILED).lower()
                    if status == STATUS_COMPLETED:
                        sync_logger.info(
                            "实例聚合完成",
                            module="aggregation_sync",
                            period=period_name,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            total_records=_extract_processed_records(result),
                            message=result.get("message"),
                        )
                    elif status == STATUS_SKIPPED:
                        sync_logger.info(
                            "实例聚合跳过",
                            module="aggregation_sync",
                            period=period_name,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            message=result.get("message"),
                        )
                    else:
                        error_msg = _extract_error_message(result)
                        instance_errors.append(f"{period_name}: {error_msg}")
                        sync_logger.error(
                            "实例聚合失败",
                            module="aggregation_sync",
                            period=period_name,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            error=error_msg,
                            errors=result.get("errors"),
                        )

                    aggregated_count += _extract_processed_records(result)

                instance_details[instance.id] = {
                    "aggregations_created": aggregated_count,
                    "errors": instance_errors,
                    "period_results": filtered_period_results,
                }

                details = {
                    "aggregations_created": aggregated_count,
                    "aggregation_count": aggregated_count,
                    "periods": filtered_period_results,
                    "errors": instance_errors,
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                }

                if record:
                    if instance_errors:
                        if sync_session_service.fail_instance_sync(
                            record.id,
                            error_message="; ".join(instance_errors),
                            sync_details=details,
                        ):
                            finalized_record_ids.add(record.id)
                        failed_instances += 1
                    else:
                        if sync_session_service.complete_instance_sync(
                            record.id,
                            items_synced=aggregated_count,
                            items_created=0,
                            items_updated=0,
                            items_deleted=0,
                            sync_details=details,
                        ):
                            finalized_record_ids.add(record.id)
                        successful_instances += 1

                total_instance_aggregations += aggregated_count

            period_summaries: List[dict[str, Any]] = []
            total_database_aggregations = 0
            for period_name in selected_periods:
                config = PERIOD_CONFIGS.get(period_name)
                if not config:
                    continue
                database_func = getattr(service, config.database_method, None)
                if database_func is None:
                    sync_logger.warning(
                        "未找到数据库聚合函数，跳过周期",
                        module="aggregation_sync",
                        period=period_name,
                    )
                    continue
                try:
                    db_result = database_func()
                except Exception as db_exc:  # pragma: no cover - 防御性日志
                    sync_logger.error(
                        "数据库级聚合执行异常",
                        module="aggregation_sync",
                        period=period_name,
                        error=str(db_exc),
                    )
                    db_result = {
                        "status": STATUS_FAILED,
                        "error": str(db_exc),
                        "errors": [str(db_exc)],
                        "period_type": period_name,
                    }
                status = (db_result.get("status") or STATUS_FAILED).lower()
                if status == STATUS_COMPLETED:
                    sync_logger.info(
                        "数据库级聚合完成",
                        module="aggregation_sync",
                        period=period_name,
                        total_records=db_result.get("total_records", 0),
                        processed_instances=db_result.get("processed_instances"),
                    )
                elif status == STATUS_SKIPPED:
                    sync_logger.info(
                        "数据库级聚合跳过",
                        module="aggregation_sync",
                        period=period_name,
                        message=db_result.get("message"),
                    )
                else:
                    sync_logger.error(
                        "数据库级聚合失败",
                        module="aggregation_sync",
                        period=period_name,
                        error=db_result.get("error"),
                        errors=db_result.get("errors"),
                    )
                db_result.setdefault("period_type", period_name)
                period_summaries.append(db_result)
                total_database_aggregations += _extract_processed_records(db_result)

            session.successful_instances = successful_instances
            session.failed_instances = failed_instances
            session.status = "completed" if failed_instances == 0 else "failed"
            session.completed_at = time_utils.now()
            db.session.commit()

            overall_status = STATUS_COMPLETED if failed_instances == 0 else STATUS_FAILED
            message = (
                f"统计聚合完成: 成功 {successful_instances} 个实例，失败 {failed_instances} 个实例"
                if failed_instances
                else f"统计聚合完成，共处理 {successful_instances} 个实例"
            )

            sync_logger.info(
                "统计聚合任务完成",
                module="aggregation_sync",
                session_id=session.session_id,
                successful_instances=successful_instances,
                failed_instances=failed_instances,
                total_instance_aggregations=total_instance_aggregations,
                total_database_aggregations=total_database_aggregations,
                manual_run=manual_run,
            )

            return {
                "status": overall_status,
                "message": message,
                "session_id": session.session_id,
                "periods_executed": selected_periods,
                "details": {
                    "periods": period_summaries,
                    "instances": instance_details,
                },
                "metrics": {
                    "instances": {
                        "total": len(active_instances),
                        "successful": successful_instances,
                        "failed": failed_instances,
                    },
                    "records": {
                        "instance": total_instance_aggregations,
                        "database": total_database_aggregations,
                        "total": total_instance_aggregations + total_database_aggregations,
                    },
                },
            }
        except Exception as exc:
            sync_logger.error(
                "统计聚合任务异常",
                module="aggregation_sync",
                error=str(exc),
            )
            if session is not None:
                try:
                    db.session.rollback()
                except Exception:  # pragma: no cover - 防御性处理
                    pass
                # 将仍处于运行状态的实例记录标记为失败
                leftover_ids = (
                    locals().get("started_record_ids", set())
                    - locals().get("finalized_record_ids", set())
                )
                for record_id in leftover_ids:
                    try:
                        sync_session_service.fail_instance_sync(
                            record_id,
                            error_message=f"聚合任务异常: {exc}",
                        )
                    except Exception:
                        continue
                session.status = "failed"
                session.completed_at = time_utils.now()
                db.session.add(session)
                db.session.commit()

            return {
                "status": STATUS_FAILED,
                "message": f"统计聚合任务执行失败: {exc}",
                "error": str(exc),
                "periods_executed": locals().get("selected_periods"),
            }


def calculate_instance_aggregations(instance_id: int) -> Dict[str, Any]:
    """
    计算指定实例的统计聚合
    
    Args:
        instance_id: 实例ID
        
    Returns:
        Dict[str, Any]: 聚合结果
    """
    from app import create_app
    
    app = create_app()
    with app.app_context():
        try:
            log_info(
                "开始计算实例统计聚合",
                module=TASK_MODULE,
                instance_id=instance_id,
            )

            instance = Instance.query.get(instance_id)
            if not instance:
                return {
                    "status": STATUS_FAILED,
                    "message": f"实例 {instance_id} 不存在",
                }
            
            if not instance.is_active:
                return {
                    "status": STATUS_SKIPPED,
                    "message": f"实例 {instance_id} 未激活",
                }
            
            # 创建聚合服务
            service = AggregationService()
            
            # 计算实例的聚合数据
            result = service.calculate_instance_aggregations(instance_id)
            
            log_info(
                "实例统计聚合完成",
                module=TASK_MODULE,
                instance_id=instance_id,
                status=result.get("status"),
                message=result.get("message"),
            )
            return result
            
        except Exception as exc:
            log_error(
                "计算实例统计聚合失败",
                module=TASK_MODULE,
                exception=exc,
                instance_id=instance_id,
            )
            return {
                "status": STATUS_FAILED,
                "message": f"计算实例 {instance_id} 统计聚合失败: {exc}",
                "error": str(exc),
            }


def calculate_period_aggregations(period_type: str, start_date: date, end_date: date) -> Dict[str, Any]:
    """
    计算指定周期的统计聚合
    
    Args:
        period_type: 周期类型 (weekly, monthly, quarterly)
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        Dict[str, Any]: 聚合结果
    """
    from app import create_app
    
    app = create_app()
    with app.app_context():
        try:
            log_info(
                "开始计算指定周期统计聚合",
                module=TASK_MODULE,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            
            # 创建聚合服务
            service = AggregationService()
            
            # 计算指定周期的聚合数据
            result = service.calculate_period_aggregations(period_type, start_date, end_date)
            
            log_info(
                "指定周期统计聚合完成",
                module=TASK_MODULE,
                period_type=period_type,
                status=result.get("status"),
                message=result.get("message"),
            )
            
            return result
            
        except Exception as exc:
            log_error(
                "计算指定周期统计聚合失败",
                module=TASK_MODULE,
                exception=exc,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            return {
                "status": STATUS_FAILED,
                "message": f"计算 {period_type} 周期统计聚合失败: {exc}",
                "error": str(exc),
            }


def get_aggregation_status() -> Dict[str, Any]:
    """
    获取聚合状态信息
    
    Returns:
        Dict[str, Any]: 状态信息
    """
    from app import create_app
    
    app = create_app()
    with app.app_context():
        try:
            from app.models.database_size_aggregation import DatabaseSizeAggregation
            from sqlalchemy import func, desc
            
            # 获取今日聚合统计
            today = date.today()
            
            # 获取最近聚合时间
            latest_aggregation = DatabaseSizeAggregation.query.order_by(
                desc(DatabaseSizeAggregation.calculated_at)
            ).first()
            
            # 获取各周期类型的聚合数量
            from sqlalchemy import func
            aggregation_counts = db.session.query(
                DatabaseSizeAggregation.period_type,
                func.count(DatabaseSizeAggregation.id).label('count')
            ).group_by(DatabaseSizeAggregation.period_type).all()
            
            # 获取总实例数
            total_instances = Instance.query.filter_by(is_active=True).count()
            
            return {
                "status": STATUS_COMPLETED,
                "latest_aggregation": latest_aggregation.calculated_at.isoformat() if latest_aggregation else None,
                "aggregation_counts": {row.period_type: row.count for row in aggregation_counts},
                "total_instances": total_instances,
                "check_date": today.isoformat(),
            }
            
        except Exception as exc:
            log_error(
                "获取聚合状态失败",
                module=TASK_MODULE,
                exception=exc,
            )
            return {
                "status": STATUS_FAILED,
                "message": f"获取聚合状态失败: {exc}",
                "error": str(exc),
            }


def validate_aggregation_config() -> Dict[str, Any]:
    """
    验证聚合配置
    
    Returns:
        Dict[str, Any]: 验证结果
    """
    try:
        config_issues = []
        
        # 检查聚合是否启用
        if not getattr(Config, 'AGGREGATION_ENABLED', True):
            config_issues.append("数据库大小统计聚合已禁用")
        
        # 检查聚合时间配置
        aggregation_hour = getattr(Config, 'AGGREGATION_HOUR', 4)
        if not isinstance(aggregation_hour, int) or aggregation_hour < 0 or aggregation_hour > 23:
            config_issues.append("聚合时间配置无效，应为0-23之间的整数")
        
        status = STATUS_COMPLETED if not config_issues else STATUS_FAILED
        message = "聚合配置验证通过" if not config_issues else "聚合配置存在需要关注的问题"

        return {
            "status": status,
            "message": message,
            "issues": config_issues,
            "config": {
                "enabled": getattr(Config, "AGGREGATION_ENABLED", True),
                "hour": aggregation_hour,
            },
        }
        
    except Exception as exc:
        log_error(
            "验证聚合配置失败",
            module=TASK_MODULE,
            exception=exc,
        )
        return {
            "status": STATUS_FAILED,
            "message": f"验证聚合配置失败: {exc}",
            "error": str(exc),
        }
