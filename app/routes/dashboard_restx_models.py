"""Dashboard 路由序列化模型(Flask-RESTX marshal fields)."""

from __future__ import annotations

from flask_restx import fields

DASHBOARD_LOG_TREND_ITEM_FIELDS = {
    "date": fields.String(),
    "error_count": fields.Integer(),
    "warning_count": fields.Integer(),
}

DASHBOARD_LOG_LEVEL_ITEM_FIELDS = {
    "level": fields.String(),
    "count": fields.Integer(),
}

DASHBOARD_TASK_STATUS_ITEM_FIELDS = {
    "status": fields.String(),
    "count": fields.Integer(),
}

DASHBOARD_SYNC_TREND_ITEM_FIELDS = {
    "date": fields.String(),
    "count": fields.Integer(),
}

DASHBOARD_CHART_FIELDS: dict[str, fields.Raw] = {
    "log_trend": fields.List(fields.Nested(DASHBOARD_LOG_TREND_ITEM_FIELDS)),
    "log_levels": fields.List(fields.Nested(DASHBOARD_LOG_LEVEL_ITEM_FIELDS)),
    "task_status": fields.List(fields.Nested(DASHBOARD_TASK_STATUS_ITEM_FIELDS)),
    "sync_trend": fields.List(fields.Nested(DASHBOARD_SYNC_TREND_ITEM_FIELDS)),
}

