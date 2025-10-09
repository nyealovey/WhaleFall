"""
数据库大小统计聚合定时任务
负责计算每周、每月、每季度的统计聚合数据
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from app.constants.sync_constants import SyncOperationType, SyncCategory
from app.services.database_size_aggregation_service import DatabaseSizeAggregationService
from app.models.instance import Instance
from app.config import Config
from app import db

logger = logging.getLogger(__name__)


def calculate_database_size_aggregations(manual_run=False):
    """
    计算数据库大小统计聚合
    每天凌晨4点执行，计算周、月、季度统计
    支持会话管理，可在会话中心查看进度
    
    Args:
        manual_run: 是否手动执行，手动执行时不创建会话
    """
    from app import create_app
    from app.services.sync_session_service import sync_session_service
    from app.utils.time_utils import time_utils
    from app.utils.structlog_config import get_sync_logger
    
    # 创建Flask应用上下文，确保数据库操作正常
    app = create_app()
    with app.app_context():
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
            
            # 创建同步会话（手动执行和定时任务都创建会话）
            if manual_run:
                # 手动执行时创建会话，created_by为当前用户
                from flask_login import current_user
                created_by = current_user.id if current_user.is_authenticated else None
                session = sync_session_service.create_session(
                    sync_type=SyncOperationType.MANUAL_TASK.value,
                    sync_category=SyncCategory.AGGREGATION.value,
                    created_by=created_by
                )
                
                sync_logger.info(
                    "创建手动统计聚合会话",
                    module="aggregation_sync",
                    session_id=session.session_id,
                    instance_count=len(active_instances),
                    created_by=created_by
                )
            else:
                # 定时任务执行时创建会话
                session = sync_session_service.create_session(
                    sync_type=SyncOperationType.SCHEDULED_TASK.value,
                    sync_category=SyncCategory.AGGREGATION.value,
                    created_by=None  # 定时任务没有创建者
                )
                
                sync_logger.info(
                    "创建定时统计聚合会话",
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
            total_instance_aggregations = 0
            total_database_aggregations = 0
            results = []
            
            # 创建聚合服务
            service = DatabaseSizeAggregationService()
            
            # 定义周期类型列表
            period_types = ['daily', 'weekly', 'monthly', 'quarterly']

            # 关键字集合，用于识别“无数据”类提示
            no_data_keywords = ['没有数据', '没有统计数据', '无数据', '无统计数据', 'no data', 'data not found']

            # 先执行数据库（库级）聚合，确保库级数据分区表有内容
            for period_type in period_types:
                try:
                    if period_type == 'daily':
                        agg_result = service.calculate_daily_aggregations()
                    elif period_type == 'weekly':
                        agg_result = service.calculate_weekly_aggregations()
                    elif period_type == 'monthly':
                        agg_result = service.calculate_monthly_aggregations()
                    elif period_type == 'quarterly':
                        agg_result = service.calculate_quarterly_aggregations()
                    else:
                        continue

                    status = agg_result.get('status')
                    error_message = str(agg_result.get('error', '') or '').strip()
                    skipped_due_to_no_data = False
                    if status != 'success' and error_message:
                        if any(keyword in error_message for keyword in no_data_keywords):
                            skipped_due_to_no_data = True

                    if status == 'success' or skipped_due_to_no_data:
                        created_records = agg_result.get('total_records', 0)
                        total_database_aggregations += created_records
                        results.append({
                            'scope': 'database',
                            'period_type': period_type,
                            'status': 'success',
                            'created_records': created_records,
                            'message': agg_result.get('message') or error_message or ''
                        })
                        if created_records > 0:
                            sync_logger.info(
                                f"数据库聚合完成: {period_type}",
                                module="aggregation_sync",
                                period_type=period_type,
                                created_records=created_records
                            )
                        else:
                            sync_logger.info(
                                f"数据库聚合跳过（无数据）: {period_type}",
                                module="aggregation_sync",
                                period_type=period_type,
                                message=agg_result.get('message', error_message or '没有统计数据')
                            )
                    else:
                        results.append({
                            'scope': 'database',
                            'period_type': period_type,
                            'status': 'error',
                            'created_records': 0,
                            'message': error_message or '未知错误'
                        })
                        sync_logger.error(
                            f"数据库聚合失败: {period_type}",
                            module="aggregation_sync",
                            period_type=period_type,
                            error=error_message or '未知错误'
                        )
                except Exception as e:
                    results.append({
                        'scope': 'database',
                        'period_type': period_type,
                        'status': 'exception',
                        'created_records': 0,
                        'message': str(e)
                    })
                    sync_logger.error(
                        f"数据库聚合异常: {period_type}",
                        module="aggregation_sync",
                        period_type=period_type,
                        error=str(e)
                    )
            
            # 按实例逐个处理聚合任务（移除全局聚合循环，避免重复计算）
            for i, instance in enumerate(active_instances):
                record = records[i] if i < len(records) else None
                if not record:
                    continue
                    
                try:
                    # 开始实例同步
                    sync_session_service.start_instance_sync(record.id)
                    
                    # 为当前实例执行聚合计算（使用连接工厂的超时机制）
                    instance_aggregations = 0
                    instance_success = True
                    instance_error_msg = ""
                    
                    # 使用连接工厂创建数据库连接，设置超时参数
                    from app.services.connection_factory import ConnectionFactory
                    import time
                    
                    # 移除signal超时控制，依赖连接工厂的超时机制
                    try:
                        
                        for period_type in period_types:
                            try:
                                # 为当前实例计算该周期的聚合数据
                                if period_type == 'daily':
                                    period_result = service.calculate_daily_aggregations_for_instance(instance.id)
                                elif period_type == 'weekly':
                                    period_result = service.calculate_weekly_aggregations_for_instance(instance.id)
                                elif period_type == 'monthly':
                                    period_result = service.calculate_monthly_aggregations_for_instance(instance.id)
                                elif period_type == 'quarterly':
                                    period_result = service.calculate_quarterly_aggregations_for_instance(instance.id)
                                else:
                                    continue
                            
                                status = period_result.get('status')
                                is_success = status == 'success'
                                error_message = str(period_result.get('error', '') or '').strip()
                                skipped_due_to_no_data = False
                                
                                # 如果服务以异常形式返回“无数据”提示，也视为成功
                                if not is_success and error_message:
                                    if any(keyword in error_message for keyword in no_data_keywords):
                                        skipped_due_to_no_data = True
                                
                                if is_success or skipped_due_to_no_data:
                                    instance_aggregations += period_result.get('total_records', 0)
                                    # 记录日志，区分有数据和无数据的情况
                                    if period_result.get('total_records', 0) > 0:
                                        sync_logger.info(
                                            f"实例 {instance.name} {period_type} 聚合完成",
                                            module="aggregation_sync",
                                            session_id=session.session_id,
                                            instance_id=instance.id,
                                            instance_name=instance.name,
                                            period_type=period_type,
                                            aggregations=period_result.get('total_records', 0)
                                        )
                                    else:
                                        # 没有数据的情况，记录为信息级别
                                        sync_logger.info(
                                            f"实例 {instance.name} {period_type} 聚合跳过（无数据）",
                                            module="aggregation_sync",
                                            session_id=session.session_id,
                                            instance_id=instance.id,
                                            instance_name=instance.name,
                                            period_type=period_type,
                                            message=period_result.get('message', error_message or '没有统计数据')
                                        )
                                else:
                                    instance_success = False
                                    instance_error_msg += f"{period_type}聚合失败; "
                                    sync_logger.error(
                                        f"实例 {instance.name} {period_type} 聚合失败",
                                        module="aggregation_sync",
                                        session_id=session.session_id,
                                        instance_id=instance.id,
                                        instance_name=instance.name,
                                        period_type=period_type,
                                        error=period_result.get('error', '未知错误')
                                    )
                                    
                            except Exception as e:
                                instance_success = False
                                instance_error_msg += f"{period_type}聚合异常: {str(e)}; "
                                sync_logger.error(
                                    f"实例 {instance.name} {period_type} 聚合异常",
                                    module="aggregation_sync",
                                    session_id=session.session_id,
                                    instance_id=instance.id,
                                    instance_name=instance.name,
                                    period_type=period_type,
                                    error=str(e)
                                )
                    
                        # 根据实例聚合结果更新记录状态
                        if instance_success:
                            # 实例聚合成功
                            sync_session_service.complete_instance_sync(
                                record.id,
                                items_synced=instance_aggregations,  # 使用实际聚合数量
                                items_created=0,
                                items_updated=0,
                                items_deleted=0,
                                sync_details={
                                    'total_aggregations': instance_aggregations,
                                    'periods_processed': len(period_types),
                                    'instance_id': instance.id,
                                    'instance_name': instance.name
                                }
                            )
                            total_processed += 1
                            total_instance_aggregations += instance_aggregations
                            
                            sync_logger.info(
                                f"实例聚合完成: {instance.name}",
                                module="aggregation_sync",
                                session_id=session.session_id,
                                instance_id=instance.id,
                                instance_name=instance.name,
                                aggregations=instance_aggregations
                            )
                        else:
                            # 实例聚合失败
                            error_msg = f"聚合失败，失败的周期: {instance_error_msg.strip()}"
                            sync_session_service.fail_instance_sync(
                                record.id,
                                error_message=error_msg
                            )
                            total_failed += 1
                            
                            sync_logger.error(
                                f"实例聚合失败: {instance.name}",
                                module="aggregation_sync",
                                session_id=session.session_id,
                                instance_id=instance.id,
                                instance_name=instance.name,
                                error=error_msg
                            )
                    
                    except TimeoutError as e:
                        # 超时异常处理
                        sync_logger.error(
                            f"实例聚合超时: {instance.name}",
                            module="aggregation_sync",
                            session_id=session.session_id,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            error=str(e)
                        )
                        sync_session_service.fail_instance_sync(
                            record.id,
                            error_message=f"聚合计算超时: {str(e)}"
                        )
                        total_failed += 1
                        
                    except Exception as e:
                        # 连接或聚合异常处理
                        sync_logger.error(
                            f"实例聚合异常: {instance.name}",
                            module="aggregation_sync",
                            session_id=session.session_id,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            error=str(e)
                        )
                        sync_session_service.fail_instance_sync(
                            record.id,
                            error_message=f"聚合计算异常: {str(e)}"
                        )
                        total_failed += 1
                    
                    finally:
                        # 清理工作（移除signal相关代码）
                        pass
                
                except Exception as e:
                    sync_logger.error(
                        f"处理实例聚合失败: {instance.name}",
                        module="aggregation_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        error=str(e)
                    )
                    sync_session_service.fail_instance_sync(
                        record.id,
                        error_message=f"处理聚合异常: {str(e)}"
                    )
                    total_failed += 1
            
            # 会话状态已通过 _update_session_statistics 实时更新，这里不需要手动更新
            # 只需要确保会话最终状态正确
            if session.status == "running":
                # 如果会话状态还是running，说明所有实例都已完成，更新最终状态
                session.status = "completed" if total_failed == 0 else "failed"
                session.completed_at = time_utils.now()
                db.session.commit()
            
            sync_logger.info(
                "统计聚合任务完成",
                module="aggregation_sync",
                session_id=session.session_id,
                total_processed=total_processed,
                total_failed=total_failed,
                total_aggregations=total_instance_aggregations + total_database_aggregations,
                manual_run=manual_run
            )
            
            total_aggregations_created = total_instance_aggregations + total_database_aggregations
            return {
                'success': True,
                'message': (
                    f'统计聚合计算完成，处理了 {total_processed} 个实例，'
                    f'创建了 {total_aggregations_created} 个聚合记录'
                ),
                'aggregations_created': total_aggregations_created,
                'instance_aggregations_created': total_instance_aggregations,
                'database_aggregations_created': total_database_aggregations,
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
                    session.completed_at = time_utils.now()
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
