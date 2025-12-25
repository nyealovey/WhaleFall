"""History 相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

HISTORY_LOG_ITEM_FIELDS = {
    "id": fields.Integer(),
    "timestamp": fields.String(),
    "timestamp_display": fields.String(),
    "level": fields.String(),
    "module": fields.String(),
    "message": fields.String(),
    "traceback": fields.String(),
    "context": fields.Raw(),
}

