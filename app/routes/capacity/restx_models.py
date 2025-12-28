"""容量统计相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

CAPACITY_INSTANCE_REF_FIELDS = {
    "id": fields.Integer(description="实例 ID", example=1),
    "name": fields.String(description="实例名称", example="prod-mysql-1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
}

CAPACITY_INSTANCE_AGGREGATION_ITEM_FIELDS = {
    "id": fields.Integer(description="记录 ID", example=1),
    "instance_id": fields.Integer(description="实例 ID", example=1),
    "period_type": fields.String(description="周期类型(day/week/month)", example="day"),
    "period_start": fields.String(description="周期开始(YYYY-MM-DD)", example="2025-01-01"),
    "period_end": fields.String(description="周期结束(YYYY-MM-DD)", example="2025-01-01"),
    "total_size_mb": fields.Integer(description="总容量(MB)", example=1024),
    "avg_size_mb": fields.Integer(description="平均容量(MB)", example=512),
    "max_size_mb": fields.Integer(description="最大容量(MB)", example=2048),
    "min_size_mb": fields.Integer(description="最小容量(MB)", example=256),
    "data_count": fields.Integer(description="采样点数量", example=24),
    "database_count": fields.Integer(description="数据库数", example=12),
    "avg_database_count": fields.Float(description="平均数据库数", example=10.5),
    "max_database_count": fields.Integer(description="最大数据库数", example=12),
    "min_database_count": fields.Integer(description="最小数据库数", example=9),
    "total_size_change_mb": fields.Integer(description="容量变化(MB)", example=50),
    "total_size_change_percent": fields.Float(description="容量变化百分比", example=5.2),
    "database_count_change": fields.Integer(description="数据库数量变化", example=1),
    "database_count_change_percent": fields.Float(description="数据库数量变化百分比", example=8.3),
    "growth_rate": fields.Float(description="增长率", example=0.12),
    "trend_direction": fields.String(description="趋势方向(up/down/flat)", example="up"),
    "calculated_at": fields.String(description="计算时间(ISO8601)", example="2025-01-01T00:00:00"),
    "created_at": fields.String(description="创建时间(ISO8601)", example="2025-01-01T00:00:00"),
    "instance": fields.Nested(CAPACITY_INSTANCE_REF_FIELDS, description="实例引用"),
}

CAPACITY_INSTANCE_SUMMARY_FIELDS = {
    "total_instances": fields.Integer(description="实例总数", example=10),
    "total_size_mb": fields.Integer(description="总容量(MB)", example=10240),
    "avg_size_mb": fields.Float(description="平均容量(MB)", example=1024.0),
    "max_size_mb": fields.Integer(description="最大容量(MB)", example=2048),
    "period_type": fields.String(description="周期类型", example="day"),
    "source": fields.String(description="数据来源", example="capacity_aggregation"),
}

CAPACITY_DATABASE_AGGREGATION_ITEM_FIELDS = {
    "id": fields.Integer(description="记录 ID", example=1),
    "instance_id": fields.Integer(description="实例 ID", example=1),
    "database_name": fields.String(description="数据库名称", example="app_db"),
    "period_type": fields.String(description="周期类型(day/week/month)", example="day"),
    "period_start": fields.String(description="周期开始(YYYY-MM-DD)", example="2025-01-01"),
    "period_end": fields.String(description="周期结束(YYYY-MM-DD)", example="2025-01-01"),
    "avg_size_mb": fields.Integer(description="平均总大小(MB)", example=512),
    "max_size_mb": fields.Integer(description="最大总大小(MB)", example=1024),
    "min_size_mb": fields.Integer(description="最小总大小(MB)", example=256),
    "data_count": fields.Integer(description="采样点数量", example=24),
    "avg_data_size_mb": fields.Integer(description="平均 data 大小(MB)", example=400),
    "max_data_size_mb": fields.Integer(description="最大 data 大小(MB)", example=800),
    "min_data_size_mb": fields.Integer(description="最小 data 大小(MB)", example=200),
    "avg_log_size_mb": fields.Integer(description="平均 log 大小(MB)", example=100),
    "max_log_size_mb": fields.Integer(description="最大 log 大小(MB)", example=200),
    "min_log_size_mb": fields.Integer(description="最小 log 大小(MB)", example=50),
    "size_change_mb": fields.Integer(description="总大小变化(MB)", example=20),
    "size_change_percent": fields.Float(description="总大小变化百分比", example=3.9),
    "data_size_change_mb": fields.Integer(description="data 大小变化(MB)", example=15),
    "data_size_change_percent": fields.Float(description="data 大小变化百分比", example=3.6),
    "log_size_change_mb": fields.Integer(description="log 大小变化(MB)", example=5),
    "log_size_change_percent": fields.Float(description="log 大小变化百分比", example=5.0),
    "growth_rate": fields.Float(description="增长率", example=0.1),
    "calculated_at": fields.String(description="计算时间(ISO8601)", example="2025-01-01T00:00:00"),
    "created_at": fields.String(description="创建时间(ISO8601)", example="2025-01-01T00:00:00"),
    "instance": fields.Nested(CAPACITY_INSTANCE_REF_FIELDS, description="实例引用"),
}

CAPACITY_DATABASE_SUMMARY_FIELDS = {
    "total_databases": fields.Integer(description="数据库总数", example=120),
    "total_instances": fields.Integer(description="实例总数", example=10),
    "total_size_mb": fields.Integer(description="总容量(MB)", example=10240),
    "avg_size_mb": fields.Float(description="平均容量(MB)", example=512.0),
    "max_size_mb": fields.Integer(description="最大容量(MB)", example=2048),
    "growth_rate": fields.Float(description="增长率", example=0.12),
}

CAPACITY_CURRENT_AGGREGATION_RESULT_FIELDS = {
    "status": fields.String(description="状态", example="ok"),
    "message": fields.String(description="提示信息", example="aggregation completed"),
    "period_type": fields.String(description="周期类型", example="day"),
    "period_start": fields.String(description="周期开始(YYYY-MM-DD)", example="2025-01-01"),
    "period_end": fields.String(description="周期结束(YYYY-MM-DD)", example="2025-01-01"),
    "scope": fields.String(description="聚合范围", example="all"),
    "requested_period_type": fields.String(description="请求周期类型", example="day"),
    "effective_period_type": fields.String(description="实际周期类型", example="day"),
    "database_summary": fields.Raw(description="数据库聚合摘要", example={}),
    "instance_summary": fields.Raw(description="实例聚合摘要", example={}),
    "session": fields.Raw(description="会话信息", example={}),
}

CAPACITY_CURRENT_AGGREGATION_RESPONSE_FIELDS = {
    "result": fields.Nested(CAPACITY_CURRENT_AGGREGATION_RESULT_FIELDS, description="聚合结果"),
}
