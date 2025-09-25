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
    """
    try:
        logger.info("开始执行数据库大小统计聚合任务...")
        
        # 检查聚合功能是否启用
        if not getattr(Config, 'AGGREGATION_ENABLED', True):
            logger.info("数据库大小统计聚合功能已禁用")
            return {
                'success': True,
                'message': '统计聚合功能已禁用',
                'aggregations_created': 0
            }
        
        # 获取所有活跃的实例
        active_instances = Instance.query.filter_by(is_active=True).all()
        
        if not active_instances:
            logger.warning("没有找到活跃的数据库实例")
            return {
                'success': True,
                'message': '没有活跃的数据库实例需要聚合',
                'aggregations_created': 0
            }
        
        logger.info(f"找到 {len(active_instances)} 个活跃实例，开始计算聚合...")
        
        # 创建聚合服务
        service = DatabaseSizeAggregationService()
        
        # 计算所有实例的聚合数据
        result = service.calculate_all_aggregations()
        
        if result['success']:
            logger.info(f"数据库大小统计聚合完成: {result['message']}")
            logger.info(f"创建聚合记录数: {result['aggregations_created']}")
        else:
            logger.error(f"数据库大小统计聚合失败: {result['message']}")
        
        return result
        
    except Exception as e:
        logger.error(f"数据库大小统计聚合任务执行失败: {str(e)}")
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
