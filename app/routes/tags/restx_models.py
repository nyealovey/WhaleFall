"""Tags 相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

TAG_LIST_ITEM_FIELDS = {
    "id": fields.Integer(),
    "name": fields.String(),
    "display_name": fields.String(),
    "category": fields.String(),
    "color": fields.String(),
    "color_value": fields.String(),
    "color_name": fields.String(),
    "css_class": fields.String(),
    "is_active": fields.Boolean(),
    "created_at": fields.String(),
    "updated_at": fields.String(),
    "instance_count": fields.Integer(),
}

