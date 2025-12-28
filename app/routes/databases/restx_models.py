"""数据库相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

TAG_FIELDS = {
    "name": fields.String(description="标签代码", example="prod"),
    "display_name": fields.String(description="标签展示名", example="生产"),
    "color": fields.String(description="颜色 key", example="red"),
}

DATABASE_LEDGER_INSTANCE_FIELDS = {
    "id": fields.Integer(description="实例 ID", example=1),
    "name": fields.String(description="实例名称", example="prod-mysql-1"),
    "host": fields.String(description="主机", example="127.0.0.1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
}

DATABASE_LEDGER_CAPACITY_FIELDS = {
    "size_mb": fields.Integer(description="容量(MB)", example=1024),
    "size_bytes": fields.Integer(description="容量(Bytes)", example=1073741824),
    "label": fields.String(description="展示标签", example="1.0 GB"),
    "collected_at": fields.String(description="采集时间(ISO8601)", example="2025-01-01T00:00:00"),
}

DATABASE_LEDGER_SYNC_STATUS_FIELDS = {
    "value": fields.String(description="状态值", example="ok"),
    "label": fields.String(description="状态展示", example="正常"),
    "variant": fields.String(description="UI variant", example="success"),
}

DATABASE_LEDGER_ITEM_FIELDS = {
    "id": fields.Integer(description="数据库 ID", example=1),
    "database_name": fields.String(description="数据库名称", example="app_db"),
    "instance": fields.Nested(DATABASE_LEDGER_INSTANCE_FIELDS, description="实例信息"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "capacity": fields.Nested(DATABASE_LEDGER_CAPACITY_FIELDS, description="容量信息"),
    "sync_status": fields.Nested(DATABASE_LEDGER_SYNC_STATUS_FIELDS, description="同步状态"),
    "tags": fields.List(fields.Nested(TAG_FIELDS), description="标签列表"),
}

DATABASE_CAPACITY_TREND_POINT_FIELDS = {
    "collected_at": fields.String(description="采集时间(ISO8601)", example="2025-01-01T00:00:00"),
    "collected_date": fields.String(description="采集日期(YYYY-MM-DD)", example="2025-01-01"),
    "size_mb": fields.Integer(description="容量(MB)", example=1024),
    "size_bytes": fields.Integer(description="容量(Bytes)", example=1073741824),
    "label": fields.String(description="展示标签", example="1.0 GB"),
}

DATABASE_CAPACITY_TREND_DATABASE_FIELDS = {
    "id": fields.Integer(description="数据库 ID", example=1),
    "name": fields.String(description="数据库名称", example="app_db"),
    "instance_id": fields.Integer(description="实例 ID", example=1),
    "instance_name": fields.String(description="实例名称", example="prod-mysql-1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
}

DATABASE_CAPACITY_TREND_RESPONSE_FIELDS = {
    "database": fields.Nested(DATABASE_CAPACITY_TREND_DATABASE_FIELDS, description="数据库信息"),
    "points": fields.List(fields.Nested(DATABASE_CAPACITY_TREND_POINT_FIELDS), description="趋势点列表"),
}
