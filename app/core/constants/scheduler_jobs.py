"""调度任务常量."""

BUILTIN_TASK_IDS: set[str] = {
    "sync_accounts",
    "calculate_account_classification_daily_stats",
    "collect_database_sizes",
    "calculate_database_size_aggregations",
}
