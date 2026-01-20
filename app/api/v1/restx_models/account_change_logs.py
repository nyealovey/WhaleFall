"""账户变更历史相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

ACCOUNT_CHANGE_LOG_LIST_ITEM_FIELDS = {
    "id": fields.Integer(description="变更日志 ID", example=1),
    "account_id": fields.Integer(description="账号 ID(可选)", example=4453),
    "instance_id": fields.Integer(description="实例 ID", example=100),
    "instance_name": fields.String(description="实例名称(可选)", example="CBRAIN"),
    "db_type": fields.String(description="数据库类型", example="oracle"),
    "username": fields.String(description="账号名", example="CBRAIN"),
    "change_type": fields.String(description="变更类型", example="modify_privilege"),
    "status": fields.String(description="状态", example="success"),
    "message": fields.String(description="摘要(可选)", example="新增账户,赋予 5 项权限"),
    "change_time": fields.String(description="变更时间(展示)", example="2025-12-31 08:13:25"),
    "session_id": fields.String(description="会话 ID(可选)", example="session_123"),
    "privilege_diff_count": fields.Integer(description="权限差异条目数", example=5),
    "other_diff_count": fields.Integer(description="其他差异条目数", example=1),
}

ACCOUNT_CHANGE_LOG_DETAIL_FIELDS = {
    "id": fields.Integer(description="变更日志 ID", example=1),
    "instance_id": fields.Integer(description="实例 ID", example=100),
    "db_type": fields.String(description="数据库类型", example="oracle"),
    "username": fields.String(description="账号名", example="CBRAIN"),
    "change_type": fields.String(description="变更类型", example="modify_privilege"),
    "change_time": fields.String(description="变更时间(展示)", example="2025-12-31 08:13:25"),
    "status": fields.String(description="状态", example="success"),
    "message": fields.String(description="摘要(可选)", example="新增账户,赋予 5 项权限"),
    "privilege_diff": fields.Raw(description="权限差异", example=[]),
    "other_diff": fields.Raw(description="其他差异", example=[]),
    "session_id": fields.String(description="会话 ID(可选)", example="session_123"),
}

ACCOUNT_CHANGE_LOG_STATISTICS_FIELDS = {
    "total_changes": fields.Integer(description="变更总数", example=100),
    "success_count": fields.Integer(description="成功数量", example=95),
    "failed_count": fields.Integer(description="失败数量", example=5),
    "affected_accounts": fields.Integer(description="影响账号数(去重)", example=42),
}
