"""Partition 路由序列化模型(Flask-RESTX marshal fields)."""

from flask_restx import fields

PARTITION_ENTRY_FIELDS: dict[str, fields.Raw] = {
    "name": fields.String(description="分区名", example="p202501"),
    "table": fields.String(description="表名", example="audit_logs"),
    "table_type": fields.String(description="表类型", example="partition"),
    "display_name": fields.String(description="展示名", example="2025-01"),
    "size": fields.String(description="大小(展示)", example="1.0 GB"),
    "size_bytes": fields.Integer(description="大小(Bytes)", example=1073741824),
    "record_count": fields.Integer(description="记录数", example=1000000),
    "date": fields.String(description="分区日期(YYYY-MM-DD, 可选)", example="2025-01-01"),
    "status": fields.String(description="状态", example="ok"),
}

PARTITION_INFO_DATA_FIELDS: dict[str, fields.Raw] = {
    "partitions": fields.List(fields.Nested(PARTITION_ENTRY_FIELDS), description="分区列表"),
    "total_partitions": fields.Integer(description="分区总数", example=12),
    "total_size_bytes": fields.Integer(description="总大小(Bytes)", example=1234567890),
    "total_size": fields.String(description="总大小(展示)", example="1.2 GB"),
    "total_records": fields.Integer(description="总记录数", example=1000000),
    "tables": fields.List(fields.String(), description="涉及表列表", example=["audit_logs"]),
    "status": fields.String(description="整体状态", example="ok"),
    "missing_partitions": fields.List(fields.String(), description="缺失分区列表", example=[]),
}

PARTITION_INFO_RESPONSE_FIELDS: dict[str, fields.Raw] = {
    "data": fields.Nested(PARTITION_INFO_DATA_FIELDS, description="分区信息"),
    "timestamp": fields.String(description="时间戳(ISO8601)", example="2025-01-01T00:00:00"),
}

PARTITION_STATUS_DATA_FIELDS: dict[str, fields.Raw] = {
    "status": fields.String(description="状态", example="ok"),
    "total_partitions": fields.Integer(description="分区总数", example=12),
    "total_size": fields.String(description="总大小(展示)", example="1.2 GB"),
    "total_records": fields.Integer(description="总记录数", example=1000000),
    "missing_partitions": fields.List(fields.String(), description="缺失分区列表", example=[]),
    "partitions": fields.List(fields.Nested(PARTITION_ENTRY_FIELDS), description="分区列表"),
}

PARTITION_STATUS_RESPONSE_FIELDS: dict[str, fields.Raw] = {
    "data": fields.Nested(PARTITION_STATUS_DATA_FIELDS, description="分区状态信息"),
    "timestamp": fields.String(description="时间戳(ISO8601)", example="2025-01-01T00:00:00"),
}

PARTITION_LIST_RESPONSE_FIELDS: dict[str, fields.Raw] = {
    "items": fields.List(fields.Nested(PARTITION_ENTRY_FIELDS), description="分区列表"),
    "total": fields.Integer(description="总数", example=12),
    "page": fields.Integer(description="页码", example=1),
    "pages": fields.Integer(description="总页数", example=1),
    "limit": fields.Integer(description="分页大小", example=20),
}

PARTITION_CORE_METRICS_FIELDS: dict[str, fields.Raw] = {
    "labels": fields.List(fields.String(), description="X 轴 labels", example=["2025-01-01", "2025-01-02"]),
    "datasets": fields.Raw(description="图表 datasets", example=[]),
    "dataPointCount": fields.Integer(description="数据点数量", example=2),
    "timeRange": fields.String(description="时间范围", example="last_7_days"),
    "yAxisLabel": fields.String(description="Y 轴 label", example="Size (MB)"),
    "chartTitle": fields.String(description="图表标题", example="Partition size trend"),
    "periodType": fields.String(description="周期类型", example="day"),
}
