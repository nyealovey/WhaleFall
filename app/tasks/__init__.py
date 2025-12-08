"""定时任务模块.

包含各种定时任务的实现,由 APScheduler 调度执行.

主要任务:
- log_cleanup_tasks: 日志清理任务
- accounts_sync_tasks: 账户同步任务
- capacity_collection_tasks: 容量采集任务
- capacity_aggregation_tasks: 容量聚合任务
- partition_management_tasks: 分区管理任务
"""

from .accounts_sync_tasks import sync_accounts
from .capacity_aggregation_tasks import (
    calculate_database_size_aggregations,
    calculate_instance_aggregations,
    calculate_period_aggregations,
    get_aggregation_status,
    validate_aggregation_config,
)

# 导入容量监控相关任务
from .capacity_collection_tasks import (
    collect_database_sizes,
    collect_database_sizes_by_type,
    collect_specific_instance_database_sizes,
    get_collection_status,
    validate_collection_config,
)
from .log_cleanup_tasks import cleanup_old_logs
from .partition_management_tasks import (
    cleanup_database_size_partitions,
    create_database_size_partitions,
    get_partition_management_status,
    monitor_partition_health,
)

__all__ = [
    # 数据库大小聚合任务
    "calculate_database_size_aggregations",
    "calculate_instance_aggregations",
    "calculate_period_aggregations",
    "cleanup_database_size_partitions",
    # 现有任务
    "cleanup_old_logs",
    # 数据库大小采集任务
    "collect_database_sizes",
    "collect_database_sizes_by_type",
    "collect_specific_instance_database_sizes",
    # 分区管理任务
    "create_database_size_partitions",
    "get_aggregation_status",
    "get_collection_status",
    "get_partition_management_status",
    "monitor_partition_health",
    "sync_accounts",
    "validate_aggregation_config",
    "validate_collection_config",
]
