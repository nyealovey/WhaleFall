"""调度任务常量与内置任务元数据."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuiltinSchedulerTask:
    """内置调度任务元数据."""

    task_name: str
    function_name: str
    function_target: str
    description: str
    editable_fields: tuple[str, ...] = ("trigger",)


BUILTIN_SCHEDULER_TASKS: dict[str, BuiltinSchedulerTask] = {
    "sync_accounts": BuiltinSchedulerTask(
        task_name="账户同步",
        function_name="sync_accounts",
        function_target="app.tasks.accounts_sync_tasks:sync_accounts",
        description="每日同步所有数据库实例的账户信息",
    ),
    "calculate_account": BuiltinSchedulerTask(
        task_name="统计账户分类",
        function_name="calculate_account",
        function_target="app.tasks.account_classification_daily_tasks:calculate_account",
        description="每日计算账户分类命中数(规则命中 + 分类去重)",
    ),
    "sync_databases": BuiltinSchedulerTask(
        task_name="数据库同步",
        function_name="sync_databases",
        function_target="app.tasks.capacity_collection_tasks:sync_databases",
        description="每日同步所有数据库实例的容量信息",
    ),
    "calculate_database": BuiltinSchedulerTask(
        task_name="统计数据库聚合",
        function_name="calculate_database",
        function_target="app.tasks.capacity_aggregation_tasks:calculate_database",
        description="每日计算数据库大小的日、周、月、季度统计聚合",
    ),
    "sync_veeam_backups": BuiltinSchedulerTask(
        task_name="同步 Veeam 备份",
        function_name="sync_veeam_backups",
        function_target="app.tasks.veeam_backup_sync_tasks:sync_veeam_backups",
        description="每日同步 Veeam 机器级备份快照",
    ),
    "sync_cluster_status": BuiltinSchedulerTask(
        task_name="群集同步状态检测",
        function_name="sync_cluster_status",
        function_target="app.tasks.cluster_status_sync_tasks:sync_cluster_status",
        description="每日检测 MySQL 主从状态与 SQL Server AG 数据库同步异常",
    ),
    "email_alert": BuiltinSchedulerTask(
        task_name="邮件告警汇总",
        function_name="email_alert",
        function_target="app.tasks.email_alert_tasks:email_alert",
        description="每日汇总发送数据库容量、同步异常与高权限账户告警",
    ),
}

BUILTIN_TASK_IDS: set[str] = set(BUILTIN_SCHEDULER_TASKS)
