"""
数据库大小统计聚合定时任务
负责计算每周、每月、每季度的统计聚合数据
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Callable, Optional, Set
from app.constants.sync_constants import SyncOperationType, SyncCategory
from app.services.database_size_aggregation_service import DatabaseSizeAggregationService
from app.models.instance import Instance
from app.config import Config
from app import db

logger = logging.getLogger(__name__)


def _initialize_instance_state(instances: List["Instance"], records_by_instance: dict[int, Any]) -> dict[int, dict[str, Any]]:
    """根据实例列表初始化状态字典"""
    instance_state: dict[int, dict[str, Any]] = {}
    for instance in instances:
        instance_state[instance.id] = {
            "record": records_by_instance.get(instance.id),
            "period_results": {},
            "aggregations_created": 0,
            "errors": [],
        }
    return instance_state


def _update_instance_state(instance_state: dict[int, dict[str, Any]], instance_id: int, period: str, result: dict) -> None:
    """更新指定实例的聚合结果状态"""
    state = instance_state.get(instance_id)
    if state is None:
        return

    state["period_results"][period] = result
    records_created = int(result.get("total_records", 0) or 0)
    state["aggregations_created"] += records_created

    status = result.get("status", "error")
    if status != "success":
        error_message = result.get("error") or result.get("message") or f"{period} 聚合失败"
        state["errors"].append(f"{period}: {error_message}")


def _run_period_aggregation(
    *,
    period: str,
    instances: List["Instance"],
    service: DatabaseSizeAggregationService,
    instance_func: Callable[[int], Dict[str, Any]],
    database_func: Callable[[], Dict[str, Any]],
    sync_logger,
    instance_state: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """执行单个周期的聚合计算"""
    period_summary: dict[str, Any] = {
        "period": period,
        "instance_results": [],
        "database_result": None,
    }

    for instance in instances:
        try:
            result = instance_func(instance.id)
        except Exception as exc:  # pragma: no cover - 防御性日志
            sync_logger.error(
                f"{period} 聚合计算异常",
                module="aggregation_sync",
                period=period,
                instance_id=instance.id,
                instance_name=instance.name,
                error=str(exc),
            )
            result = {
                "status": "error",
                "instance_id": instance.id,
                "instance_name": instance.name,
                "period_type": period,
                "error": str(exc),
            }

        result.setdefault("instance_id", instance.id)
        result.setdefault("instance_name", instance.name)
        result.setdefault("period_type", period)

        if result.get("status") == "success":
            sync_logger.info(
                f"{period} 聚合完成",
                module="aggregation_sync",
                period=period,
                instance_id=instance.id,
                instance_name=instance.name,
                total_records=result.get("total_records", 0),
                message=result.get("message"),
            )
        else:
            sync_logger.error(
                f"{period} 聚合失败",
                module="aggregation_sync",
                period=period,
                instance_id=result.get("instance_id"),
                instance_name=result.get("instance_name"),
                error=result.get("error") or result.get("message"),
            )

        period_summary["instance_results"].append(result)
        _update_instance_state(instance_state, instance.id, period, result)

    try:
        database_result = database_func()
    except Exception as exc:  # pragma: no cover - 防御性日志
        sync_logger.error(
            f"{period} 数据库聚合异常",
            module="aggregation_sync",
            period=period,
            error=str(exc),
        )
        database_result = {
            "status": "error",
            "period_type": period,
            "error": str(exc),
        }

    if database_result.get("status") == "success":
        sync_logger.info(
            f"{period} 数据库聚合完成",
            module="aggregation_sync",
            period=period,
            total_records=database_result.get("total_records", 0),
            processed_instances=database_result.get("processed_instances", 0),
        )
    else:
        sync_logger.error(
            f"{period} 数据库聚合失败",
            module="aggregation_sync",
            period=period,
            error=database_result.get("error"),
        )

    database_result.setdefault("period_type", period)
    period_summary["database_result"] = database_result
    return period_summary


def run_daily_aggregation(
    *,
    instances: List["Instance"],
    service: DatabaseSizeAggregationService,
    sync_logger,
    instance_state: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """执行日聚合"""
    return _run_period_aggregation(
        period="daily",
        instances=instances,
        service=service,
        instance_func=service.calculate_daily_aggregations_for_instance,
        database_func=service.calculate_daily_aggregations,
        sync_logger=sync_logger,
        instance_state=instance_state,
    )


def run_weekly_aggregation(
    *,
    instances: List["Instance"],
    service: DatabaseSizeAggregationService,
    sync_logger,
    instance_state: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """执行周聚合"""
    return _run_period_aggregation(
        period="weekly",
        instances=instances,
        service=service,
        instance_func=service.calculate_weekly_aggregations_for_instance,
        database_func=service.calculate_weekly_aggregations,
        sync_logger=sync_logger,
        instance_state=instance_state,
    )


def run_monthly_aggregation(
    *,
    instances: List["Instance"],
    service: DatabaseSizeAggregationService,
    sync_logger,
    instance_state: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """执行月聚合"""
    return _run_period_aggregation(
        period="monthly",
        instances=instances,
        service=service,
        instance_func=service.calculate_monthly_aggregations_for_instance,
        database_func=service.calculate_monthly_aggregations,
        sync_logger=sync_logger,
        instance_state=instance_state,
    )


def run_quarterly_aggregation(
    *,
    instances: List["Instance"],
    service: DatabaseSizeAggregationService,
    sync_logger,
    instance_state: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """执行季聚合"""
    return _run_period_aggregation(
        period="quarterly",
        instances=instances,
        service=service,
        instance_func=service.calculate_quarterly_aggregations_for_instance,
        database_func=service.calculate_quarterly_aggregations,
        sync_logger=sync_logger,
        instance_state=instance_state,
    )


def calculate_database_size_aggregations(
    manual_run: bool = False,
    periods: Optional[List[str]] = None,
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
                    "success": True,
                    "message": "统计聚合功能已禁用",
                    "aggregations_created": 0,
                }

            active_instances = Instance.query.filter_by(is_active=True).all()
            if not active_instances:
                sync_logger.warning("没有找到活跃的数据库实例", module="aggregation_sync")
                return {
                    "success": True,
                    "message": "没有活跃的数据库实例需要聚合",
                    "aggregations_created": 0,
                }

            period_order = ["daily", "weekly", "monthly", "quarterly"]
            selected_periods = (
                period_order if periods is None else [p for p in period_order if p in periods]
            )
            if periods is not None:
                unknown_periods = [p for p in periods if p not in period_order]
                if unknown_periods:
                    sync_logger.warning(
                        "忽略未知聚合周期",
                        module="aggregation_sync",
                        unknown_periods=unknown_periods,
                    )
            if not selected_periods:
                sync_logger.warning(
                    "未选择任何有效的聚合周期，任务直接完成",
                    module="aggregation_sync",
                    requested_periods=periods,
                )
                return {
                    "success": True,
                    "message": "未选择有效的聚合周期，未执行统计任务",
                    "aggregations_created": 0,
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
                from flask_login import current_user

                created_by = current_user.id if current_user.is_authenticated else None
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
            instance_state = _initialize_instance_state(active_instances, records_by_instance)

            started_record_ids: Set[int] = set()
            finalized_record_ids: Set[int] = set()

            service = DatabaseSizeAggregationService()
            instance_period_funcs: dict[str, Callable[[int], Dict[str, Any]]] = {
                "daily": service.calculate_daily_aggregations_for_instance,
                "weekly": service.calculate_weekly_aggregations_for_instance,
                "monthly": service.calculate_monthly_aggregations_for_instance,
                "quarterly": service.calculate_quarterly_aggregations_for_instance,
            }
            database_period_funcs: dict[str, Callable[[], Dict[str, Any]]] = {
                "daily": service.calculate_daily_aggregations,
                "weekly": service.calculate_weekly_aggregations,
                "monthly": service.calculate_monthly_aggregations,
                "quarterly": service.calculate_quarterly_aggregations,
            }

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

                period_results: dict[str, Dict[str, Any]] = {}
                instance_errors: List[str] = []
                aggregated_count = 0

                for period_name in selected_periods:
                    period_func = instance_period_funcs.get(period_name)
                    if not period_func:
                        sync_logger.warning(
                            "未找到实例聚合函数，跳过周期",
                            module="aggregation_sync",
                            period=period_name,
                            instance_id=instance.id,
                        )
                        continue

                    try:
                        result = period_func(instance.id)
                    except Exception as period_exc:  # pragma: no cover - 防御性日志
                        sync_logger.error(
                            "实例聚合执行异常",
                            module="aggregation_sync",
                            period=period_name,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            error=str(period_exc),
                        )
                        result = {
                            "status": "error",
                            "error": str(period_exc),
                            "instance_id": instance.id,
                            "instance_name": instance.name,
                            "period_type": period_name,
                        }

                    status = result.get("status")
                    if status != "success":
                        error_msg = result.get("error") or result.get("message") or "未知错误"
                        instance_errors.append(f"{period_name}: {error_msg}")
                        sync_logger.error(
                            "实例聚合失败",
                            module="aggregation_sync",
                            period=period_name,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            error=error_msg,
                        )
                    else:
                        sync_logger.info(
                            "实例聚合完成",
                            module="aggregation_sync",
                            period=period_name,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            total_records=result.get("total_records", 0),
                            message=result.get("message"),
                        )

                    aggregated_count += result.get("total_records", 0) or 0
                    period_results[period_name] = result

                state = instance_state.setdefault(
                    instance.id,
                    {"record": record, "period_results": {}, "aggregations_created": 0, "errors": []},
                )
                state["period_results"] = period_results
                state["aggregations_created"] = aggregated_count
                state["errors"] = instance_errors

                details = {
                    "aggregations_created": aggregated_count,
                    "aggregation_count": aggregated_count,
                    "periods": period_results,
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
            for period_name in selected_periods:
                period_func = database_period_funcs.get(period_name)
                if not period_func:
                    continue
                try:
                    db_result = period_func()
                except Exception as db_exc:  # pragma: no cover - 防御性日志
                    sync_logger.error(
                        "数据库级聚合执行异常",
                        module="aggregation_sync",
                        period=period_name,
                        error=str(db_exc),
                    )
                    db_result = {
                        "status": "error",
                        "error": str(db_exc),
                        "period_type": period_name,
                    }
                if db_result.get("status") == "success":
                    sync_logger.info(
                        "数据库级聚合完成",
                        module="aggregation_sync",
                        period=period_name,
                        total_records=db_result.get("total_records", 0),
                        processed_instances=db_result.get("processed_instances"),
                    )
                period_summaries.append(db_result)

            total_database_aggregations = sum(
                summary.get("total_records", 0) or summary.get("aggregations_created", 0) or 0
                for summary in period_summaries
            )

            session.successful_instances = successful_instances
            session.failed_instances = failed_instances
            session.status = "completed" if failed_instances == 0 else "failed"
            session.completed_at = time_utils.now()
            db.session.commit()

            message = (
                f"统计聚合完成: 成功 {successful_instances} 个实例，失败 {failed_instances} 个实例"
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
                "success": failed_instances == 0,
                "message": message,
                "aggregations_created": total_instance_aggregations + total_database_aggregations,
                "instance_aggregations_created": total_instance_aggregations,
                "database_aggregations_created": total_database_aggregations,
                "processed_instances": successful_instances + failed_instances,
                "failed_instances": failed_instances,
                "session_id": session.session_id,
                "periods_executed": selected_periods,
                "details": {
                    "periods": period_summaries,
                    "instances": {
                        instance_id: {
                            "aggregations_created": state["aggregations_created"],
                            "errors": state["errors"],
                            "period_results": state["period_results"],
                        }
                        for instance_id, state in instance_state.items()
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
                "success": False,
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
            logger.info(f"开始计算实例 {instance_id} 的统计聚合...")
            
            # 获取实例
            instance = Instance.query.get(instance_id)
            if not instance:
                return {
                    'success': False,
                    'message': f'实例 {instance_id} 不存在'
                }
            
            if not instance.is_active:
                return {
                    'success': False,
                    'message': f'实例 {instance_id} 未激活'
                }
            
            # 创建聚合服务
            service = DatabaseSizeAggregationService()
            
            # 计算实例的聚合数据
            result = service.calculate_instance_aggregations(instance_id)
            
            if result['success']:
                logger.info(f"实例 {instance_id} 统计聚合完成: {result['message']}")
            else:
                logger.error(f"实例 {instance_id} 统计聚合失败: {result['message']}")
            
            return result
            
        except Exception as e:
            logger.error(f"计算实例 {instance_id} 统计聚合失败: {str(e)}")
            return {
                'success': False,
                'message': f'计算实例 {instance_id} 统计聚合失败: {str(e)}',
                'error': str(e)
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
            logger.info(f"开始计算 {period_type} 周期统计聚合 ({start_date} 到 {end_date})...")
            
            # 创建聚合服务
            service = DatabaseSizeAggregationService()
            
            # 计算指定周期的聚合数据
            result = service.calculate_period_aggregations(period_type, start_date, end_date)
            
            if result['success']:
                logger.info(f"{period_type} 周期统计聚合完成: {result['message']}")
            else:
                logger.error(f"{period_type} 周期统计聚合失败: {result['message']}")
            
            return result
            
        except Exception as e:
            logger.error(f"计算 {period_type} 周期统计聚合失败: {str(e)}")
            return {
                'success': False,
                'message': f'计算 {period_type} 周期统计聚合失败: {str(e)}',
                'error': str(e)
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
                'success': True,
                'latest_aggregation': latest_aggregation.calculated_at.isoformat() if latest_aggregation else None,
                'aggregation_counts': {row.period_type: row.count for row in aggregation_counts},
                'total_instances': total_instances,
                'check_date': today.isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取聚合状态失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取聚合状态失败: {str(e)}',
                'error': str(e)
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
        
        return {
            'success': len(config_issues) == 0,
            'message': '聚合配置验证完成',
            'issues': config_issues,
            'config': {
                'enabled': getattr(Config, 'AGGREGATION_ENABLED', True),
                'hour': aggregation_hour
            }
        }
        
    except Exception as e:
        logger.error(f"验证聚合配置失败: {str(e)}")
        return {
            'success': False,
            'message': f'验证聚合配置失败: {str(e)}',
            'error': str(e)
        }


def cleanup_old_aggregations(retention_days: int = 365) -> Dict[str, Any]:
    """
    清理旧的聚合数据
    
    Args:
        retention_days: 保留天数
        
    Returns:
        Dict[str, Any]: 清理结果
    """
    from app import create_app
    
    app = create_app()
    with app.app_context():
        try:
            logger.info(f"开始清理 {retention_days} 天前的聚合数据...")
            
            from app.models.database_size_aggregation import DatabaseSizeAggregation
            
            # 计算清理日期
            cutoff_date = date.today() - timedelta(days=retention_days)
            
            # 删除旧数据
            deleted_count = DatabaseSizeAggregation.query.filter(
                DatabaseSizeAggregation.calculated_at < cutoff_date
            ).delete()
            
            db.session.commit()
            
            logger.info(f"清理了 {deleted_count} 条旧聚合数据")
            
            return {
                'success': True,
                'message': f'清理了 {deleted_count} 条旧聚合数据',
                'deleted_count': deleted_count,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"清理旧聚合数据失败: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'message': f'清理旧聚合数据失败: {str(e)}',
                'error': str(e)
            }
