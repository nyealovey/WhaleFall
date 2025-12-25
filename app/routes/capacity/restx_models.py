"""容量统计相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

CAPACITY_INSTANCE_REF_FIELDS = {
    "id": fields.Integer(),
    "name": fields.String(),
    "db_type": fields.String(),
}

CAPACITY_INSTANCE_AGGREGATION_ITEM_FIELDS = {
    "id": fields.Integer(),
    "instance_id": fields.Integer(),
    "period_type": fields.String(),
    "period_start": fields.String(),
    "period_end": fields.String(),
    "total_size_mb": fields.Integer(),
    "avg_size_mb": fields.Integer(),
    "max_size_mb": fields.Integer(),
    "min_size_mb": fields.Integer(),
    "data_count": fields.Integer(),
    "database_count": fields.Integer(),
    "avg_database_count": fields.Float(),
    "max_database_count": fields.Integer(),
    "min_database_count": fields.Integer(),
    "total_size_change_mb": fields.Integer(),
    "total_size_change_percent": fields.Float(),
    "database_count_change": fields.Integer(),
    "database_count_change_percent": fields.Float(),
    "growth_rate": fields.Float(),
    "trend_direction": fields.String(),
    "calculated_at": fields.String(),
    "created_at": fields.String(),
    "instance": fields.Nested(CAPACITY_INSTANCE_REF_FIELDS),
}

CAPACITY_INSTANCE_SUMMARY_FIELDS = {
    "total_instances": fields.Integer(),
    "total_size_mb": fields.Integer(),
    "avg_size_mb": fields.Float(),
    "max_size_mb": fields.Integer(),
    "period_type": fields.String(),
    "source": fields.String(),
}

CAPACITY_DATABASE_AGGREGATION_ITEM_FIELDS = {
    "id": fields.Integer(),
    "instance_id": fields.Integer(),
    "database_name": fields.String(),
    "period_type": fields.String(),
    "period_start": fields.String(),
    "period_end": fields.String(),
    "avg_size_mb": fields.Integer(),
    "max_size_mb": fields.Integer(),
    "min_size_mb": fields.Integer(),
    "data_count": fields.Integer(),
    "avg_data_size_mb": fields.Integer(),
    "max_data_size_mb": fields.Integer(),
    "min_data_size_mb": fields.Integer(),
    "avg_log_size_mb": fields.Integer(),
    "max_log_size_mb": fields.Integer(),
    "min_log_size_mb": fields.Integer(),
    "size_change_mb": fields.Integer(),
    "size_change_percent": fields.Float(),
    "data_size_change_mb": fields.Integer(),
    "data_size_change_percent": fields.Float(),
    "log_size_change_mb": fields.Integer(),
    "log_size_change_percent": fields.Float(),
    "growth_rate": fields.Float(),
    "calculated_at": fields.String(),
    "created_at": fields.String(),
    "instance": fields.Nested(CAPACITY_INSTANCE_REF_FIELDS),
}

CAPACITY_DATABASE_SUMMARY_FIELDS = {
    "total_databases": fields.Integer(),
    "total_instances": fields.Integer(),
    "total_size_mb": fields.Integer(),
    "avg_size_mb": fields.Float(),
    "max_size_mb": fields.Integer(),
    "growth_rate": fields.Float(),
}

CAPACITY_CURRENT_AGGREGATION_RESULT_FIELDS = {
    "status": fields.String(),
    "message": fields.String(),
    "period_type": fields.String(),
    "period_start": fields.String(),
    "period_end": fields.String(),
    "scope": fields.String(),
    "requested_period_type": fields.String(),
    "effective_period_type": fields.String(),
    "database_summary": fields.Raw(),
    "instance_summary": fields.Raw(),
    "session": fields.Raw(),
}

CAPACITY_CURRENT_AGGREGATION_RESPONSE_FIELDS = {
    "result": fields.Nested(CAPACITY_CURRENT_AGGREGATION_RESULT_FIELDS),
}

