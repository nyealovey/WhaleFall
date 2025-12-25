"""Common 路由序列化模型(Flask-RESTX marshal fields)."""

from __future__ import annotations

from flask_restx import fields

COMMON_INSTANCE_OPTION_ITEM_FIELDS = {
    "id": fields.Integer(),
    "name": fields.String(),
    "db_type": fields.String(),
    "display_name": fields.String(),
}

COMMON_INSTANCES_OPTIONS_RESPONSE_FIELDS = {
    "instances": fields.List(fields.Nested(COMMON_INSTANCE_OPTION_ITEM_FIELDS)),
}

COMMON_DATABASE_OPTION_ITEM_FIELDS = {
    "id": fields.Integer(),
    "database_name": fields.String(),
    "is_active": fields.Boolean(),
    "first_seen_date": fields.String(),
    "last_seen_date": fields.String(),
    "deleted_at": fields.String(),
}

COMMON_DATABASES_OPTIONS_RESPONSE_FIELDS = {
    "databases": fields.List(fields.Nested(COMMON_DATABASE_OPTION_ITEM_FIELDS)),
    "total_count": fields.Integer(),
    "limit": fields.Integer(),
    "offset": fields.Integer(),
}

COMMON_DBTYPE_OPTION_ITEM_FIELDS = {
    "value": fields.String(),
    "text": fields.String(),
    "icon": fields.String(),
    "color": fields.String(),
}

COMMON_DBTYPES_OPTIONS_RESPONSE_FIELDS = {
    "options": fields.List(fields.Nested(COMMON_DBTYPE_OPTION_ITEM_FIELDS)),
}

