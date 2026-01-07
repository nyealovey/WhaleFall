"""实例相关 Flask-RESTX marshal fields 定义."""

from __future__ import annotations

from flask_restx import fields

INSTANCE_TAG_FIELDS = {
    "name": fields.String(description="标签代码", example="prod"),
    "display_name": fields.String(description="标签展示名", example="生产"),
    "color": fields.String(description="颜色 key", example="red"),
}

INSTANCE_LIST_ITEM_FIELDS = {
    "id": fields.Integer(description="实例 ID", example=1),
    "name": fields.String(description="实例名称", example="prod-mysql-1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "host": fields.String(description="主机", example="127.0.0.1"),
    "port": fields.Integer(description="端口", example=3306),
    "description": fields.String(description="描述", example="生产环境实例"),
    "is_active": fields.Boolean(description="是否启用", example=True),
    "deleted_at": fields.String(description="删除时间(ISO8601, 可选)", example=None),
    "status": fields.String(description="状态", example="ok"),
    "main_version": fields.String(description="主版本", example="8.0"),
    "active_db_count": fields.Integer(description="活跃数据库数", example=12),
    "active_account_count": fields.Integer(description="活跃账号数", example=42),
    "last_sync_time": fields.String(description="最后同步时间(ISO8601, 可选)", example="2025-01-02T00:00:00"),
    "tags": fields.List(
        fields.Nested(INSTANCE_TAG_FIELDS),
        description="标签列表",
        example=[{"name": "prod", "display_name": "生产", "color": "red"}],
    ),
}

INSTANCE_OPTION_ITEM_FIELDS = {
    "id": fields.Integer(description="实例 ID", example=1),
    "name": fields.String(description="实例名称", example="prod-mysql-1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "display_name": fields.String(description="展示名", example="生产 MySQL 1"),
}

INSTANCES_OPTIONS_RESPONSE_FIELDS = {
    "instances": fields.List(
        fields.Nested(INSTANCE_OPTION_ITEM_FIELDS),
        description="实例选项列表",
        example=[{"id": 1, "name": "prod-mysql-1", "db_type": "mysql", "display_name": "生产 MySQL 1"}],
    ),
}

INSTANCE_ACCOUNT_SUMMARY_FIELDS = {
    "total": fields.Integer(description="账号总数", example=100),
    "active": fields.Integer(description="启用账号数", example=90),
    "deleted": fields.Integer(description="删除账号数", example=10),
    "superuser": fields.Integer(description="超管账号数", example=2),
}

INSTANCE_ACCOUNT_LIST_ITEM_FIELDS = {
    "id": fields.Integer(description="账号 ID", example=1),
    "username": fields.String(description="账号名", example="root"),
    "is_superuser": fields.Boolean(description="是否超管", example=True),
    "is_locked": fields.Boolean(description="是否锁定", example=False),
    "is_deleted": fields.Boolean(description="是否删除", example=False),
    "last_change_time": fields.String(description="最后变更时间(ISO8601, 可选)", example="2025-01-02T00:00:00"),
    "type_specific": fields.Raw(description="类型特有字段", example={}),
    "host": fields.String(description="主机(可选)", example="127.0.0.1"),
    "plugin": fields.String(description="认证插件(可选)", example="mysql_native_password"),
    "password_change_time": fields.String(description="密码变更时间(ISO8601, 可选)", example=None),
    "oracle_id": fields.Raw(description="Oracle ID(可选)", example=None),
    "authentication_type": fields.String(description="认证类型(可选)", example="password"),
    "account_status": fields.String(description="账号状态(可选)", example="open"),
    "lock_date": fields.String(description="锁定日期(可选)", example=None),
    "expiry_date": fields.String(description="过期日期(可选)", example=None),
    "default_tablespace": fields.String(description="默认 tablespace(可选)", example=None),
    "created": fields.String(description="创建时间(可选)", example=None),
    "server_roles": fields.List(fields.String(), description="Server roles(可选)", example=["sysadmin"]),
    "server_permissions": fields.List(
        fields.String(),
        description="Server permissions(可选)",
        example=["VIEW SERVER STATE"],
    ),
    "database_roles": fields.Raw(description="数据库角色(可选)", example={}),
    "database_permissions": fields.Raw(description="数据库权限(可选)", example={}),
}

INSTANCE_ACCOUNT_INFO_FIELDS = {
    "id": fields.Integer(description="账号 ID", example=1),
    "instance_id": fields.Integer(description="实例 ID", example=1),
    "username": fields.String(description="账号名", example="root"),
    "instance_name": fields.String(description="实例名称", example="prod-mysql-1"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
}

INSTANCE_ACCOUNT_PERMISSIONS_FIELDS = {
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "username": fields.String(description="账号名", example="root"),
    "is_superuser": fields.Boolean(description="是否超管", example=True),
    "last_sync_time": fields.String(description="最后同步时间(ISO8601, 可选)", example="2025-01-02T00:00:00"),
    "snapshot": fields.Raw(description="权限快照(v4)", example={}),
}

INSTANCE_ACCOUNT_PERMISSIONS_RESPONSE_FIELDS = {
    "permissions": fields.Nested(INSTANCE_ACCOUNT_PERMISSIONS_FIELDS, description="权限详情"),
    "account": fields.Nested(INSTANCE_ACCOUNT_INFO_FIELDS, description="账号基础信息"),
}

INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS = {
    "id": fields.Integer(description="变更记录 ID", example=1),
    "change_type": fields.String(description="变更类型", example="grant"),
    "change_time": fields.String(description="变更时间(ISO8601)", example="2025-01-01T00:00:00"),
    "status": fields.String(description="状态", example="success"),
    "message": fields.String(description="描述", example="权限变更成功"),
    "privilege_diff": fields.Raw(description="权限差异", example={}),
    "other_diff": fields.Raw(description="其他差异", example={}),
    "session_id": fields.String(description="会话 ID(可选)", example="session_123"),
}

INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS = {
    "id": fields.Integer(description="账号 ID", example=1),
    "username": fields.String(description="账号名", example="root"),
    "db_type": fields.String(description="数据库类型", example="mysql"),
}

INSTANCE_ACCOUNT_CHANGE_HISTORY_RESPONSE_FIELDS = {
    "account": fields.Nested(INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS, description="账号信息"),
    "history": fields.List(fields.Nested(INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS), description="变更历史列表"),
}

INSTANCE_DATABASE_SIZE_ENTRY_FIELDS = {
    "id": fields.Integer(description="数据库 ID", example=1),
    "database_name": fields.String(description="数据库名称", example="app_db"),
    "size_mb": fields.Raw(description="总大小(MB)", example=1024.5),
    "data_size_mb": fields.Raw(description="数据大小(MB)", example=900.0),
    "log_size_mb": fields.Raw(description="日志大小(MB)", example=124.5),
    "collected_date": fields.String(description="采集日期(YYYY-MM-DD)", example="2025-01-01"),
    "collected_at": fields.String(description="采集时间(ISO8601)", example="2025-01-01T00:00:00"),
    "is_active": fields.Boolean(description="是否启用", example=True),
    "deleted_at": fields.String(description="删除时间(ISO8601, 可选)", example=None),
    "last_seen_date": fields.String(description="最后出现日期(YYYY-MM-DD)", example="2025-01-02"),
}

INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS = {
    "schema_name": fields.String(description="Schema 名称", example="public"),
    "table_name": fields.String(description="表名称", example="users"),
    "size_mb": fields.Raw(description="总大小(MB)", example=12),
    "data_size_mb": fields.Raw(description="数据大小(MB,可选)", example=9),
    "index_size_mb": fields.Raw(description="索引大小(MB,可选)", example=3),
    "row_count": fields.Raw(description="行数(可选)", example=1000),
    "collected_at": fields.String(description="采集时间(ISO8601,可选)", example="2026-01-02T00:00:00"),
}

INSTANCE_DB_TYPE_STAT_FIELDS = {
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "count": fields.Integer(description="数量", example=10),
}

INSTANCE_PORT_STAT_FIELDS = {
    "port": fields.Integer(description="端口", example=3306),
    "count": fields.Integer(description="数量", example=10),
}

INSTANCE_VERSION_STAT_FIELDS = {
    "db_type": fields.String(description="数据库类型", example="mysql"),
    "version": fields.String(description="版本", example="8.0"),
    "count": fields.Integer(description="数量", example=10),
}

INSTANCE_STATISTICS_FIELDS = {
    "total_instances": fields.Integer(description="实例总数", example=10),
    "active_instances": fields.Integer(description="启用实例数", example=9),
    "normal_instances": fields.Integer(description="正常实例数", example=8),
    "disabled_instances": fields.Integer(description="停用实例数", example=1),
    "deleted_instances": fields.Integer(description="删除实例数", example=1),
    "inactive_instances": fields.Integer(description="非活跃实例数", example=1),
    "db_types_count": fields.Integer(description="数据库类型数量", example=4),
    "db_type_stats": fields.List(fields.Nested(INSTANCE_DB_TYPE_STAT_FIELDS), description="按 db_type 聚合统计"),
    "port_stats": fields.List(fields.Nested(INSTANCE_PORT_STAT_FIELDS), description="按端口聚合统计"),
    "version_stats": fields.List(fields.Nested(INSTANCE_VERSION_STAT_FIELDS), description="按版本聚合统计"),
}
