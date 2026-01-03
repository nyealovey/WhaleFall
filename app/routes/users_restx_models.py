"""Users 路由序列化模型(Flask-RESTX marshal fields)."""

from flask_restx import fields

USER_LIST_ITEM_FIELDS: dict[str, type[fields.Raw]] = {
    "id": fields.Integer,
    "username": fields.String,
    "role": fields.String,
    "created_at": fields.String,
    "created_at_display": fields.String,
    "last_login": fields.String,
    "is_active": fields.Boolean,
}
