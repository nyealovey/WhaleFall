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
    from app import create_app
    from app.services.sync_session_service import sync_session_service
    from app.utils.timezone import now
    from app.utils.structlog_config import get_sync_logger
    
    # 创建Flask应用上下文，确保数据库操作正常
    app = create_app()
    with app.app_context():
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
            records = sync_session_service.add_instance_records(session.session_id, instance_ids, sync_category="capacity")
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
                    
                    # 采集数据库大小
                    collection_result = collector.collect_database_sizes()
                    
                    if collection_result['success']:
                        # 更新同步记录 - 容量同步使用数据库数量作为同步数量
                        database_count = len(collection_result.get('databases', []))
                        sync_session_service.complete_instance_sync(
                            record.id,
                            accounts_synced=database_count,  # 使用数据库数量作为同步数量
                            accounts_created=0,  # 容量同步没有新增概念
                            accounts_updated=0,  # 容量同步没有更新概念
                            accounts_deleted=0,  # 容量同步没有删除概念
                            sync_details={
                                'total_size_mb': collection_result.get('total_size_mb', 0),
                                'database_count': database_count,
                                'databases': collection_result.get('databases', [])
                            }
                        )
                        
                        total_synced += 1
                        total_size_mb += collection_result.get('total_size_mb', 0)
                        
                        sync_logger.info(
                            f"实例容量同步成功: {instance.name}",
                            module="capacity_sync",
                            session_id=session.session_id,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            size_mb=collection_result.get('total_size_mb', 0)
                        )
                        
                        results.append({
                            'instance_id': instance.id,
                            'instance_name': instance.name,
                            'success': True,
                            'size_mb': collection_result.get('total_size_mb', 0),
                            'databases': collection_result.get('databases', [])
                        })
                    else:
                        error_msg = collection_result.get('message', '采集失败')
                        sync_logger.error(
                            f"实例容量同步失败: {instance.name} - {error_msg}",
                            module="capacity_sync",
                            session_id=session.session_id,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            error=error_msg
                        )
                        sync_session_service.fail_instance_sync(record.id, error_msg)
                        total_failed += 1
                        results.append({
                            'instance_id': instance.id,
                            'instance_name': instance.name,
                            'success': False,
                            'error': error_msg
                        })
                    
                    # 关闭连接
                    collector.disconnect()
                    
                except Exception as e:
                    error_msg = f"实例同步异常: {str(e)}"
                    sync_logger.error(
                        error_msg,
                        module="capacity_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        exc_info=True
                    )
                    sync_session_service.fail_instance_sync(record.id, error_msg)
                    total_failed += 1
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
    from app import create_app
    from app.services.database_size_collector_service import DatabaseSizeCollectorService
    
    # 创建Flask应用上下文
    app = create_app()
    with app.app_context():
        try:
            logger.info(f"开始采集实例 {instance_id} 的数据库大小...")
            
            # 获取实例信息
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
            
            # 创建采集服务
            collector = DatabaseSizeCollectorService(instance)
            
            # 建立连接
            if not collector.connect():
                return {
                    'success': False,
                    'message': f'无法连接到实例 {instance.name}'
                }
            
            try:
                # 采集数据库大小
                result = collector.collect_database_sizes()
                return result
            finally:
                # 确保关闭连接
                collector.disconnect()
                
        except Exception as e:
            logger.error(f"采集实例 {instance_id} 数据库大小失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'采集失败: {str(e)}',
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
    from app import create_app
    
    # 创建Flask应用上下文
    app = create_app()
    with app.app_context():
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
            logger.error(f"采集 {db_type} 类型数据库大小失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'采集失败: {str(e)}',
                'error': str(e)
            }


def get_collection_status() -> Dict[str, Any]:
    """
    获取数据库大小采集状态
    
    Returns:
        Dict[str, Any]: 采集状态信息
    """
    from app import create_app
    from app.models.instance_size_stat import InstanceSizeStat
    
    # 创建Flask应用上下文
    app = create_app()
    with app.app_context():
        try:
            # 统计采集数据
            total_stats = InstanceSizeStat.query.count()
            recent_stats = InstanceSizeStat.query.filter(
                InstanceSizeStat.created_at >= datetime.now().date()
            ).count()
            
            # 获取最新采集时间
            latest_stat = InstanceSizeStat.query.order_by(
                InstanceSizeStat.created_at.desc()
            ).first()
            
            latest_time = latest_stat.created_at if latest_stat else None
            
            return {
                'success': True,
                'total_records': total_stats,
                'today_records': recent_stats,
                'latest_collection': latest_time.isoformat() if latest_time else None,
                'collection_enabled': getattr(Config, 'COLLECT_DB_SIZE_ENABLED', True)
            }
            
        except Exception as e:
            logger.error(f"获取采集状态失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'获取状态失败: {str(e)}',
                'error': str(e)
            }


def validate_collection_config() -> Dict[str, Any]:
    """
    验证数据库大小采集配置
    
    Returns:
        Dict[str, Any]: 配置验证结果
    """
    try:
        # 检查配置项
        config_checks = {
            'COLLECT_DB_SIZE_ENABLED': getattr(Config, 'COLLECT_DB_SIZE_ENABLED', True),
            'DB_SIZE_COLLECTION_INTERVAL': getattr(Config, 'DB_SIZE_COLLECTION_INTERVAL', 24),
            'DB_SIZE_COLLECTION_TIMEOUT': getattr(Config, 'DB_SIZE_COLLECTION_TIMEOUT', 300)
        }
        
        # 检查服务可用性
        from app.services.database_size_collector_service import DatabaseSizeCollectorService
        service = DatabaseSizeCollectorService()
        
        return {
            'success': True,
            'config': config_checks,
            'service_available': True,
            'message': '配置验证通过'
        }
        
    except Exception as e:
        logger.error(f"配置验证失败: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'配置验证失败: {str(e)}',
            'error': str(e)
        }
