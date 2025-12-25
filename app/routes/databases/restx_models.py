"""数据库相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

TAG_FIELDS = {
    "name": fields.String(),
    "display_name": fields.String(),
    "color": fields.String(),
}

DATABASE_LEDGER_INSTANCE_FIELDS = {
    "id": fields.Integer(),
    "name": fields.String(),
    "host": fields.String(),
    "db_type": fields.String(),
}

DATABASE_LEDGER_CAPACITY_FIELDS = {
    "size_mb": fields.Integer(),
    "size_bytes": fields.Integer(),
    "label": fields.String(),
    "collected_at": fields.String(),
}

DATABASE_LEDGER_SYNC_STATUS_FIELDS = {
    "value": fields.String(),
    "label": fields.String(),
    "variant": fields.String(),
}

DATABASE_LEDGER_ITEM_FIELDS = {
    "id": fields.Integer(),
    "database_name": fields.String(),
    "instance": fields.Nested(DATABASE_LEDGER_INSTANCE_FIELDS),
    "db_type": fields.String(),
    "capacity": fields.Nested(DATABASE_LEDGER_CAPACITY_FIELDS),
    "sync_status": fields.Nested(DATABASE_LEDGER_SYNC_STATUS_FIELDS),
    "tags": fields.List(fields.Nested(TAG_FIELDS)),
}

DATABASE_CAPACITY_TREND_POINT_FIELDS = {
    "collected_at": fields.String(),
    "collected_date": fields.String(),
    "size_mb": fields.Integer(),
    "size_bytes": fields.Integer(),
    "label": fields.String(),
}

DATABASE_CAPACITY_TREND_DATABASE_FIELDS = {
    "id": fields.Integer(),
    "name": fields.String(),
    "instance_id": fields.Integer(),
    "instance_name": fields.String(),
    "db_type": fields.String(),
}

DATABASE_CAPACITY_TREND_RESPONSE_FIELDS = {
    "database": fields.Nested(DATABASE_CAPACITY_TREND_DATABASE_FIELDS),
    "points": fields.List(fields.Nested(DATABASE_CAPACITY_TREND_POINT_FIELDS)),
}
