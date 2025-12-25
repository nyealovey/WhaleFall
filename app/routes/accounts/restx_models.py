"""Accounts 相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

TAG_FIELDS = {
    "name": fields.String(),
    "display_name": fields.String(),
    "color": fields.String(),
}

CLASSIFICATION_FIELDS = {
    "name": fields.String(),
    "color": fields.String(),
}

ACCOUNT_LEDGER_ITEM_FIELDS = {
    "id": fields.Integer(),
    "username": fields.String(),
    "instance_name": fields.String(),
    "instance_host": fields.String(),
    "db_type": fields.String(),
    "is_locked": fields.Boolean(),
    "is_superuser": fields.Boolean(),
    "is_active": fields.Boolean(),
    "is_deleted": fields.Boolean(),
    "tags": fields.List(fields.Nested(TAG_FIELDS)),
    "classifications": fields.List(fields.Nested(CLASSIFICATION_FIELDS)),
}

