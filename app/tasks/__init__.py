"""
鲸落定时任务模块
包含各种定时任务的实现
"""

# 导入现有任务
from .cleanup_old_logs import cleanup_old_logs
from .sync_accounts import sync_accounts

# 导入数据库大小监控相关任务
from .database_size_collection_tasks import (
    collect_database_sizes,
    collect_specific_instance_database_sizes,
    collect_database_sizes_by_type,
    get_collection_status,
    validate_collection_config
)

from .database_size_aggregation_tasks import (
    calculate_database_size_aggregations,
    calculate_instance_aggregations,
    calculate_period_aggregations,
    get_aggregation_status,
    validate_aggregation_config,
    cleanup_old_aggregations
)

from .partition_management_tasks import (
    create_database_size_partitions,
    cleanup_database_size_partitions,
    monitor_partition_health,
    get_partition_management_status
)

__all__ = [
    # 现有任务
    'cleanup_old_logs',
    'sync_accounts',
    
    # 数据库大小采集任务
    'collect_database_sizes',
    'collect_specific_instance_database_sizes',
    'collect_database_sizes_by_type',
    'get_collection_status',
    'validate_collection_config',
    
    # 数据库大小聚合任务
    'calculate_database_size_aggregations',
    'calculate_instance_aggregations',
    'calculate_period_aggregations',
    'get_aggregation_status',
    'validate_aggregation_config',
    'cleanup_old_aggregations',
    
    # 分区管理任务
    'create_database_size_partitions',
    'cleanup_database_size_partitions',
    'monitor_partition_health',
    'get_partition_management_status'
]
