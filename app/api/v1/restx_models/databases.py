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

DATABASE_STATISTICS_DB_TYPE_ITEM_FIELDS = {
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "count": fields.Integer(description="数据库数量", example=4),
}

DATABASE_STATISTICS_INSTANCE_ITEM_FIELDS = {
    "instance_id": fields.Integer(description="实例 ID", example=1),
    "instance_name": fields.String(description="实例名称", example="prod-mysql-1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "count": fields.Integer(description="数据库数量", example=4),
}

DATABASE_STATISTICS_SYNC_STATUS_ITEM_FIELDS = {
    "value": fields.String(description="同步状态值", example="completed"),
    "label": fields.String(description="同步状态标签", example="已更新"),
    "variant": fields.String(description="状态样式", example="success"),
    "count": fields.Integer(description="数据库数量", example=4),
}

DATABASE_STATISTICS_CAPACITY_RANKING_ITEM_FIELDS = {
    "instance_id": fields.Integer(description="实例 ID", example=1),
    "instance_name": fields.String(description="实例名称", example="prod-mysql-1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "database_name": fields.String(description="数据库名称", example="app_db"),
    "size_mb": fields.Integer(description="容量大小(MB)", example=2048),
    "size_label": fields.String(description="格式化容量", example="2.00 GB"),
    "collected_at": fields.String(description="采集时间(ISO8601, 可选)", example="2026-03-16T10:00:00+00:00"),
}

DATABASE_STATISTICS_FIELDS = {
    "total_databases": fields.Integer(description="数据库总数", example=8),
    "active_databases": fields.Integer(description="活跃数据库数", example=6),
    "inactive_databases": fields.Integer(description="停用数据库数", example=1),
    "deleted_databases": fields.Integer(description="已删除数据库数", example=2),
    "total_instances": fields.Integer(description="涉及实例数", example=3),
    "total_size_mb": fields.Integer(description="总容量(MB)", example=4096),
    "avg_size_mb": fields.Float(description="平均容量(MB)", example=682.7),
    "max_size_mb": fields.Integer(description="最大容量(MB)", example=2048),
    "db_type_stats": fields.List(
        fields.Nested(DATABASE_STATISTICS_DB_TYPE_ITEM_FIELDS), description="按数据库类型统计"
    ),
    "instance_stats": fields.List(fields.Nested(DATABASE_STATISTICS_INSTANCE_ITEM_FIELDS), description="按实例统计"),
    "sync_status_stats": fields.List(
        fields.Nested(DATABASE_STATISTICS_SYNC_STATUS_ITEM_FIELDS),
        description="按同步状态统计",
    ),
    "capacity_rankings": fields.List(
        fields.Nested(DATABASE_STATISTICS_CAPACITY_RANKING_ITEM_FIELDS),
        description="最新容量排行",
    ),
}
