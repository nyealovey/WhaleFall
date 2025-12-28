"""Scheduler 路由序列化模型(Flask-RESTX marshal fields)."""

from flask_restx import fields

SCHEDULER_JOB_LIST_ITEM_FIELDS: dict[str, fields.Raw] = {
    "id": fields.String(description="Job ID", example="job_1"),
    "name": fields.String(description="Job 名称", example="sync_accounts"),
    "description": fields.String(description="描述", example="同步账号任务"),
    "next_run_time": fields.String(description="下次运行时间(ISO8601, 可选)", example="2025-01-01T01:00:00"),
    "last_run_time": fields.String(description="上次运行时间(ISO8601, 可选)", example="2025-01-01T00:00:00"),
    "trigger_type": fields.String(description="触发器类型", example="cron"),
    "trigger_args": fields.Raw(description="触发器参数", example={}),
    "state": fields.String(description="状态", example="scheduled"),
    "is_builtin": fields.Boolean(description="是否内置任务", example=True),
    "func": fields.String(description="执行函数", example="app.tasks.scheduler:run"),
    "args": fields.Raw(description="位置参数", example=[]),
    "kwargs": fields.Raw(description="关键字参数", example={}),
}

SCHEDULER_JOB_DETAIL_FIELDS: dict[str, fields.Raw] = {
    "id": fields.String(description="Job ID", example="job_1"),
    "name": fields.String(description="Job 名称", example="sync_accounts"),
    "next_run_time": fields.String(description="下次运行时间(ISO8601, 可选)", example="2025-01-01T01:00:00"),
    "trigger": fields.String(description="触发器描述", example="cron[hour='1']"),
    "func": fields.String(description="执行函数", example="app.tasks.scheduler:run"),
    "args": fields.Raw(description="位置参数", example=[]),
    "kwargs": fields.Raw(description="关键字参数", example={}),
    "misfire_grace_time": fields.Integer(description="misfire 宽限(秒)", example=60),
    "max_instances": fields.Integer(description="最大并发实例数", example=1),
    "coalesce": fields.Boolean(description="是否合并错过的执行", example=True),
}
