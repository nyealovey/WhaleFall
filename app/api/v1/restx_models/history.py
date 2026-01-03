"""History 相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

HISTORY_LOG_ITEM_FIELDS = {
    "id": fields.Integer(description="日志 ID", example=1),
    "timestamp": fields.String(description="时间戳(ISO8601)", example="2025-01-01T00:00:00"),
    "timestamp_display": fields.String(description="时间戳展示字段", example="2025-01-01 00:00:00"),
    "level": fields.String(description="日志级别", example="INFO"),
    "module": fields.String(description="模块", example="scheduler"),
    "message": fields.String(description="消息", example="任务执行成功"),
    "traceback": fields.String(description="异常堆栈(可选)", example=None),
    "context": fields.Raw(description="结构化上下文", example={}),
}

HISTORY_LOG_MODULES_FIELDS = {
    "modules": fields.List(fields.String(), description="模块列表", example=["scheduler", "accounts"]),
}

HISTORY_LOG_TOP_MODULE_FIELDS = {
    "module": fields.String(description="模块", example="scheduler"),
    "count": fields.Integer(description="数量", example=10),
}

HISTORY_LOG_STATISTICS_FIELDS = {
    "total_logs": fields.Integer(description="日志总数", example=1000),
    "error_count": fields.Integer(description="ERROR 数量", example=10),
    "warning_count": fields.Integer(description="WARNING 数量", example=20),
    "info_count": fields.Integer(description="INFO 数量", example=900),
    "debug_count": fields.Integer(description="DEBUG 数量", example=50),
    "critical_count": fields.Integer(description="CRITICAL 数量", example=0),
    "level_distribution": fields.Raw(description="按 level 分布", example={}),
    "top_modules": fields.List(fields.Nested(HISTORY_LOG_TOP_MODULE_FIELDS), description="Top modules"),
    "error_rate": fields.Float(description="错误率", example=0.01),
}

SYNC_INSTANCE_RECORD_ITEM_FIELDS = {
    "id": fields.Integer(description="记录 ID", example=1),
    "session_id": fields.String(description="会话 ID", example="session_123"),
    "instance_id": fields.Integer(description="实例 ID", example=1),
    "instance_name": fields.String(description="实例名称", example="prod-mysql-1"),
    "sync_category": fields.String(description="同步类别", example="accounts"),
    "status": fields.String(description="状态", example="success"),
    "started_at": fields.String(description="开始时间(ISO8601)", example="2025-01-01T00:00:00"),
    "completed_at": fields.String(description="完成时间(ISO8601, 可选)", example="2025-01-01T00:10:00"),
    "items_synced": fields.Integer(description="同步总数", example=100),
    "items_created": fields.Integer(description="新增数量", example=10),
    "items_updated": fields.Integer(description="更新数量", example=80),
    "items_deleted": fields.Integer(description="删除数量", example=10),
    "error_message": fields.String(description="错误信息(可选)", example=None),
    "sync_details": fields.Raw(description="同步详情(可选)", example={}),
    "created_at": fields.String(description="创建时间(ISO8601)", example="2025-01-01T00:00:00"),
}

SYNC_SESSION_ITEM_FIELDS = {
    "id": fields.Integer(description="记录 ID", example=1),
    "session_id": fields.String(description="会话 ID", example="session_123"),
    "sync_type": fields.String(description="同步类型", example="full"),
    "sync_category": fields.String(description="同步类别", example="accounts"),
    "status": fields.String(description="状态", example="success"),
    "started_at": fields.String(description="开始时间(ISO8601)", example="2025-01-01T00:00:00"),
    "completed_at": fields.String(description="完成时间(ISO8601, 可选)", example="2025-01-01T00:10:00"),
    "total_instances": fields.Integer(description="实例总数", example=5),
    "successful_instances": fields.Integer(description="成功实例数", example=5),
    "failed_instances": fields.Integer(description="失败实例数", example=0),
    "created_by": fields.Integer(description="创建人用户 ID", example=1),
    "created_at": fields.String(description="创建时间(ISO8601)", example="2025-01-01T00:00:00"),
    "updated_at": fields.String(description="更新时间(ISO8601)", example="2025-01-01T00:10:00"),
}

SYNC_SESSION_DETAIL_ITEM_FIELDS = {
    **SYNC_SESSION_ITEM_FIELDS,
    "instance_records": fields.List(
        fields.Nested(SYNC_INSTANCE_RECORD_ITEM_FIELDS),
        description="实例同步记录列表",
    ),
    "progress_percentage": fields.Float(description="进度百分比", example=100.0),
}

SYNC_SESSION_DETAIL_RESPONSE_FIELDS = {
    "session": fields.Nested(SYNC_SESSION_DETAIL_ITEM_FIELDS, description="会话详情"),
}

SYNC_SESSION_ERROR_LOGS_RESPONSE_FIELDS = {
    "session": fields.Nested(SYNC_SESSION_ITEM_FIELDS, description="会话信息"),
    "error_records": fields.List(fields.Nested(SYNC_INSTANCE_RECORD_ITEM_FIELDS), description="错误记录列表"),
    "error_count": fields.Integer(description="错误记录数量", example=0),
}
