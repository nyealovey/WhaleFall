"""Accounts 相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

TAG_FIELDS = {
    "name": fields.String(description="标签代码", example="prod"),
    "display_name": fields.String(description="标签展示名", example="生产"),
    "color": fields.String(description="颜色 key", example="red"),
}

CLASSIFICATION_FIELDS = {
    "name": fields.String(description="分类名称", example="高风险"),
    "color": fields.String(description="颜色", example="#FF0000"),
}

ACCOUNT_LEDGER_ITEM_FIELDS = {
    "id": fields.Integer(description="账号 ID", example=1),
    "username": fields.String(description="账号名", example="root"),
    "instance_name": fields.String(description="实例名称", example="prod-mysql-1"),
    "instance_host": fields.String(description="实例主机", example="127.0.0.1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "is_locked": fields.Boolean(description="是否锁定", example=False),
    "is_superuser": fields.Boolean(description="是否超管", example=True),
    "is_active": fields.Boolean(description="是否启用", example=True),
    "is_deleted": fields.Boolean(description="是否删除", example=False),
    "tags": fields.List(fields.Nested(TAG_FIELDS), description="标签列表"),
    "classifications": fields.List(fields.Nested(CLASSIFICATION_FIELDS), description="分类列表"),
}

ACCOUNT_LEDGER_PERMISSION_ACCOUNT_FIELDS = {
    "id": fields.Integer(description="账号 ID", example=1),
    "username": fields.String(description="账号名", example="root"),
    "instance_name": fields.String(description="实例名称", example="prod-mysql-1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
}

ACCOUNT_LEDGER_PERMISSIONS_FIELDS = {
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "username": fields.String(description="账号名", example="root"),
    "is_superuser": fields.Boolean(description="是否超管", example=True),
    "last_sync_time": fields.String(description="最后同步时间(ISO8601)", example="2025-01-02T00:00:00"),
    "snapshot": fields.Raw(description="权限快照(v4)", example={}),
}

ACCOUNT_LEDGER_PERMISSIONS_RESPONSE_FIELDS = {
    "permissions": fields.Nested(ACCOUNT_LEDGER_PERMISSIONS_FIELDS, description="权限详情"),
    "account": fields.Nested(ACCOUNT_LEDGER_PERMISSION_ACCOUNT_FIELDS, description="账号基础信息"),
}

ACCOUNT_STATISTICS_FIELDS = {
    "total_accounts": fields.Integer(description="账号总数", example=100),
    "active_accounts": fields.Integer(description="启用账号数", example=90),
    "locked_accounts": fields.Integer(description="锁定账号数", example=2),
    "normal_accounts": fields.Integer(description="正常账号数", example=88),
    "deleted_accounts": fields.Integer(description="删除账号数", example=10),
    "database_instances": fields.Integer(description="数据库实例数(统计口径)", example=5),
    "total_instances": fields.Integer(description="实例总数", example=5),
    "active_instances": fields.Integer(description="启用实例数", example=4),
    "disabled_instances": fields.Integer(description="停用实例数", example=0),
    "normal_instances": fields.Integer(description="正常实例数", example=4),
    "deleted_instances": fields.Integer(description="删除实例数", example=1),
    "db_type_stats": fields.Raw(description="按 db_type 聚合统计", example={}),
    "classification_stats": fields.Raw(description="按 classification 聚合统计", example={}),
}

ACCOUNT_CLASSIFICATION_LIST_ITEM_FIELDS = {
    "id": fields.Integer(description="分类 ID", example=1),
    "name": fields.String(description="分类名称", example="高风险"),
    "description": fields.String(description="分类描述", example="高风险账户"),
    "risk_level": fields.String(description="风险等级", example="high"),
    "color": fields.String(description="颜色", example="#FF0000"),
    "color_key": fields.String(description="颜色 key", example="red"),
    "icon_name": fields.String(description="图标名称", example="alert-triangle"),
    "priority": fields.Integer(description="优先级", example=10),
    "is_system": fields.Boolean(description="是否系统内置", example=False),
    "created_at": fields.String(description="创建时间(ISO8601)", example="2025-01-01T00:00:00"),
    "updated_at": fields.String(description="更新时间(ISO8601)", example="2025-01-02T00:00:00"),
    "rules_count": fields.Integer(description="规则数量", example=3),
}

ACCOUNT_CLASSIFICATION_RULE_ITEM_FIELDS = {
    "id": fields.Integer(description="规则 ID", example=1),
    "rule_name": fields.String(description="规则名称", example="root-users"),
    "classification_id": fields.Integer(description="分类 ID", example=1),
    "classification_name": fields.String(description="分类名称", example="高风险"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "rule_expression": fields.Raw(description="规则表达式", example={}),
    "is_active": fields.Boolean(description="是否启用", example=True),
    "created_at": fields.String(description="创建时间(ISO8601)", example="2025-01-01T00:00:00"),
    "updated_at": fields.String(description="更新时间(ISO8601)", example="2025-01-02T00:00:00"),
    "matched_accounts_count": fields.Integer(description="命中账号数", example=12),
}

ACCOUNT_CLASSIFICATION_RULE_FILTER_ITEM_FIELDS = {
    "id": fields.Integer(description="规则 ID", example=1),
    "rule_name": fields.String(description="规则名称", example="root-users"),
    "classification_id": fields.Integer(description="分类 ID", example=1),
    "classification_name": fields.String(description="分类名称", example="高风险"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "rule_expression": fields.Raw(description="规则表达式", example={}),
    "is_active": fields.Boolean(description="是否启用", example=True),
    "created_at": fields.String(description="创建时间(ISO8601)", example="2025-01-01T00:00:00"),
    "updated_at": fields.String(description="更新时间(ISO8601)", example="2025-01-02T00:00:00"),
}

ACCOUNT_CLASSIFICATION_RULE_STAT_ITEM_FIELDS = {
    "rule_id": fields.Integer(description="规则 ID", example=1),
    "matched_accounts_count": fields.Integer(description="命中账号数", example=12),
}

ACCOUNT_CLASSIFICATION_ASSIGNMENT_ITEM_FIELDS = {
    "id": fields.Integer(description="分配记录 ID", example=1),
    "account_id": fields.Integer(description="账号 ID", example=1),
    "assigned_by": fields.Integer(description="分配人用户 ID", example=1),
    "classification_id": fields.Integer(description="分类 ID", example=1),
    "classification_name": fields.String(description="分类名称", example="高风险"),
    "assigned_at": fields.String(description="分配时间(ISO8601)", example="2025-01-01T00:00:00"),
}

ACCOUNT_CLASSIFICATION_PERMISSIONS_RESPONSE_FIELDS = {
    "permissions": fields.Raw(description="权限信息", example={}),
}
