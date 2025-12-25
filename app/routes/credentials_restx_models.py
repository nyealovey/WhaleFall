"""Credentials 路由序列化模型(Flask-RESTX marshal fields)."""

from flask_restx import fields

CREDENTIAL_LIST_ITEM_FIELDS: dict[str, fields.Raw] = {
    "id": fields.Integer,
    "name": fields.String,
    "credential_type": fields.String,
    "db_type": fields.String,
    "username": fields.String,
    "category_id": fields.Integer,
    "created_at": fields.String,
    "updated_at": fields.String,
    "password": fields.String,
    "description": fields.String,
    "is_active": fields.Boolean,
    "instance_count": fields.Integer,
    "created_at_display": fields.String,
}

