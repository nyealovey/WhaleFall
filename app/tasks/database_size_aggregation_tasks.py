"""
数据库大小统计聚合定时任务
负责计算每周、每月、每季度的统计聚合数据
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from app.services.database_size_aggregation_service import DatabaseSizeAggregationService
from app.models.instance import Instance
from app.config import Config
from app import db

logger = logging.getLogger(__name__)


def calculate_database_size_aggregations():
    """
    计算数据库大小统计聚合
    每天凌晨4点执行，计算周、月、季度统计
    支持会话管理，可在会话中心查看进度
    """
    from app.services.sync_session_service import sync_session_service
    from app.utils.timezone import now
    from app.utils.structlog_config import get_sync_logger
    
    sync_logger = get_sync_logger()
    
    try:
        sync_logger.info("开始执行数据库大小统计聚合任务", module="aggregation_sync")
        
        # 检查聚合功能是否启用
        if not getattr(Config, 'AGGREGATION_ENABLED', True):
            sync_logger.info("数据库大小统计聚合功能已禁用", module="aggregation_sync")
            return {
                'success': True,
                'message': '统计聚合功能已禁用',
                'aggregations_created': 0
            }
        
        # 获取所有活跃的实例
        active_instances = Instance.query.filter_by(is_active=True).all()
        
        if not active_instances:
            sync_logger.warning("没有找到活跃的数据库实例", module="aggregation_sync")
            return {
                'success': True,
                'message': '没有活跃的数据库实例需要聚合',
                'aggregations_created': 0
            }
        
        sync_logger.info(
            "找到活跃实例，开始统计聚合",
            module="aggregation_sync",
            instance_count=len(active_instances)
        )
        
        # 创建同步会话
        session = sync_session_service.create_session(
            sync_type="scheduled_task",
            sync_category="aggregation",
            created_by=None  # 定时任务没有创建者
        )
        
        sync_logger.info(
            "创建统计聚合会话",
            module="aggregation_sync",
            session_id=session.session_id,
            instance_count=len(active_instances)
        )
        
        # 添加实例记录
        instance_ids = [inst.id for inst in active_instances]
        records = sync_session_service.add_instance_records(session.session_id, instance_ids)
        session.total_instances = len(active_instances)
        
        total_processed = 0
        total_failed = 0
        total_aggregations = 0
        results = []
        
        # 创建聚合服务
        service = DatabaseSizeAggregationService()
        
        # 按周期类型计算聚合
        period_types = ['daily', 'weekly', 'monthly', 'quarterly']
        
        for period_type in period_types:
            try:
                sync_logger.info(
                    f"开始计算 {period_type} 周期聚合",
                    module="aggregation_sync",
                    session_id=session.session_id,
                    period_type=period_type
                )
                
                # 计算该周期的聚合数据
                if period_type == 'daily':
                    period_result = service.calculate_daily_aggregations()
                elif period_type == 'weekly':
                    period_result = service.calculate_weekly_aggregations()
                elif period_type == 'monthly':
                    period_result = service.calculate_monthly_aggregations()
                elif period_type == 'quarterly':
                    period_result = service.calculate_quarterly_aggregations()
                else:
                    continue
                
                # 更新实例记录状态 - 基于聚合服务的实际结果
                if period_result.get('status') == 'success':
                    # 聚合服务调用成功，更新所有实例记录为成功
                    for i, instance in enumerate(active_instances):
                        record = records[i] if i < len(records) else None
                        if record:
                            try:
                                sync_session_service.start_instance_sync(record.id)
                                
                                sync_logger.info(
                                    f"处理实例聚合: {instance.name} ({period_type})",
                                    module="aggregation_sync",
                                    session_id=session.session_id,
                                    instance_id=instance.id,
                                    instance_name=instance.name,
                                    period_type=period_type
                                )
                                
                                sync_session_service.complete_instance_sync(
                                    record.id, 
                                    success=True,
                                    sync_details={
                                        'period_type': period_type,
                                        'aggregations_created': period_result.get('total_records', 0),
                                        'processed_instances': period_result.get('processed_instances', 0)
                                    }
                                )
                                
                                total_processed += 1
                                
                            except Exception as e:
                                sync_logger.error(
                                    f"更新实例记录失败: {instance.name} ({period_type})",
                                    module="aggregation_sync",
                                    session_id=session.session_id,
                                    instance_id=instance.id,
                                    instance_name=instance.name,
                                    period_type=period_type,
                                    error=str(e)
                                )
                                
                                sync_session_service.complete_instance_sync(
                                    record.id, 
                                    success=False,
                                    error_message=str(e)
                                )
                                
                                total_failed += 1
                else:
                    # 聚合服务调用失败，更新所有实例记录为失败
                    error_msg = period_result.get('error', '未知错误')
                    for i, instance in enumerate(active_instances):
                        record = records[i] if i < len(records) else None
                        if record:
                            try:
                                sync_session_service.start_instance_sync(record.id)
                                
                                sync_logger.error(
                                    f"处理实例聚合失败: {instance.name} ({period_type}) - {error_msg}",
                                    module="aggregation_sync",
                                    session_id=session.session_id,
                                    instance_id=instance.id,
                                    instance_name=instance.name,
                                    period_type=period_type,
                                    error=error_msg
                                )
                                
                                sync_session_service.complete_instance_sync(
                                    record.id, 
                                    success=False,
                                    error_message=error_msg
                                )
                                
                                total_failed += 1
                                
                            except Exception as e:
                                sync_logger.error(
                                    f"更新实例记录失败: {instance.name} ({period_type})",
                                    module="aggregation_sync",
                                    session_id=session.session_id,
                                    instance_id=instance.id,
                                    instance_name=instance.name,
                                    period_type=period_type,
                                    error=str(e)
                                )
                                
                                sync_session_service.complete_instance_sync(
                                    record.id, 
                                    success=False,
                                    error_message=str(e)
                                )
                                
                                total_failed += 1
                
                # 累计聚合结果
                if period_result.get('status') == 'success':
                    total_aggregations += period_result.get('total_records', 0)
                results.append({
                    'period_type': period_type,
                    'result': period_result
                })
                
                if period_result.get('status') == 'success':
                    sync_logger.info(
                        f"{period_type} 周期聚合完成",
                        module="aggregation_sync",
                        session_id=session.session_id,
                        period_type=period_type,
                        aggregations_created=period_result.get('total_records', 0)
                    )
                else:
                    sync_logger.error(
                        f"{period_type} 周期聚合失败",
                        module="aggregation_sync",
                        session_id=session.session_id,
                        period_type=period_type,
                        error=period_result.get('error', '未知错误')
                    )
                
            except Exception as e:
                sync_logger.error(
                    f"计算 {period_type} 周期聚合失败",
                    module="aggregation_sync",
                    session_id=session.session_id,
                    period_type=period_type,
                    error=str(e)
                )
                total_failed += 1
                continue
        
        # 更新会话状态
        session.successful_instances = total_processed
        session.failed_instances = total_failed
        session.status = "completed" if total_failed == 0 else "failed"
        session.completed_at = now()
        db.session.commit()
        
        sync_logger.info(
            "统计聚合任务完成",
            module="aggregation_sync",
            session_id=session.session_id,
            total_processed=total_processed,
            total_failed=total_failed,
            total_aggregations=total_aggregations
        )
        
        return {
            'success': True,
            'message': f'统计聚合计算完成，处理了 {total_processed} 个实例，创建了 {total_aggregations} 个聚合记录',
            'aggregations_created': total_aggregations,
            'processed_instances': total_processed,
            'failed_instances': total_failed,
            'session_id': session.session_id,
            'details': results
        }
        
    except Exception as e:
        sync_logger.error(
            "数据库大小统计聚合任务执行失败",
            module="aggregation_sync",
            error=str(e)
        )
        
        # 如果创建了会话，更新其状态为失败
        try:
            if 'session' in locals():
                session.status = "failed"
                session.completed_at = now()
                db.session.commit()
        except:
            pass
        
        return {
            'success': False,
            'message': f'数据库大小统计聚合任务执行失败: {str(e)}',
            'error': str(e)
        }


def calculate_instance_aggregations(instance_id: int) -> Dict[str, Any]:
    """
    计算指定实例的统计聚合
    
    Args:
        instance_id: 实例ID
        
    Returns:
        Dict[str, Any]: 聚合结果
    """
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
