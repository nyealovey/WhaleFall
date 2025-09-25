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
    采集所有数据库实例的大小信息
    每天凌晨3点执行，采集所有活跃实例的数据库大小
    """
    try:
        logger.info("开始执行数据库大小采集任务...")
        
        # 获取所有活跃的实例
        active_instances = Instance.query.filter_by(is_active=True).all()
        
        if not active_instances:
            logger.warning("没有找到活跃的数据库实例")
            return {
                'success': True,
                'message': '没有活跃的数据库实例需要采集',
                'instances_processed': 0,
                'total_size_mb': 0
            }
        
        logger.info(f"找到 {len(active_instances)} 个活跃实例，开始采集...")
        
        # 调用采集服务
        result = collect_all_instances_database_sizes()
        
        if result['success']:
            logger.info(f"数据库大小采集完成: {result['message']}")
            logger.info(f"处理实例数: {result['instances_processed']}")
            logger.info(f"总大小: {result['total_size_mb']} MB")
        else:
            logger.error(f"数据库大小采集失败: {result['message']}")
        
        return result
        
    except Exception as e:
        logger.error(f"数据库大小采集任务执行失败: {str(e)}")
        return {
            'success': False,
            'message': f'数据库大小采集任务执行失败: {str(e)}',
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
