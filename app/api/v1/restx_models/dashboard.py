"""Dashboard 路由序列化模型(Flask-RESTX marshal fields)."""

from __future__ import annotations

from flask_restx import fields

DASHBOARD_LOG_TREND_ITEM_FIELDS = {
    "date": fields.String(description="日期(YYYY-MM-DD)", example="2025-01-01"),
    "error_count": fields.Integer(description="错误数量", example=1),
    "warning_count": fields.Integer(description="警告数量", example=2),
}

DASHBOARD_LOG_LEVEL_ITEM_FIELDS = {
    "level": fields.String(description="日志级别", example="INFO"),
    "count": fields.Integer(description="数量", example=100),
}

DASHBOARD_TASK_STATUS_ITEM_FIELDS = {
    "status": fields.String(description="任务状态", example="success"),
    "count": fields.Integer(description="数量", example=10),
}

DASHBOARD_SYNC_TREND_ITEM_FIELDS = {
    "date": fields.String(description="日期(YYYY-MM-DD)", example="2025-01-01"),
    "count": fields.Integer(description="数量", example=3),
}

DASHBOARD_CHART_FIELDS: dict[str, fields.Raw] = {
    "log_trend": fields.List(fields.Nested(DASHBOARD_LOG_TREND_ITEM_FIELDS), description="日志趋势"),
    "log_levels": fields.List(fields.Nested(DASHBOARD_LOG_LEVEL_ITEM_FIELDS), description="按 level 分布"),
    "task_status": fields.List(fields.Nested(DASHBOARD_TASK_STATUS_ITEM_FIELDS), description="任务状态分布"),
    "sync_trend": fields.List(fields.Nested(DASHBOARD_SYNC_TREND_ITEM_FIELDS), description="同步趋势"),
}
