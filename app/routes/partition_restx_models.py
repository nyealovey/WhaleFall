"""Partition 路由序列化模型(Flask-RESTX marshal fields)."""

from flask_restx import fields

PARTITION_ENTRY_FIELDS: dict[str, fields.Raw] = {
    "name": fields.String,
    "table": fields.String,
    "table_type": fields.String,
    "display_name": fields.String,
    "size": fields.String,
    "size_bytes": fields.Integer,
    "record_count": fields.Integer,
    "date": fields.String,
    "status": fields.String,
}

PARTITION_INFO_DATA_FIELDS: dict[str, fields.Raw] = {
    "partitions": fields.List(fields.Nested(PARTITION_ENTRY_FIELDS)),
    "total_partitions": fields.Integer,
    "total_size_bytes": fields.Integer,
    "total_size": fields.String,
    "total_records": fields.Integer,
    "tables": fields.List(fields.String),
    "status": fields.String,
    "missing_partitions": fields.List(fields.String),
}

PARTITION_INFO_RESPONSE_FIELDS: dict[str, fields.Raw] = {
    "data": fields.Nested(PARTITION_INFO_DATA_FIELDS),
    "timestamp": fields.String,
}

PARTITION_STATUS_DATA_FIELDS: dict[str, fields.Raw] = {
    "status": fields.String,
    "total_partitions": fields.Integer,
    "total_size": fields.String,
    "total_records": fields.Integer,
    "missing_partitions": fields.List(fields.String),
    "partitions": fields.List(fields.Nested(PARTITION_ENTRY_FIELDS)),
}

PARTITION_STATUS_RESPONSE_FIELDS: dict[str, fields.Raw] = {
    "data": fields.Nested(PARTITION_STATUS_DATA_FIELDS),
    "timestamp": fields.String,
}

PARTITION_LIST_RESPONSE_FIELDS: dict[str, fields.Raw] = {
    "items": fields.List(fields.Nested(PARTITION_ENTRY_FIELDS)),
    "total": fields.Integer,
    "page": fields.Integer,
    "pages": fields.Integer,
    "limit": fields.Integer,
}

PARTITION_CORE_METRICS_FIELDS: dict[str, fields.Raw] = {
    "labels": fields.List(fields.String),
    "datasets": fields.Raw,
    "dataPointCount": fields.Integer,
    "timeRange": fields.String,
    "yAxisLabel": fields.String,
    "chartTitle": fields.String,
    "periodType": fields.String,
}
