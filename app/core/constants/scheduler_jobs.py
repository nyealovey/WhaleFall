"""调度任务常量."""

BUILTIN_TASK_IDS: set[str] = {
    "sync_accounts",
    "sync_veeam_backups",
    "sync_cluster_status",
    "calculate_account",
    "sync_databases",
    "calculate_database",
    "email_alert",
}
