"""实例相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

INSTANCE_TAG_FIELDS = {
    "name": fields.String(),
    "display_name": fields.String(),
    "color": fields.String(),
}

INSTANCE_LIST_ITEM_FIELDS = {
    "id": fields.Integer(),
    "name": fields.String(),
    "db_type": fields.String(),
    "host": fields.String(),
    "port": fields.Integer(),
    "description": fields.String(),
    "is_active": fields.Boolean(),
    "deleted_at": fields.String(),
    "status": fields.String(),
    "main_version": fields.String(),
    "active_db_count": fields.Integer(),
    "active_account_count": fields.Integer(),
    "last_sync_time": fields.String(),
    "tags": fields.List(fields.Nested(INSTANCE_TAG_FIELDS)),
}

INSTANCE_ACCOUNT_SUMMARY_FIELDS = {
    "total": fields.Integer(),
    "active": fields.Integer(),
    "deleted": fields.Integer(),
    "superuser": fields.Integer(),
}

INSTANCE_ACCOUNT_LIST_ITEM_FIELDS = {
    "id": fields.Integer(),
    "username": fields.String(),
    "is_superuser": fields.Boolean(),
    "is_locked": fields.Boolean(),
    "is_deleted": fields.Boolean(),
    "last_change_time": fields.String(),
    "type_specific": fields.Raw(),
    "host": fields.String(),
    "plugin": fields.String(),
    "password_change_time": fields.String(),
    "oracle_id": fields.Raw(),
    "authentication_type": fields.String(),
    "account_status": fields.String(),
    "lock_date": fields.String(),
    "expiry_date": fields.String(),
    "default_tablespace": fields.String(),
    "created": fields.String(),
    "server_roles": fields.List(fields.String()),
    "server_permissions": fields.List(fields.String()),
    "database_roles": fields.Raw(),
    "database_permissions": fields.Raw(),
}

INSTANCE_ACCOUNT_INFO_FIELDS = {
    "id": fields.Integer(),
    "instance_id": fields.Integer(),
    "username": fields.String(),
    "instance_name": fields.String(),
    "db_type": fields.String(),
}

INSTANCE_ACCOUNT_PERMISSIONS_FIELDS = {
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

INSTANCE_ACCOUNT_PERMISSIONS_RESPONSE_FIELDS = {
    "permissions": fields.Nested(INSTANCE_ACCOUNT_PERMISSIONS_FIELDS),
    "account": fields.Nested(INSTANCE_ACCOUNT_INFO_FIELDS),
}

INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS = {
    "id": fields.Integer(),
    "change_type": fields.String(),
    "change_time": fields.String(),
    "status": fields.String(),
    "message": fields.String(),
    "privilege_diff": fields.Raw(),
    "other_diff": fields.Raw(),
    "session_id": fields.String(),
}

INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS = {
    "id": fields.Integer(),
    "username": fields.String(),
    "db_type": fields.String(),
}

INSTANCE_ACCOUNT_CHANGE_HISTORY_RESPONSE_FIELDS = {
    "account": fields.Nested(INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS),
    "history": fields.List(fields.Nested(INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS)),
}

INSTANCE_DATABASE_SIZE_ENTRY_FIELDS = {
    "id": fields.Integer(),
    "database_name": fields.String(),
    "size_mb": fields.Raw(),
    "data_size_mb": fields.Raw(),
    "log_size_mb": fields.Raw(),
    "collected_date": fields.String(),
    "collected_at": fields.String(),
    "is_active": fields.Boolean(),
    "deleted_at": fields.String(),
    "last_seen_date": fields.String(),
}

INSTANCE_DB_TYPE_STAT_FIELDS = {
    "db_type": fields.String(),
    "count": fields.Integer(),
}

INSTANCE_PORT_STAT_FIELDS = {
    "port": fields.Integer(),
    "count": fields.Integer(),
}

INSTANCE_VERSION_STAT_FIELDS = {
    "db_type": fields.String(),
    "version": fields.String(),
    "count": fields.Integer(),
}

INSTANCE_STATISTICS_FIELDS = {
    "total_instances": fields.Integer(),
    "active_instances": fields.Integer(),
    "normal_instances": fields.Integer(),
    "disabled_instances": fields.Integer(),
    "deleted_instances": fields.Integer(),
    "inactive_instances": fields.Integer(),
    "db_types_count": fields.Integer(),
    "db_type_stats": fields.List(fields.Nested(INSTANCE_DB_TYPE_STAT_FIELDS)),
    "port_stats": fields.List(fields.Nested(INSTANCE_PORT_STAT_FIELDS)),
    "version_stats": fields.List(fields.Nested(INSTANCE_VERSION_STAT_FIELDS)),
}
