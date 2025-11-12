"""
调度任务常量
"""

BUILTIN_TASK_IDS: set[str] = {
    "cleanup_logs",
    "sync_accounts",
    "monitor_partition_health",
    "collect_database_sizes",
    "calculate_database_size_aggregations",
}
