"""PostgreSQL 账户同步适配器(两阶段版)."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, cast

from app.core.constants import DatabaseType
from app.schemas.external_contracts.postgresql_account import PostgreSQLRawAccountSchema
from app.services.accounts_sync.accounts_sync_filters import DatabaseFilterManager
from app.services.accounts_sync.adapters.base_adapter import BaseAccountAdapter
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.structlog_config import get_sync_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.core.types import JsonDict, JsonValue, PermissionSnapshot, RawAccount, RemoteAccount
    from app.core.types.sync import SyncConnection
    from app.models.instance import Instance


class PostgreSQLAccountAdapter(BaseAccountAdapter):
    """PostgreSQL 账户同步适配器.

    实现 PostgreSQL 数据库的账户查询和权限采集功能.
    通过 pg_roles 视图和权限查询函数采集角色信息和权限.

    Attributes:
        logger: 同步日志记录器.
        filter_manager: 数据库过滤管理器.

    Example:
        >>> adapter = PostgreSQLAccountAdapter()
        >>> accounts = adapter.fetch_accounts(instance, connection)
        >>> enriched = adapter.enrich_permissions(instance, connection, accounts)

    """

    def __init__(self) -> None:
        """初始化 PostgreSQL 适配器,挂载日志与过滤器."""
        self.logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()
        self.POSTGRES_ADAPTER_EXCEPTIONS: tuple[type[Exception], ...] = (
            RuntimeError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            ConnectionError,
        )

    @staticmethod
    def _get_connection(connection: object) -> SyncConnection:
        """将通用连接对象规范为同步协议连接."""
        return cast("SyncConnection", connection)

    @staticmethod
    def _to_isoformat(value: JsonValue) -> str | None:
        """将日期/时间值转换为 ISO 字符串."""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, str):
            return value
        return None

    def _fetch_raw_accounts(self, instance: Instance, connection: object) -> list[RawAccount]:
        """拉取 PostgreSQL 原始账户信息.

        从 pg_roles 视图中查询角色基本信息.

        Args:
            instance: 实例对象.
            connection: PostgreSQL 数据库连接对象.

        Returns:
            原始账户信息列表,每个元素包含用户名、超级用户标志、角色属性等.

        """
        conn = self._get_connection(connection)
        try:
            where_clause, params = self._build_filter_conditions()
            roles_sql = (
                "SELECT "
                "    rolname as username, "
                "    rolsuper as is_superuser, "
                "    rolcreaterole as can_create_role, "
                "    rolcreatedb as can_create_db, "
                "    rolreplication as can_replicate, "
                "    rolbypassrls as can_bypass_rls, "
                "    rolcanlogin as can_login, "
                "    rolinherit as can_inherit, "
                "    CASE "
                "        WHEN rolvaliduntil = 'infinity'::timestamp THEN NULL "
                "        WHEN rolvaliduntil = '-infinity'::timestamp THEN NULL "
                "        ELSE rolvaliduntil "
                "    END as valid_until "
                "FROM pg_roles WHERE " + where_clause + " ORDER BY rolname"
            )
            rows = conn.execute_query(roles_sql, params)
        except self.POSTGRES_ADAPTER_EXCEPTIONS as exc:
            self.logger.exception(
                "fetch_postgresql_accounts_failed",
                module="postgresql_account_adapter",
                instance=instance.name,
                error=str(exc),
            )
            return []
        else:
            accounts: list[RawAccount] = []
            for row in rows:
                (
                    username,
                    is_superuser,
                    can_create_role,
                    can_create_db,
                    can_replicate,
                    can_bypass_rls,
                    can_login,
                    can_inherit,
                    valid_until,
                ) = row
                valid_until_str = self._to_isoformat(valid_until)
                type_specific: JsonDict = {}
                if valid_until_str:
                    type_specific["valid_until"] = valid_until_str
                role_attributes = {
                    "can_create_role": bool(can_create_role),
                    "can_create_db": bool(can_create_db),
                    "can_replicate": bool(can_replicate),
                    "can_bypass_rls": bool(can_bypass_rls),
                    "can_inherit": bool(can_inherit),
                    "can_login": bool(can_login),
                    "can_super": bool(is_superuser),
                }
                permissions: PermissionSnapshot = {
                    "type_specific": type_specific,
                    "postgresql_role_attributes": role_attributes,
                }
                accounts.append(
                    {
                        "username": username,
                        "is_superuser": is_superuser,
                        "can_login": bool(can_login),
                        "permissions": permissions,
                    },
                )
            self.logger.info(
                "fetch_postgresql_accounts_success",
                module="postgresql_account_adapter",
                instance=instance.name,
                account_count=len(accounts),
            )
            return accounts

    def _normalize_account(self, instance: Instance, account: RawAccount) -> RemoteAccount:
        """规范化 PostgreSQL 账户信息.

        将原始账户信息转换为统一格式.

        Args:
            instance: 实例对象.
            account: 原始账户信息字典.

        Returns:
            规范化后的账户信息字典.

        """
        _ = instance
        parsed = PostgreSQLRawAccountSchema.model_validate(account)
        permissions = parsed.permissions
        normalized_permissions: PermissionSnapshot = {
            "postgresql_predefined_roles": permissions.postgresql_predefined_roles,
            "postgresql_role_attributes": permissions.postgresql_role_attributes,
            "postgresql_database_privileges": cast("JsonDict", permissions.postgresql_database_privileges),
            "type_specific": permissions.type_specific,
        }
        return cast(
            "RemoteAccount",
            {
                "username": parsed.username,
                "display_name": parsed.username,
                "db_type": DatabaseType.POSTGRESQL,
                "is_superuser": parsed.is_superuser,
                "is_locked": parsed.is_locked,
                "is_active": True,
                "permissions": normalized_permissions,
            },
        )

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _build_filter_conditions(self) -> tuple[str, list[str] | dict[str, JsonValue]]:
        """根据配置生成账号过滤条件.

        Returns:
            tuple[str, list[str]]: 参数化 WHERE 子句及其参数列表.

        """
        rules = self.filter_manager.get_filter_rules("postgresql")
        builder = SafeQueryBuilder(db_type="postgresql")
        exclude_users = cast("list[str]", rules.get("exclude_users", []))
        exclude_patterns = cast("list[str]", rules.get("exclude_patterns", []))
        builder.add_database_specific_condition("rolname", exclude_users, exclude_patterns)
        where_clause, params = builder.build_where_clause()
        if isinstance(params, list):
            return where_clause, [str(param) for param in params]
        return where_clause, params

    def _get_role_permissions(
        self,
        connection: object,
        username: str,
    ) -> PermissionSnapshot:
        """聚合指定角色的权限信息.

        Args:
            connection: PostgreSQL 数据库连接.
            username: 角色名/用户名.

        Returns:
            PermissionSnapshot: 包含角色属性、预定义角色、数据库权限等信息.

        """
        permissions: PermissionSnapshot = {
            "postgresql_predefined_roles": [],
            "postgresql_role_attributes": {},
            "postgresql_database_privileges": {},
            "type_specific": {},
        }
        try:
            permissions["postgresql_role_attributes"] = self._get_role_attributes(connection, username)
        except self.POSTGRES_ADAPTER_EXCEPTIONS as exc:
            self.logger.warning(
                "fetch_pg_role_attributes_failed",
                role=username,
                error=str(exc),
                exc_info=True,
            )
        try:
            permissions["postgresql_predefined_roles"] = self._get_predefined_roles(connection, username)
        except self.POSTGRES_ADAPTER_EXCEPTIONS as exc:
            self.logger.warning(
                "fetch_pg_predefined_roles_failed",
                role=username,
                error=str(exc),
                exc_info=True,
            )
        try:
            permissions["postgresql_database_privileges"] = self._get_database_privileges(connection, username)
        except self.POSTGRES_ADAPTER_EXCEPTIONS as exc:
            self.logger.warning(
                "fetch_pg_database_privileges_failed",
                role=username,
                error=str(exc),
                exc_info=True,
            )
        return permissions

    def enrich_permissions(
        self,
        instance: Instance,
        connection: object,
        accounts: list[RemoteAccount],
        *,
        usernames: Sequence[str] | None = None,
    ) -> list[RemoteAccount]:
        """丰富 PostgreSQL 账户的权限信息.

        为指定账户查询详细的权限信息,包括角色属性、预定义角色、数据库权限等.

        Args:
            instance: 实例对象.
            connection: PostgreSQL 数据库连接对象.
            accounts: 账户信息列表.
            usernames: 可选的目标用户名列表.

        Returns:
            丰富后的账户信息列表.

        """
        target_usernames = {account["username"] for account in accounts} if usernames is None else set(usernames)
        if not target_usernames:
            return accounts

        processed = 0
        for account in accounts:
            username = account.get("username")
            if not username or username not in target_usernames:
                continue
            processed += 1
            try:
                existing_permissions_value = account.get("permissions")
                existing_permissions: PermissionSnapshot
                if isinstance(existing_permissions_value, dict):
                    existing_permissions = cast("PermissionSnapshot", existing_permissions_value)
                else:
                    existing_permissions = cast("PermissionSnapshot", {})
                permissions = self._get_role_permissions(
                    connection,
                    username,
                )
                self._merge_seed_permissions(permissions, existing_permissions)
                account["permissions"] = permissions
            except self.POSTGRES_ADAPTER_EXCEPTIONS as exc:
                self.logger.exception(
                    "fetch_pg_permissions_failed",
                    module="postgresql_account_adapter",
                    instance=instance.name,
                    username=username,
                    error=str(exc),
                )
                permissions_value = account.get("permissions")
                if not isinstance(permissions_value, dict):
                    permissions_value = {}
                    account["permissions"] = cast("PermissionSnapshot", permissions_value)
                permissions = cast("PermissionSnapshot", permissions_value)
                errors_list = permissions.get("errors")
                if not isinstance(errors_list, list):
                    errors_list = []
                    permissions["errors"] = errors_list
                errors_list.append(str(exc))

        self.logger.info(
            "fetch_postgresql_permissions_completed",
            module="postgresql_account_adapter",
            instance=instance.name,
            processed_accounts=processed,
        )
        return accounts

    def _merge_seed_permissions(
        self,
        permissions: PermissionSnapshot,
        seed_permissions: PermissionSnapshot,
    ) -> None:
        """将已有权限数据与新查询数据合并."""
        type_specific = cast("JsonDict", permissions.setdefault("type_specific", {}))
        role_attributes = cast("JsonDict", permissions.setdefault("postgresql_role_attributes", {}))
        seed_type_specific_value = seed_permissions.get("type_specific")
        seed_type_specific = (
            cast("JsonDict", seed_type_specific_value) if isinstance(seed_type_specific_value, dict) else {}
        )
        seed_role_attributes_value = seed_permissions.get("postgresql_role_attributes")
        seed_role_attributes = (
            cast("JsonDict", seed_role_attributes_value) if isinstance(seed_role_attributes_value, dict) else {}
        )

        if seed_type_specific.get("valid_until") is not None:
            type_specific.setdefault("valid_until", seed_type_specific["valid_until"])
        for key, value in seed_role_attributes.items():
            if value is not None:
                role_attributes.setdefault(key, value)

    # 以下辅助查询函数沿用旧实现
    def _get_role_attributes(self, connection: object, username: str) -> JsonDict:
        """查询角色属性.

        Args:
            connection: PostgreSQL 连接对象.
            username: 角色名.

        Returns:
            JsonDict: 角色能力标志,如 `can_create_db` 等.

        """
        sql = """
            SELECT rolcreaterole, rolcreatedb, rolreplication, rolbypassrls, rolcanlogin, rolinherit
            FROM pg_roles
            WHERE rolname = %s
        """
        conn = self._get_connection(connection)
        rows = list(conn.execute_query(sql, (username,)))
        if not rows:
            return {}
        row = rows[0]
        return {
            "can_create_role": bool(row[0]),
            "can_create_db": bool(row[1]),
            "can_replicate": bool(row[2]),
            "can_bypass_rls": bool(row[3]),
            "can_login": bool(row[4]),
            "can_inherit": bool(row[5]),
        }

    def _get_predefined_roles(self, connection: object, username: str) -> list[str]:
        """查询用户所属的预定义角色.

        Args:
            connection: PostgreSQL 连接对象.
            username: 角色名.

        Returns:
            list[str]: 预定义角色名称列表.

        """
        sql = """
            SELECT
                pg_get_userbyid(roleid) as role_name
            FROM pg_auth_members
            WHERE member = (SELECT oid FROM pg_roles WHERE rolname = %s)
        """
        conn = self._get_connection(connection)
        rows = list(conn.execute_query(sql, (username,)))
        role_names: list[str] = []
        for row in rows:
            role_name = row[0] if row and len(row) > 0 else None
            if isinstance(role_name, (str, bytes)):
                role_names.append(str(role_name))
        return role_names

    def _get_database_privileges(self, connection: object, username: str) -> dict[str, list[str]]:
        """查询用户在各数据库上的权限.

        Args:
            connection: PostgreSQL 连接对象.
            username: 角色名.

        Returns:
            dict[str, list[str]]: 键为数据库名,值为权限列表.

        """
        sql = """
            SELECT
                datname,
                ARRAY[
                    CASE WHEN has_database_privilege(%s, datname, 'CONNECT') THEN 'CONNECT' END,
                    CASE WHEN has_database_privilege(%s, datname, 'CREATE') THEN 'CREATE' END,
                    CASE WHEN has_database_privilege(%s, datname, 'TEMP') THEN 'TEMP' END
                ]::text[] AS privileges
            FROM pg_database
            WHERE datallowconn = true
              AND (
                    has_database_privilege(%s, datname, 'CONNECT')
                 OR has_database_privilege(%s, datname, 'CREATE')
                 OR has_database_privilege(%s, datname, 'TEMP')
              )
        """
        conn = self._get_connection(connection)
        rows = list(conn.execute_query(sql, (username,) * 6))
        privileges: dict[str, list[str]] = {}
        for row in rows:
            if not row or not row[0]:
                continue
            datname, priv_list = row
            if not isinstance(datname, (str, bytes)):
                continue
            filtered = (
                [str(priv) for priv in priv_list if isinstance(priv, (str, bytes))]
                if isinstance(priv_list, (list, tuple, set))
                else []
            )
            if filtered:
                privileges[str(datname)] = filtered
        return privileges
