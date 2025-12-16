"""PostgreSQL 账户同步适配器(两阶段版)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from app.constants import DatabaseType
from app.services.accounts_sync.accounts_sync_filters import DatabaseFilterManager
from app.services.accounts_sync.adapters.base_adapter import BaseAccountAdapter
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.structlog_config import get_sync_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.models.instance import Instance
    from app.types import JsonDict, JsonValue, PermissionSnapshot, RawAccount, RemoteAccount
    from app.types.sync import SyncConnection
else:
    Instance = Any
    JsonDict = dict[str, Any]
    JsonValue = Any
    PermissionSnapshot = dict[str, Any]
    RawAccount = dict[str, Any]
    RemoteAccount = dict[str, Any]


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
        self.POSTGRES_ADAPTER_EXCEPTIONS: tuple[type[BaseException], ...] = (
            RuntimeError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            ConnectionError,
        )

    @staticmethod
    def _get_connection(connection: object) -> "SyncConnection":
        """将通用连接对象规范为同步协议连接."""
        return cast("SyncConnection", connection)

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
                "FROM pg_roles WHERE "
                + where_clause
                + " ORDER BY rolname"
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
                type_specific = {
                    "can_create_role": bool(can_create_role),
                    "can_create_db": bool(can_create_db),
                    "can_replicate": bool(can_replicate),
                    "can_bypass_rls": bool(can_bypass_rls),
                    "can_login": bool(can_login),
                    "can_inherit": bool(can_inherit),
                    "valid_until": valid_until.isoformat() if valid_until else None,
                }
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
                    "role_attributes": role_attributes,
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
        permissions = cast("PermissionSnapshot", account.get("permissions") or {})
        type_specific = cast("JsonDict", permissions.setdefault("type_specific", {}))
        role_attributes = cast("JsonDict", permissions.setdefault("role_attributes", {}))
        if "can_login" not in type_specific and account.get("can_login") is not None:
            type_specific["can_login"] = bool(account.get("can_login"))
        can_login = bool(type_specific.get("can_login", True))
        normalized_permissions: PermissionSnapshot = {
            "predefined_roles": cast("list[str]", permissions.get("predefined_roles", [])),
            "role_attributes": role_attributes,
            "database_privileges_pg": cast("JsonDict", permissions.get("database_privileges_pg", {})),
            "tablespace_privileges": cast("JsonDict", permissions.get("tablespace_privileges", {})),
            "system_privileges": cast("list[str]", permissions.get("system_privileges", [])),
            "type_specific": type_specific,
        }
        return cast(
            "RemoteAccount",
            {
                "username": account["username"],
                "display_name": account["username"],
                "db_type": DatabaseType.POSTGRESQL,
                "is_superuser": account.get("is_superuser", False),
                "is_locked": not can_login,
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
        return builder.build_where_clause()

    def _get_role_permissions(
        self,
        connection: object,
        username: str,
        *,
        is_superuser: bool,
    ) -> PermissionSnapshot:
        """聚合指定角色的权限信息.

        Args:
            connection: PostgreSQL 数据库连接.
            username: 角色名/用户名.
            is_superuser: 该用户是否具备超级权限.

        Returns:
            PermissionSnapshot: 包含角色属性、预定义角色、数据库/表空间权限等信息.

        """
        permissions: PermissionSnapshot = {
            "predefined_roles": [],
            "role_attributes": {},
            "database_privileges_pg": {},
            "tablespace_privileges": {},
            "system_privileges": [],
            "type_specific": {},
        }
        try:
            permissions["role_attributes"] = self._get_role_attributes(connection, username)
        except self.POSTGRES_ADAPTER_EXCEPTIONS as exc:
            self.logger.warning(
                "fetch_pg_role_attributes_failed",
                role=username,
                error=str(exc),
                exc_info=True,
            )
        try:
            permissions["predefined_roles"] = self._get_predefined_roles(connection, username)
        except self.POSTGRES_ADAPTER_EXCEPTIONS as exc:
            self.logger.warning(
                "fetch_pg_predefined_roles_failed",
                role=username,
                error=str(exc),
                exc_info=True,
            )
        try:
            permissions["database_privileges_pg"] = self._get_database_privileges(connection, username)
        except self.POSTGRES_ADAPTER_EXCEPTIONS as exc:
            self.logger.warning(
                "fetch_pg_database_privileges_failed",
                role=username,
                error=str(exc),
                exc_info=True,
            )
        try:
            permissions["tablespace_privileges"] = self._get_tablespace_privileges(connection, username)
        except self.POSTGRES_ADAPTER_EXCEPTIONS as exc:
            self.logger.warning(
                "fetch_pg_tablespace_privileges_failed",
                role=username,
                error=str(exc),
                exc_info=True,
            )
        if is_superuser:
            permissions["system_privileges"].append("SUPERUSER")
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
                existing_permissions = cast("PermissionSnapshot", account.get("permissions") or {})
                permissions = self._get_role_permissions(
                    connection,
                    username,
                    is_superuser=bool(account.get("is_superuser")),
                )
                self._merge_seed_permissions(permissions, existing_permissions)
                self._apply_login_flags(account, permissions)
            except self.POSTGRES_ADAPTER_EXCEPTIONS as exc:
                self.logger.exception(
                    "fetch_pg_permissions_failed",
                    module="postgresql_account_adapter",
                    instance=instance.name,
                    username=username,
                    error=str(exc),
                )
                account.setdefault("permissions", {}).setdefault("errors", []).append(str(exc))

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
        role_attributes = cast("JsonDict", permissions.setdefault("role_attributes", {}))
        seed_type_specific = cast("JsonDict", seed_permissions.get("type_specific") or {})
        seed_role_attributes = cast("JsonDict", seed_permissions.get("role_attributes") or {})

        for key, value in seed_type_specific.items():
            if value is not None:
                type_specific.setdefault(key, value)
        for key, value in seed_role_attributes.items():
            if value is not None:
                role_attributes.setdefault(key, value)

        propagated_keys = (
            "can_create_role",
            "can_create_db",
            "can_replicate",
            "can_bypass_rls",
            "can_inherit",
            "can_login",
        )
        for propagated_key in propagated_keys:
            value = role_attributes.get(propagated_key)
            if value is not None:
                type_specific.setdefault(propagated_key, value)

        if "can_login" not in type_specific and role_attributes.get("can_login") is not None:
            type_specific["can_login"] = bool(role_attributes["can_login"])
        if seed_type_specific.get("valid_until") is not None and "valid_until" not in type_specific:
            type_specific["valid_until"] = seed_type_specific["valid_until"]

    def _apply_login_flags(
        self,
        account: RemoteAccount,
        permissions: PermissionSnapshot,
    ) -> None:
        """根据权限结果更新账户状态."""
        account["permissions"] = permissions
        type_specific = cast("JsonDict", permissions.get("type_specific") or {})
        can_login = bool(type_specific.get("can_login", True))
        account["is_active"] = can_login
        account["is_locked"] = not can_login

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
        result = conn.execute_query(sql, (username,))
        if not result:
            return {}
        row = result[0]
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
        rows = conn.execute_query(sql, (username,))
        return [row[0] for row in rows if row and row[0]]

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
        rows = conn.execute_query(sql, (username,) * 6)
        privileges: dict[str, list[str]] = {}
        for row in rows:
            if not row or not row[0]:
                continue
            datname, priv_list = row
            filtered = [priv for priv in (priv_list or []) if priv]
            if filtered:
                privileges[datname] = filtered
        return privileges

    def _get_tablespace_privileges(self, connection: object, username: str) -> dict[str, list[str]]:
        """查询用户在各表空间上的权限.

        Args:
            connection: PostgreSQL 连接对象.
            username: 角色名.

        Returns:
            dict[str, list[str]]: 键为表空间名,值为权限列表.

        """
        sql = """
            SELECT
                spcname,
                ARRAY[
                    CASE WHEN has_tablespace_privilege(%s, spcname, 'CREATE') THEN 'CREATE' END
                ]::text[] AS privileges
            FROM pg_tablespace
            WHERE has_tablespace_privilege(%s, spcname, 'CREATE')
        """
        conn = self._get_connection(connection)
        rows = conn.execute_query(sql, (username, username))
        privileges: dict[str, list[str]] = {}
        for row in rows:
            if not row or not row[0]:
                continue
            spcname, priv_list = row
            filtered = [priv for priv in (priv_list or []) if priv]
            if filtered:
                privileges[spcname] = filtered
        return privileges
