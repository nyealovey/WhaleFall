"""Credentials 路由序列化模型(Flask-RESTX marshal fields)."""

from flask_restx import fields

CREDENTIAL_LIST_ITEM_FIELDS: dict[str, fields.Raw] = {
    "id": fields.Integer(description="凭据 ID", example=1),
    "name": fields.String(description="凭据名称", example="prod-db-user"),
    "credential_type": fields.String(description="凭据类型", example="password"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "username": fields.String(description="用户名", example="db_user"),
    "category_id": fields.Integer(description="分类 ID", example=1),
    "created_at": fields.String(description="创建时间(ISO8601)", example="2025-01-01T00:00:00"),
    "updated_at": fields.String(description="更新时间(ISO8601)", example="2025-01-02T00:00:00"),
    "password": fields.String(description="密码(脱敏/占位)", example="******"),
    "description": fields.String(description="描述", example="用于生产环境"),
    "is_active": fields.Boolean(description="是否启用", example=True),
    "instance_count": fields.Integer(description="关联实例数", example=2),
    "created_at_display": fields.String(description="创建时间展示字段", example="2025-01-01"),
}
