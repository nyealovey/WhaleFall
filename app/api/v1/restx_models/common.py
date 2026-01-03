"""Common 路由序列化模型(Flask-RESTX marshal fields)."""

from __future__ import annotations

from flask_restx import fields

COMMON_INSTANCE_OPTION_ITEM_FIELDS = {
    "id": fields.Integer(description="实例 ID", example=1),
    "name": fields.String(description="实例名称", example="prod-mysql-1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "display_name": fields.String(description="展示名", example="生产 MySQL 1"),
}

COMMON_INSTANCES_OPTIONS_RESPONSE_FIELDS = {
    "instances": fields.List(
        fields.Nested(COMMON_INSTANCE_OPTION_ITEM_FIELDS),
        description="实例选项列表",
        example=[{"id": 1, "name": "prod-mysql-1", "db_type": "mysql", "display_name": "生产 MySQL 1"}],
    ),
}

COMMON_DATABASE_OPTION_ITEM_FIELDS = {
    "id": fields.Integer(description="数据库 ID", example=1),
    "database_name": fields.String(description="数据库名称", example="app_db"),
    "is_active": fields.Boolean(description="是否启用", example=True),
    "first_seen_date": fields.String(description="首次发现日期(YYYY-MM-DD)", example="2025-01-01"),
    "last_seen_date": fields.String(description="最后发现日期(YYYY-MM-DD)", example="2025-01-02"),
    "deleted_at": fields.String(description="删除时间(ISO8601, 可选)", example=None),
}

COMMON_DATABASES_OPTIONS_RESPONSE_FIELDS = {
    "databases": fields.List(fields.Nested(COMMON_DATABASE_OPTION_ITEM_FIELDS), description="数据库选项列表"),
    "total_count": fields.Integer(description="总数", example=1),
    "limit": fields.Integer(description="分页大小", example=100),
    "offset": fields.Integer(description="分页偏移", example=0),
}

COMMON_DBTYPE_OPTION_ITEM_FIELDS = {
    "value": fields.String(description="数据库类型值", example="mysql"),
    "text": fields.String(description="展示文本", example="MySQL"),
    "icon": fields.String(description="图标 key", example="database"),
    "color": fields.String(description="颜色", example="#1f77b4"),
}

COMMON_DBTYPES_OPTIONS_RESPONSE_FIELDS = {
    "options": fields.List(
        fields.Nested(COMMON_DBTYPE_OPTION_ITEM_FIELDS),
        description="数据库类型选项列表",
    ),
}
