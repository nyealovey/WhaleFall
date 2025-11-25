"""定时任务模块。

包含各种定时任务的实现，由 APScheduler 调度执行。

主要任务：
- log_cleanup_tasks: 日志清理任务
- account_sync_tasks: 账户同步任务
- capacity_collection_tasks: 容量采集任务
- capacity_aggregation_tasks: 容量聚合任务
- partition_management_tasks: 分区管理任务
"""

from .log_cleanup_tasks import cleanup_old_logs
from .account_sync_tasks import sync_accounts

# 导入容量监控相关任务
from .capacity_collection_tasks import (
    collect_database_sizes,
    collect_specific_instance_database_sizes,
    collect_database_sizes_by_type,
    get_collection_status,
    validate_collection_config
)

from .capacity_aggregation_tasks import (
    calculate_database_size_aggregations,
    calculate_instance_aggregations,
    calculate_period_aggregations,
    get_aggregation_status,
    validate_aggregation_config,
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
    
    # 分区管理任务
    'create_database_size_partitions',
    'cleanup_database_size_partitions',
    'monitor_partition_health',
    'get_partition_management_status'
]
