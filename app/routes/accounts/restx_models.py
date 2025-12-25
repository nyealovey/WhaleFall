"""Accounts 相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

TAG_FIELDS = {
    "name": fields.String(),
    "display_name": fields.String(),
    "color": fields.String(),
}

CLASSIFICATION_FIELDS = {
    "name": fields.String(),
    "color": fields.String(),
}

ACCOUNT_LEDGER_ITEM_FIELDS = {
    "id": fields.Integer(),
    "username": fields.String(),
    "instance_name": fields.String(),
    "instance_host": fields.String(),
    "db_type": fields.String(),
    "is_locked": fields.Boolean(),
    "is_superuser": fields.Boolean(),
    "is_active": fields.Boolean(),
    "is_deleted": fields.Boolean(),
    "tags": fields.List(fields.Nested(TAG_FIELDS)),
    "classifications": fields.List(fields.Nested(CLASSIFICATION_FIELDS)),
}

ACCOUNT_LEDGER_PERMISSION_ACCOUNT_FIELDS = {
    "id": fields.Integer(),
    "username": fields.String(),
    "instance_name": fields.String(),
    "db_type": fields.String(),
}

ACCOUNT_LEDGER_PERMISSIONS_FIELDS = {
    "db_type": fields.String(),
    "username": fields.String(),
    "is_superuser": fields.Boolean(),
    "last_sync_time": fields.String(),
    "global_privileges": fields.List(fields.String()),
    "database_privileges": fields.Raw(),
    "predefined_roles": fields.List(fields.String()),
    "role_attributes": fields.Raw(),
    "database_privileges_pg": fields.Raw(),
    "tablespace_privileges": fields.Raw(),
    "server_roles": fields.List(fields.String()),
    "server_permissions": fields.List(fields.String()),
    "database_roles": fields.Raw(),
    "database_permissions": fields.Raw(),
    "oracle_roles": fields.List(fields.String()),
    "oracle_system_privileges": fields.List(fields.String()),
    "oracle_tablespace_privileges": fields.Raw(),
}

ACCOUNT_LEDGER_PERMISSIONS_RESPONSE_FIELDS = {
    "permissions": fields.Nested(ACCOUNT_LEDGER_PERMISSIONS_FIELDS),
    "account": fields.Nested(ACCOUNT_LEDGER_PERMISSION_ACCOUNT_FIELDS),
}

ACCOUNT_STATISTICS_FIELDS = {
    "total_accounts": fields.Integer(),
    "active_accounts": fields.Integer(),
    "locked_accounts": fields.Integer(),
    "normal_accounts": fields.Integer(),
    "deleted_accounts": fields.Integer(),
    "database_instances": fields.Integer(),
    "total_instances": fields.Integer(),
    "active_instances": fields.Integer(),
    "disabled_instances": fields.Integer(),
    "normal_instances": fields.Integer(),
    "deleted_instances": fields.Integer(),
    "db_type_stats": fields.Raw(),
    "classification_stats": fields.Raw(),
}

ACCOUNT_CLASSIFICATION_LIST_ITEM_FIELDS = {
    "id": fields.Integer(),
    "name": fields.String(),
    "description": fields.String(),
    "risk_level": fields.String(),
    "color": fields.String(),
    "color_key": fields.String(),
    "icon_name": fields.String(),
    "priority": fields.Integer(),
    "is_system": fields.Boolean(),
    "created_at": fields.String(),
    "updated_at": fields.String(),
    "rules_count": fields.Integer(),
}

ACCOUNT_CLASSIFICATION_RULE_ITEM_FIELDS = {
    "id": fields.Integer(),
    "rule_name": fields.String(),
    "classification_id": fields.Integer(),
    "classification_name": fields.String(),
    "db_type": fields.String(),
    "rule_expression": fields.Raw(),
    "is_active": fields.Boolean(),
    "created_at": fields.String(),
    "updated_at": fields.String(),
    "matched_accounts_count": fields.Integer(),
}

ACCOUNT_CLASSIFICATION_RULE_STAT_ITEM_FIELDS = {
    "rule_id": fields.Integer(),
    "matched_accounts_count": fields.Integer(),
}

ACCOUNT_CLASSIFICATION_ASSIGNMENT_ITEM_FIELDS = {
    "id": fields.Integer(),
    "account_id": fields.Integer(),
    "assigned_by": fields.Integer(),
    "classification_id": fields.Integer(),
    "classification_name": fields.String(),
    "assigned_at": fields.String(),
}

ACCOUNT_CLASSIFICATION_PERMISSIONS_RESPONSE_FIELDS = {
    "permissions": fields.Raw(),
}
