"""Scheduler 路由序列化模型(Flask-RESTX marshal fields)."""

from flask_restx import fields

SCHEDULER_JOB_LIST_ITEM_FIELDS: dict[str, fields.Raw] = {
    "id": fields.String,
    "name": fields.String,
    "description": fields.String,
    "next_run_time": fields.String,
    "last_run_time": fields.String,
    "trigger_type": fields.String,
    "trigger_args": fields.Raw,
    "state": fields.String,
    "is_builtin": fields.Boolean,
    "func": fields.String,
    "args": fields.Raw,
    "kwargs": fields.Raw,
}

SCHEDULER_JOB_DETAIL_FIELDS: dict[str, fields.Raw] = {
    "id": fields.String,
    "name": fields.String,
    "next_run_time": fields.String,
    "trigger": fields.String,
    "func": fields.String,
    "args": fields.Raw,
    "kwargs": fields.Raw,
    "misfire_grace_time": fields.Integer,
    "max_instances": fields.Integer,
    "coalesce": fields.Boolean,
}

