"""
数据库大小采集定时任务
负责每日自动采集所有数据库实例的大小信息
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, List
from app.services.database_size_collector_service import collect_all_instances_database_sizes
from app.models.instance import Instance
from app.config import Config
from app import db

logger = logging.getLogger(__name__)


def collect_database_sizes():
    """
    容量同步定时任务
    每天凌晨3点执行，同步所有活跃实例的数据库容量信息
    """
    from app.services.sync_session_service import sync_session_service
    from app.utils.timezone import now
    from app.utils.structlog_config import get_sync_logger
    
    sync_logger = get_sync_logger()
    
    try:
        sync_logger.info("开始容量同步任务", module="capacity_sync")
        
        # 获取所有活跃的实例
        active_instances = Instance.query.filter_by(is_active=True).all()
        
        if not active_instances:
            sync_logger.warning("没有找到活跃的数据库实例", module="capacity_sync")
            return {
                'success': True,
                'message': '没有活跃的数据库实例需要同步',
                'instances_processed': 0,
                'total_size_mb': 0
            }
        
        sync_logger.info(
            "找到活跃实例，开始容量同步",
            module="capacity_sync",
            instance_count=len(active_instances)
        )
        
        # 创建同步会话
        session = sync_session_service.create_session(
            sync_type="scheduled_task",
            sync_category="capacity",
            created_by=None  # 定时任务没有创建者
        )
        
        sync_logger.info(
            "创建容量同步会话",
            module="capacity_sync",
            session_id=session.session_id,
            instance_count=len(active_instances)
        )
        
        # 添加实例记录
        instance_ids = [inst.id for inst in active_instances]
        records = sync_session_service.add_instance_records(session.session_id, instance_ids)
        session.total_instances = len(active_instances)
        
        total_synced = 0
        total_failed = 0
        total_size_mb = 0
        results = []
        
        for i, instance in enumerate(active_instances):
            # 找到对应的记录
            record = records[i] if i < len(records) else None
            if not record:
                continue
            
            try:
                # 开始实例同步
                sync_session_service.start_instance_sync(record.id)
                
                sync_logger.info(
                    f"开始同步实例容量: {instance.name}",
                    module="capacity_sync",
                    session_id=session.session_id,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    db_type=instance.db_type
                )
                
                # 调用数据库大小采集服务
                from app.services.database_size_collector_service import DatabaseSizeCollectorService
                
                collector = DatabaseSizeCollectorService(instance)
                
                # 建立连接
                if not collector.connect():
                    error_msg = f"无法连接到实例 {instance.name}"
                    sync_logger.error(
                        error_msg,
                        module="capacity_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        instance_name=instance.name
                    )
                    sync_session_service.fail_instance_sync(record.id, error_msg)
                    total_failed += 1
                    results.append({
                        'instance_id': instance.id,
                        'instance_name': instance.name,
                        'success': False,
                        'error': error_msg
                    })
                    continue
                
                try:
                    # 采集并保存数据库大小数据（包括实例大小统计）
                    saved_count = collector.collect_and_save()
                    
                    # 从实例大小统计表获取总大小
                    from app.models.instance_size_stat import InstanceSizeStat
                    latest_stat = InstanceSizeStat.query.filter(
                        InstanceSizeStat.instance_id == instance.id,
                        InstanceSizeStat.is_deleted == False
                    ).order_by(InstanceSizeStat.collected_date.desc()).first()
                    
                    if not latest_stat:
                        error_msg = f"实例 {instance.name} 没有找到任何数据库"
                        sync_logger.warning(
                            error_msg,
                            module="capacity_sync",
                            session_id=session.session_id,
                            instance_id=instance.id,
                            instance_name=instance.name
                        )
                        sync_session_service.fail_instance_sync(record.id, error_msg)
                        total_failed += 1
                        results.append({
                            'instance_id': instance.id,
                            'instance_name': instance.name,
                            'success': False,
                            'error': error_msg
                        })
                        continue
                    
                    instance_size_mb = latest_stat.total_size_mb
                    database_count = latest_stat.database_count
                    total_size_mb += instance_size_mb
                    
                    # 更新实例的最后连接时间
                    instance.last_connected = now()
                    
                    # 完成实例同步
                    sync_session_service.complete_instance_sync(
                        record.id,
                        accounts_synced=database_count,  # 使用数据库数量作为同步数量
                        accounts_created=saved_count,  # 新创建的记录数
                        accounts_updated=0,  # 容量同步没有更新概念
                        accounts_deleted=0,  # 容量同步没有删除概念
                        sync_details={
                            'databases_count': database_count,
                            'saved_count': saved_count,
                            'total_size_mb': instance_size_mb
                        }
                    )
                    
                    total_synced += 1
                    results.append({
                        'instance_id': instance.id,
                        'instance_name': instance.name,
                        'success': True,
                        'databases_count': database_count,
                        'saved_count': saved_count,
                        'total_size_mb': instance_size_mb
                    })
                    
                    sync_logger.info(
                        f"实例 {instance.name} 容量同步完成",
                        module="capacity_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        databases_count=database_count,
                        saved_count=saved_count,
                        total_size_mb=instance_size_mb
                    )
                    
                finally:
                    # 确保断开连接
                    collector.disconnect()
                    
            except Exception as e:
                total_failed += 1
                sync_logger.error(
                    f"实例 {instance.name} 容量同步失败",
                    module="capacity_sync",
                    session_id=session.session_id,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    error=str(e),
                    exc_info=True
                )
                
                # 标记实例同步失败
                if 'record' in locals() and record:
                    sync_session_service.fail_instance_sync(record.id, str(e))
                
                results.append({
                    'instance_id': instance.id,
                    'instance_name': instance.name,
                    'success': False,
                    'error': str(e)
                })
        
        # 更新会话状态
        session.successful_instances = total_synced
        session.failed_instances = total_failed
        session.status = "completed" if total_failed == 0 else "failed"
        session.completed_at = now()
        db.session.commit()
        
        result = {
            'success': total_failed == 0,
            'message': f'容量同步完成: 成功 {total_synced} 个，失败 {total_failed} 个',
            'instances_processed': total_synced,
            'total_size_mb': total_size_mb,
            'session_id': session.session_id,
            'details': results
        }
        
        sync_logger.info(
            "容量同步任务完成",
            module="capacity_sync",
            session_id=session.session_id,
            total_instances=len(active_instances),
            successful_instances=total_synced,
            failed_instances=total_failed,
            total_size_mb=total_size_mb
        )
        
        return result
        
    except Exception as e:
        sync_logger.error(
            "容量同步任务执行失败",
            module="capacity_sync",
            error=str(e),
            exc_info=True
        )
        
        # 更新会话状态为失败
        if 'session' in locals() and session:
            session.status = "failed"
            session.completed_at = now()
            session.failed_instances = len(active_instances) if 'active_instances' in locals() else 0
            db.session.commit()
        
        return {
            'success': False,
            'message': f'容量同步任务执行失败: {str(e)}',
            'error': str(e)
        }


def collect_specific_instance_database_sizes(instance_id: int) -> Dict[str, Any]:
    """
    采集指定实例的数据库大小信息
    
    Args:
        instance_id: 实例ID
        
    Returns:
        Dict[str, Any]: 采集结果
    """
    try:
        logger.info(f"开始采集实例 {instance_id} 的数据库大小...")
        
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
        
        # 调用采集服务
        from app.services.database_size_collector_service import DatabaseSizeCollectorService
        service = DatabaseSizeCollectorService()
        
        result = service.collect_instance_database_sizes(instance_id)
        
        if result['success']:
            logger.info(f"实例 {instance_id} 数据库大小采集完成: {result['message']}")
        else:
            logger.error(f"实例 {instance_id} 数据库大小采集失败: {result['message']}")
        
        return result
        
    except Exception as e:
        logger.error(f"采集实例 {instance_id} 数据库大小失败: {str(e)}")
        return {
            'success': False,
            'message': f'采集实例 {instance_id} 数据库大小失败: {str(e)}',
            'error': str(e)
        }


def collect_database_sizes_by_type(db_type: str) -> Dict[str, Any]:
    """
    采集指定类型数据库的大小信息
    
    Args:
        db_type: 数据库类型 (mysql, sqlserver, postgresql, oracle)
        
    Returns:
        Dict[str, Any]: 采集结果
    """
    try:
        logger.info(f"开始采集 {db_type} 类型数据库的大小...")
        
        # 获取指定类型的活跃实例
        instances = Instance.query.filter_by(
            db_type=db_type,
            is_active=True
        ).all()
        
        if not instances:
            return {
                'success': True,
                'message': f'没有找到 {db_type} 类型的活跃实例',
                'instances_processed': 0
            }
        
        logger.info(f"找到 {len(instances)} 个 {db_type} 类型实例")
        
        # 调用采集服务
        from app.services.database_size_collector_service import DatabaseSizeCollectorService
        service = DatabaseSizeCollectorService()
        
        total_processed = 0
        total_size_mb = 0
        errors = []
        
        for instance in instances:
            try:
                result = service.collect_instance_database_sizes(instance.id)
                if result['success']:
                    total_processed += 1
                    total_size_mb += result.get('total_size_mb', 0)
                else:
                    errors.append(f"实例 {instance.name}: {result['message']}")
            except Exception as e:
                errors.append(f"实例 {instance.name}: {str(e)}")
        
        return {
            'success': True,
            'message': f'{db_type} 类型数据库大小采集完成',
            'instances_processed': total_processed,
            'total_size_mb': total_size_mb,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"采集 {db_type} 类型数据库大小失败: {str(e)}")
        return {
            'success': False,
            'message': f'采集 {db_type} 类型数据库大小失败: {str(e)}',
            'error': str(e)
        }


def get_collection_status() -> Dict[str, Any]:
    """
    获取采集状态信息
    
    Returns:
        Dict[str, Any]: 状态信息
    """
    try:
        from app.models.database_size_stat import DatabaseSizeStat
        from sqlalchemy import func, desc
        
        # 获取今日采集统计
        today = date.today()
        today_stats = DatabaseSizeStat.query.filter_by(collected_date=today).all()
        
        # 获取最近采集时间
        latest_collection = DatabaseSizeStat.query.order_by(
            desc(DatabaseSizeStat.collected_at)
        ).first()
        
        # 获取总实例数
        total_instances = Instance.query.filter_by(is_active=True).count()
        
        # 获取各数据库类型的实例数
        from sqlalchemy import func
        instance_counts = db.session.query(
            Instance.db_type,
            func.count(Instance.id).label('count')
        ).filter_by(is_active=True).group_by(Instance.db_type).all()
        
        return {
            'success': True,
            'today_collected': len(today_stats),
            'total_instances': total_instances,
            'latest_collection': latest_collection.collected_at.isoformat() if latest_collection else None,
            'instance_counts': {row.db_type: row.count for row in instance_counts},
            'collection_date': today.isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取采集状态失败: {str(e)}")
        return {
            'success': False,
            'message': f'获取采集状态失败: {str(e)}',
            'error': str(e)
        }


def validate_collection_config() -> Dict[str, Any]:
    """
    验证采集配置
    
    Returns:
        Dict[str, Any]: 验证结果
    """
    try:
        config_issues = []
        
        # 检查采集是否启用
        if not getattr(Config, 'COLLECT_DB_SIZE_ENABLED', True):
            config_issues.append("数据库大小采集已禁用")
        
        # 检查超时配置
        timeout = getattr(Config, 'DB_SIZE_COLLECT_TIMEOUT', 30)
        if timeout < 10:
            config_issues.append("采集超时时间过短，建议至少10秒")
        
        # 检查批次大小
        batch_size = getattr(Config, 'DB_SIZE_COLLECT_BATCH_SIZE', 10)
        if batch_size < 1:
            config_issues.append("采集批次大小无效")
        
        # 检查重试次数
        retry_count = getattr(Config, 'DB_SIZE_COLLECT_RETRY_COUNT', 3)
        if retry_count < 0:
            config_issues.append("重试次数不能为负数")
        
        return {
            'success': len(config_issues) == 0,
            'message': '配置验证完成',
            'issues': config_issues,
            'config': {
                'enabled': getattr(Config, 'COLLECT_DB_SIZE_ENABLED', True),
                'timeout': timeout,
                'batch_size': batch_size,
                'retry_count': retry_count
            }
        }
        
    except Exception as e:
        logger.error(f"验证采集配置失败: {str(e)}")
        return {
            'success': False,
            'message': f'验证采集配置失败: {str(e)}',
            'error': str(e)
        }
