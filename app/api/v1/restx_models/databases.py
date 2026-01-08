"""数据库相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

DATABASE_OPTION_ITEM_FIELDS = {
    "id": fields.Integer(description="数据库 ID", example=1),
    "database_name": fields.String(description="数据库名称", example="app_db"),
    "is_active": fields.Boolean(description="是否启用", example=True),
    "first_seen_date": fields.String(description="首次发现日期(YYYY-MM-DD)", example="2025-01-01"),
    "last_seen_date": fields.String(description="最后发现日期(YYYY-MM-DD)", example="2025-01-02"),
    "deleted_at": fields.String(description="删除时间(ISO8601, 可选)", example=None),
}

DATABASES_OPTIONS_RESPONSE_FIELDS = {
    "databases": fields.List(fields.Nested(DATABASE_OPTION_ITEM_FIELDS), description="数据库选项列表"),
    "total_count": fields.Integer(description="总数", example=1),
    "page": fields.Integer(description="页码", example=1),
    "pages": fields.Integer(description="总页数", example=1),
    "limit": fields.Integer(description="分页大小", example=100),
}
