"""Tags 相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

TAG_LIST_ITEM_FIELDS = {
    "id": fields.Integer(description="标签 ID", example=1),
    "name": fields.String(description="标签代码", example="prod"),
    "display_name": fields.String(description="标签展示名", example="生产"),
    "category": fields.String(description="标签分类", example="env"),
    "color": fields.String(description="颜色 key", example="red"),
    "color_value": fields.String(description="颜色值", example="#FF0000"),
    "color_name": fields.String(description="颜色名称", example="Red"),
    "css_class": fields.String(description="CSS class", example="tag-red"),
    "is_active": fields.Boolean(description="是否启用", example=True),
    "created_at": fields.String(description="创建时间(ISO8601)", example="2025-01-01T00:00:00"),
    "updated_at": fields.String(description="更新时间(ISO8601)", example="2025-01-02T00:00:00"),
    "instance_count": fields.Integer(description="关联实例数", example=3),
}

TAG_OPTION_FIELDS = {
    "id": fields.Integer(description="标签 ID", example=1),
    "name": fields.String(description="标签代码", example="prod"),
    "display_name": fields.String(description="标签展示名", example="生产"),
    "category": fields.String(description="标签分类", example="env"),
    "color": fields.String(description="颜色 key", example="red"),
    "color_value": fields.String(description="颜色值", example="#FF0000"),
    "color_name": fields.String(description="颜色名称", example="Red"),
    "css_class": fields.String(description="CSS class", example="tag-red"),
    "is_active": fields.Boolean(description="是否启用", example=True),
    "created_at": fields.String(description="创建时间(ISO8601)", example="2025-01-01T00:00:00"),
    "updated_at": fields.String(description="更新时间(ISO8601)", example="2025-01-02T00:00:00"),
}

TAGGABLE_INSTANCE_FIELDS = {
    "id": fields.Integer(description="实例 ID", example=1),
    "name": fields.String(description="实例名称", example="prod-mysql-1"),
    "host": fields.String(description="主机", example="127.0.0.1"),
    "port": fields.Integer(description="端口", example=3306),
    "db_type": fields.String(description="数据库类型", example="mysql"),
}
