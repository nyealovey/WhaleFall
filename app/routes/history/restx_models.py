"""History 相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

HISTORY_LOG_ITEM_FIELDS = {
    "id": fields.Integer(),
    "timestamp": fields.String(),
    "timestamp_display": fields.String(),
    "level": fields.String(),
    "module": fields.String(),
    "message": fields.String(),
    "traceback": fields.String(),
    "context": fields.Raw(),
}

HISTORY_LOG_MODULES_FIELDS = {
    "modules": fields.List(fields.String()),
}

HISTORY_LOG_TOP_MODULE_FIELDS = {
    "module": fields.String(),
    "count": fields.Integer(),
}

HISTORY_LOG_STATISTICS_FIELDS = {
    "total_logs": fields.Integer(),
    "error_count": fields.Integer(),
    "warning_count": fields.Integer(),
    "info_count": fields.Integer(),
    "debug_count": fields.Integer(),
    "critical_count": fields.Integer(),
    "level_distribution": fields.Raw(),
    "top_modules": fields.List(fields.Nested(HISTORY_LOG_TOP_MODULE_FIELDS)),
    "error_rate": fields.Float(),
}

SYNC_INSTANCE_RECORD_ITEM_FIELDS = {
    "id": fields.Integer(),
    "session_id": fields.String(),
    "instance_id": fields.Integer(),
    "instance_name": fields.String(),
    "sync_category": fields.String(),
    "status": fields.String(),
    "started_at": fields.String(),
    "completed_at": fields.String(),
    "items_synced": fields.Integer(),
    "items_created": fields.Integer(),
    "items_updated": fields.Integer(),
    "items_deleted": fields.Integer(),
    "error_message": fields.String(),
    "sync_details": fields.Raw(),
    "created_at": fields.String(),
}

SYNC_SESSION_ITEM_FIELDS = {
    "id": fields.Integer(),
    "session_id": fields.String(),
    "sync_type": fields.String(),
    "sync_category": fields.String(),
    "status": fields.String(),
    "started_at": fields.String(),
    "completed_at": fields.String(),
    "total_instances": fields.Integer(),
    "successful_instances": fields.Integer(),
    "failed_instances": fields.Integer(),
    "created_by": fields.Integer(),
    "created_at": fields.String(),
    "updated_at": fields.String(),
}

SYNC_SESSION_DETAIL_ITEM_FIELDS = {
    **SYNC_SESSION_ITEM_FIELDS,
    "instance_records": fields.List(fields.Nested(SYNC_INSTANCE_RECORD_ITEM_FIELDS)),
    "progress_percentage": fields.Float(),
}

SYNC_SESSION_DETAIL_RESPONSE_FIELDS = {
    "session": fields.Nested(SYNC_SESSION_DETAIL_ITEM_FIELDS),
}

SYNC_SESSION_ERROR_LOGS_RESPONSE_FIELDS = {
    "session": fields.Nested(SYNC_SESSION_ITEM_FIELDS),
    "error_records": fields.List(fields.Nested(SYNC_INSTANCE_RECORD_ITEM_FIELDS)),
    "error_count": fields.Integer(),
}
