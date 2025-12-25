"""实例相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

INSTANCE_TAG_FIELDS = {
    "name": fields.String(),
    "display_name": fields.String(),
    "color": fields.String(),
}

INSTANCE_LIST_ITEM_FIELDS = {
    "id": fields.Integer(),
    "name": fields.String(),
    "db_type": fields.String(),
    "host": fields.String(),
    "port": fields.Integer(),
    "description": fields.String(),
    "is_active": fields.Boolean(),
    "deleted_at": fields.String(),
    "status": fields.String(),
    "main_version": fields.String(),
    "active_db_count": fields.Integer(),
    "active_account_count": fields.Integer(),
    "last_sync_time": fields.String(),
    "tags": fields.List(fields.Nested(INSTANCE_TAG_FIELDS)),
}

