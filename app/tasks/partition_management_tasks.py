"""
分区管理定时任务
负责自动创建、清理和监控数据库大小统计表的分区
"""

import logging
from datetime import datetime, date, timedelta
from app.services.partition_management_service import PartitionManagementService
from app.config import Config

logger = logging.getLogger(__name__)


def create_database_size_partitions():
    """
    创建数据库大小统计表的分区
    每天凌晨2点执行，创建未来3个月的分区
    """
    try:
        logger.info("开始创建数据库大小统计表分区...")
        
        service = PartitionManagementService()
        
        # 创建未来3个月的分区
        result = service.create_future_partitions(months_ahead=3)
        
        if result['success']:
            logger.info(f"分区创建完成: {result['message']}")
        else:
            logger.error(f"分区创建失败: {result['message']}")
        
        return result
        
    except Exception as e:
        logger.error(f"创建分区任务执行失败: {str(e)}")
        return {
            'success': False,
            'message': f'创建分区任务执行失败: {str(e)}',
            'error': str(e)
        }


def cleanup_database_size_partitions():
    """
    清理数据库大小统计表的旧分区
    每天凌晨3点执行，清理12个月前的分区
    """
    try:
        logger.info("开始清理数据库大小统计表旧分区...")
        
        service = PartitionManagementService()
        
        # 获取保留月数配置
        retention_months = getattr(Config, 'DATABASE_SIZE_RETENTION_MONTHS', 12)
        
        # 清理旧分区
        result = service.cleanup_old_partitions(retention_months=retention_months)
        
        if result['success']:
            logger.info(f"分区清理完成: {result['message']}")
        else:
            logger.error(f"分区清理失败: {result['message']}")
        
        return result
        
    except Exception as e:
        logger.error(f"清理分区任务执行失败: {str(e)}")
        return {
            'success': False,
            'message': f'清理分区任务执行失败: {str(e)}',
            'error': str(e)
        }


def monitor_partition_health():
    """
    监控分区健康状态
    每小时执行一次，检查分区状态和性能
    """
    try:
        logger.info("开始监控分区健康状态...")
        
        service = PartitionManagementService()
        
        # 获取分区信息
        partition_info = service.get_partition_info()
        
        if not partition_info['success']:
            logger.error(f"获取分区信息失败: {partition_info['message']}")
            return partition_info
        
        # 获取分区统计
        stats = service.get_partition_statistics()
        
        if not stats['success']:
            logger.error(f"获取分区统计失败: {stats['message']}")
            return stats
        
        # 记录分区状态
        logger.info(f"分区监控完成: 总分区数={stats['total_partitions']}, "
                   f"总大小={stats['total_size']}, 总记录数={stats['total_records']}")
        
        # 检查是否需要创建新分区
        current_date = date.today()
        next_month = current_date.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        
        # 检查下个月的分区是否存在
        partition_name = f"database_size_stats_{next_month.strftime('%Y_%m')}"
        if not service._partition_exists(partition_name):
            logger.warning(f"下个月分区 {partition_name} 不存在，尝试创建...")
            create_result = service.create_partition(next_month)
            if create_result['success']:
                logger.info(f"成功创建下个月分区: {create_result['message']}")
            else:
                logger.error(f"创建下个月分区失败: {create_result['message']}")
        
        return {
            'success': True,
            'message': '分区健康监控完成',
            'partition_count': stats['total_partitions'],
            'total_size': stats['total_size'],
            'total_records': stats['total_records']
        }
        
    except Exception as e:
        logger.error(f"分区健康监控任务执行失败: {str(e)}")
        return {
            'success': False,
            'message': f'分区健康监控任务执行失败: {str(e)}',
            'error': str(e)
        }


def get_partition_management_status():
    """
    获取分区管理状态
    用于API接口和监控页面
    """
    try:
        service = PartitionManagementService()
        
        # 获取分区信息
        partition_info = service.get_partition_info()
        if not partition_info['success']:
            return partition_info
        
        # 获取分区统计
        stats = service.get_partition_statistics()
        if not stats['success']:
            return stats
        
        # 检查最近的分区状态
        partitions = partition_info['partitions']
        current_date = date.today()
        
        # 检查当前月份和未来2个月的分区
        required_partitions = []
        for i in range(3):
            check_date = current_date.replace(day=1) + timedelta(days=i * 30)
            partition_name = f"database_size_stats_{check_date.strftime('%Y_%m')}"
            required_partitions.append(partition_name)
        
        existing_partitions = [p['name'] for p in partitions]
        missing_partitions = [p for p in required_partitions if p not in existing_partitions]
        
        return {
            'success': True,
            'status': 'healthy' if not missing_partitions else 'warning',
            'total_partitions': stats['total_partitions'],
            'total_size': stats['total_size'],
            'total_records': stats['total_records'],
            'missing_partitions': missing_partitions,
            'partitions': partitions
        }
        
    except Exception as e:
        logger.error(f"获取分区管理状态失败: {str(e)}")
        return {
            'success': False,
            'message': f'获取分区管理状态失败: {str(e)}',
            'error': str(e)
        }
