"""SQL Server 账户同步适配器(两阶段版)."""

from __future__ import annotations

import re
import time
from collections.abc import Iterable, Sequence
from re import Pattern
from typing import TYPE_CHECKING, Any, cast

from app.constants import DatabaseType
from app.services.accounts_sync.accounts_sync_filters import DatabaseFilterManager
from app.services.accounts_sync.adapters.base_adapter import BaseAccountAdapter
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.utils.structlog_config import get_sync_logger

if TYPE_CHECKING:
    from app.models.instance import Instance
    from app.types import JsonDict, JsonValue, PermissionSnapshot, RawAccount, RemoteAccount
else:
    Instance = Any
    JsonDict = dict[str, Any]
    JsonValue = Any
    PermissionSnapshot = dict[str, Any]
    RawAccount = dict[str, Any]
    RemoteAccount = dict[str, Any]

try:  # pragma: no cover - 运行环境可能未安装 SQL Server 驱动
    import pymssql  # type: ignore
except ImportError:  # pragma: no cover
    pymssql = None  # type: ignore[assignment]

if pymssql:
    SQLSERVER_DRIVER_EXCEPTIONS: tuple[type[BaseException], ...] = (pymssql.Error,)
else:  # pragma: no cover - optional dependency
    SQLSERVER_DRIVER_EXCEPTIONS = ()

SQLSERVER_ADAPTER_EXCEPTIONS: tuple[type[BaseException], ...] = (ConnectionAdapterError, RuntimeError, LookupError, ValueError, TypeError, KeyError, AttributeError, ConnectionError, TimeoutError, OSError, *SQLSERVER_DRIVER_EXCEPTIONS)


class SQLServerAccountAdapter(BaseAccountAdapter):
    """SQL Server 账户同步适配器.

    实现 SQL Server 数据库的账户查询和权限采集功能.
    通过 sys.server_principals、sys.server_role_members、sys.database_principals 等视图采集登录信息和权限.
    支持批量优化查询,提高多用户权限采集效率.

    Attributes:
        logger: 同步日志记录器.
        filter_manager: 数据库过滤管理器.

    Example:
        >>> adapter = SQLServerAccountAdapter()
        >>> accounts = adapter.fetch_accounts(instance, connection)
        >>> enriched = adapter.enrich_permissions(instance, connection, accounts)

    """

    def __init__(self) -> None:
        """初始化 SQL Server 适配器,配置日志与过滤管理器."""
        self.logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()

    def _fetch_raw_accounts(self, instance: Instance, connection: object) -> list[RawAccount]:
        """拉取 SQL Server 原始账户信息.

        从 sys.server_principals 视图中查询登录基本信息.

        Args:
            instance: 实例对象.
            connection: SQL Server 数据库连接对象.

        Returns:
            原始账户信息列表,每个元素包含登录名、是否禁用、是否为系统管理员等.

        """
        try:
            users = self._fetch_logins(connection)
            accounts: list[RawAccount] = []
            for user in users:
                login_name = user["name"]
                is_disabled = user.get("is_disabled", False)
                is_superuser = user.get("is_sysadmin", False)
                accounts.append(
                    {
                        "username": login_name,
                        "is_superuser": is_superuser,
                        "is_disabled": is_disabled,
                        "permissions": {
                            "type_specific": {
                                "is_disabled": is_disabled,
                            },
                        },
                    },
                )
            self.logger.info(
                "fetch_sqlserver_accounts_success",
                module="sqlserver_account_adapter",
                instance=instance.name,
                account_count=len(accounts),
            )
            return accounts
        except SQLSERVER_ADAPTER_EXCEPTIONS as exc:
            self.logger.exception(
                "fetch_sqlserver_accounts_failed",
                module="sqlserver_account_adapter",
                instance=instance.name,
                error=str(exc),
            )
            return []

    def _normalize_account(self, instance: Instance, account: RawAccount) -> RemoteAccount:
        """规范化 SQL Server 账户信息.

        将原始账户信息转换为统一格式.

        Args:
            instance: 实例对象.
            account: 原始账户信息字典.

        Returns:
            规范化后的账户信息字典.

        """
        permissions = cast("PermissionSnapshot", account.get("permissions") or {})
        type_specific = cast("JsonDict", permissions.setdefault("type_specific", {}))
        if "is_disabled" not in type_specific:
            type_specific["is_disabled"] = bool(account.get("is_disabled", False))
        is_disabled = bool(type_specific.get("is_disabled", account.get("is_disabled", False)))
        type_specific["is_disabled"] = is_disabled
        return {
            "username": account["username"],
            "display_name": account["username"],
            "db_type": DatabaseType.SQLSERVER,
            "is_superuser": account.get("is_superuser", False),
            "is_locked": is_disabled,
            # SQL Server 登录被禁用仍视为清单内账户,仅通过 is_locked 字段表达锁定状态
            "is_active": True,
            "permissions": {
                "server_roles": permissions.get("server_roles", []),
                "server_permissions": permissions.get("server_permissions", []),
                "database_roles": permissions.get("database_roles", {}),
                "database_permissions": permissions.get("database_permissions", {}),
                "type_specific": permissions.get("type_specific", {}),
            },
        }

    def enrich_permissions(
        self,
        instance: Instance,
        connection: object,
        accounts: list[RemoteAccount],
        *,
        usernames: list[str] | None = None,
    ) -> list[RemoteAccount]:
        """丰富 SQL Server 账户的权限信息.

        为指定账户查询详细的权限信息,包括服务器角色、服务器权限、数据库角色和数据库权限.
        使用批量优化查询提高性能.

        Args:
            instance: 实例对象.
            connection: SQL Server 数据库连接对象.
            accounts: 账户信息列表.
            usernames: 可选的目标用户名列表.

        Returns:
            丰富后的账户信息列表.

        """
        target_usernames = {account["username"] for account in accounts} if usernames is None else set(usernames)
        if not target_usernames:
            return accounts

        usernames_list = list(target_usernames)
        server_roles_map = self._get_server_roles_bulk(connection, usernames_list)
        server_permissions_map = self._get_server_permissions_bulk(connection, usernames_list)
        db_batch_permissions = self._get_all_users_database_permissions_batch(connection, usernames_list)
        db_permissions_map: dict[str, JsonValue] = {
            login: cast("JsonValue", data.get("permissions", {})) for login, data in db_batch_permissions.items()
        }
        db_roles_map: dict[str, dict[str, list[str]]] = {
            login: data.get("roles", {}) for login, data in db_batch_permissions.items()
        }
        processed = 0
        for account in accounts:
            username = account.get("username")
            if not username or username not in target_usernames:
                continue
            processed += 1
            try:
                permissions = self._get_login_permissions(
                    connection,
                    username,
                    precomputed_server_roles=server_roles_map,
                    precomputed_server_permissions=server_permissions_map,
                    precomputed_db_roles=db_roles_map,
                    precomputed_db_permissions=db_permissions_map,
                )
                type_specific = cast("JsonDict", permissions.setdefault("type_specific", {}))
                existing_type_specific = cast(
                    "JsonDict",
                    account.get("permissions", {}).get("type_specific", {}) or {},
                )
                for key, value in existing_type_specific.items():
                    if value is not None:
                        type_specific.setdefault(key, value)
                type_specific.setdefault("is_disabled", bool(account.get("is_disabled", False)))
                account["permissions"] = permissions
                account["is_locked"] = bool(type_specific.get("is_disabled", False))
            except SQLSERVER_ADAPTER_EXCEPTIONS as exc:
                self.logger.exception(
                    "fetch_sqlserver_permissions_failed",
                    module="sqlserver_account_adapter",
                    instance=instance.name,
                    username=username,
                    error=str(exc),
                )
                account.setdefault("permissions", {}).setdefault("errors", []).append(str(exc))

        self.logger.info(
            "fetch_sqlserver_permissions_completed",
            module="sqlserver_account_adapter",
            instance=instance.name,
            processed_accounts=processed,
        )
        return accounts

    # ------------------------------------------------------------------
    # 查询逻辑来源于旧实现
    # ------------------------------------------------------------------
    def _fetch_logins(self, connection: object) -> list[RawAccount]:
        """查询服务器登录账户.

        Args:
            connection: SQL Server 数据库连接.

        Returns:
            list[RawAccount]: 过滤后的登录列表,包含名称、类型与状态.

        """
        filter_rules = self.filter_manager.get_filter_rules("sqlserver")
        exclude_users = filter_rules.get("exclude_users", [])
        exclude_patterns = self._compile_like_patterns(filter_rules.get("exclude_patterns"))

        sql = """
            SELECT
                sp.name,
                sp.type_desc,
                sp.is_disabled,
                IS_SRVROLEMEMBER('sysadmin', sp.name) AS is_sysadmin
            FROM sys.server_principals sp
            WHERE sp.type IN ('S', 'U', 'G')
        """
        params: list[str] = []
        if exclude_users:
            placeholders = ", ".join(["%s"] * len(exclude_users))
            sql += f" AND sp.name NOT IN ({placeholders})"
            params.extend(exclude_users)
        rows = connection.execute_query(sql, tuple(params) if params else None)

        results: list[RawAccount] = []
        for row in rows:
            name = row[0]
            if any(pattern.match(name) for pattern in exclude_patterns):
                continue
            results.append(
                {
                    "name": name,
                    "type_desc": row[1],
                    "is_disabled": bool(row[2]),
                    "is_sysadmin": bool(row[3]),
                },
            )
        return results

    @staticmethod
    def _compile_like_patterns(patterns: Iterable[str] | None) -> list[Pattern[str]]:
        """将 SQL LIKE 模式编译为正则表达式.

        Args:
            patterns: LIKE 模式集合,支持 % 与 _.

        Returns:
            list[Pattern[str]]: 可复用的忽略大小写正则列表.

        """
        compiled: list[Pattern[str]] = []
        if not patterns:
            return compiled
        for pattern in patterns:
            if not pattern:
                continue
            regex_parts = ["^"]
            for ch in pattern:
                if ch == "%":
                    regex_parts.append(".*")
                elif ch == "_":
                    regex_parts.append(".")
                else:
                    regex_parts.append(re.escape(ch))
            regex_parts.append("$")
            compiled.append(re.compile("".join(regex_parts), re.IGNORECASE))
        return compiled

    def _get_login_permissions(
        self,
        connection: object,
        login_name: str,
        *,
        precomputed_server_roles: dict[str, list[str]] | None = None,
        precomputed_server_permissions: dict[str, list[str]] | None = None,
        precomputed_db_roles: dict[str, dict[str, list[str]]] | None = None,
        precomputed_db_permissions: dict[str, JsonValue] | None = None,
    ) -> PermissionSnapshot:
        """组装登录账户的权限快照.

        Args:
            connection: SQL Server 连接(预留以便后续自定义查询).
            login_name: 登录名.
            precomputed_server_roles: 预先查询的服务器角色映射.
            precomputed_server_permissions: 预先查询的服务器权限映射.
            precomputed_db_roles: 预先查询的数据库角色映射.
            precomputed_db_permissions: 预先查询的数据库权限映射.

        Returns:
            PermissionSnapshot: server/database 角色与权限的聚合结果.

        """
        server_roles = self._deduplicate_preserve_order(
            (precomputed_server_roles or {}).get(login_name, []),
        )
        server_permissions = self._deduplicate_preserve_order(
            (precomputed_server_permissions or {}).get(login_name, []),
        )
        database_roles = {
            db_name: self._deduplicate_preserve_order(roles or [])
            for db_name, roles in ((precomputed_db_roles or {}).get(login_name) or {}).items()
        }
        database_permissions = self._copy_database_permissions(
            (precomputed_db_permissions or {}).get(login_name) or {},
        )

        return {
            "server_roles": server_roles,
            "server_permissions": server_permissions,
            "database_roles": database_roles,
            "database_permissions": database_permissions,
            "type_specific": {},
        }

    @staticmethod
    def _deduplicate_preserve_order(values: Sequence[str] | None) -> list[str]:
        """去重并保持原始顺序.

        Args:
            values: 待处理的序列.

        Returns:
            list[str]: 去重后的新列表.

        """
        if not values:
            return []
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value is None:
                continue
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _copy_database_permissions(self, data: dict[str, JsonValue] | None) -> dict[str, JsonValue]:
        """深拷贝数据库权限结构并去重.

        Args:
            data: 预计算的权限结构.

        Returns:
            dict[str, JsonValue]: 适合序列化/返回的副本.

        """
        if not data:
            return {}

        copied: dict[str, JsonValue] = {}
        for db_name, perms in data.items():
            if not db_name:
                continue
            if isinstance(perms, dict):
                db_entry: JsonDict = {
                    "database": self._deduplicate_preserve_order(perms.get("database", [])),
                    "schema": {},
                    "table": {},
                }
                schema_map = perms.get("schema") or {}
                db_entry["schema"] = {
                    schema_name: self._deduplicate_preserve_order(values)
                    for schema_name, values in schema_map.items()
                    if schema_name
                }
                table_map = perms.get("table") or {}
                db_entry["table"] = {
                    table_name: self._deduplicate_preserve_order(values)
                    for table_name, values in table_map.items()
                    if table_name
                }
                column_map = perms.get("column") or {}
                if column_map:
                    db_entry["column"] = {
                        column_name: self._deduplicate_preserve_order(values)
                        for column_name, values in column_map.items()
                        if column_name
                    }
                copied[db_name] = db_entry
            elif isinstance(perms, list):
                copied[db_name] = self._deduplicate_preserve_order(cast("Sequence[str]", perms))
        return copied

    def _get_server_roles_bulk(self, connection: object, usernames: Sequence[str]) -> dict[str, list[str]]:
        """批量查询服务器角色.

        Args:
            connection: SQL Server 连接.
            usernames: 登录名列表.

        Returns:
            dict[str, list[str]]: 登录名到角色列表的映射.

        """
        normalized = [name for name in usernames if name]
        if not normalized:
            return {}

        placeholders = ", ".join(["%s"] * len(normalized))
        sql = f"""
            SELECT member.name AS login_name, role.name AS role_name
            FROM sys.server_role_members rm
            JOIN sys.server_principals role ON rm.role_principal_id = role.principal_id
            JOIN sys.server_principals member ON rm.member_principal_id = member.principal_id
            WHERE member.name IN ({placeholders})
        """
        rows = connection.execute_query(sql, tuple(normalized))
        result: dict[str, list[str]] = {}
        for login_name, role_name in rows:
            if not login_name or not role_name:
                continue
            result.setdefault(login_name, []).append(role_name)
        for login_name, roles in result.items():
            result[login_name] = self._deduplicate_preserve_order(roles)
        return result

    def _get_server_permissions_bulk(self, connection: object, usernames: Sequence[str]) -> dict[str, list[str]]:
        """批量查询服务器权限.

        Args:
            connection: SQL Server 连接.
            usernames: 登录名列表.

        Returns:
            dict[str, list[str]]: 登录名到权限列表的映射.

        """
        normalized = [name for name in usernames if name]
        if not normalized:
            return {}

        placeholders = ", ".join(["%s"] * len(normalized))
        sql = f"""
            SELECT sp.name AS login_name, perm.permission_name
            FROM sys.server_permissions perm
            JOIN sys.server_principals sp ON perm.grantee_principal_id = sp.principal_id
            WHERE sp.name IN ({placeholders})
        """
        rows = connection.execute_query(sql, tuple(normalized))
        result: dict[str, list[str]] = {}
        for login_name, permission_name in rows:
            if not login_name or not permission_name:
                continue
            result.setdefault(login_name, []).append(permission_name)
        for login_name, permissions in result.items():
            result[login_name] = self._deduplicate_preserve_order(permissions)
        return result

    def _get_all_users_database_permissions_batch(
        self,
        connection: object,
        usernames: Sequence[str],
    ) -> dict[str, JsonDict]:
        """批量查询所有用户的数据库权限(优化版).

        通过 UNION ALL 合并多个数据库的查询,一次性获取所有用户在所有数据库中的权限信息.
        显著提高多用户、多数据库场景下的查询效率.

        Args:
            connection: SQL Server 数据库连接对象.
            usernames: 用户名列表.

        Returns:
            用户权限字典,键为登录名,值包含角色和权限信息.
            格式:{
                'login_name': {
                    'roles': {'db_name': ['role1', 'role2']},
                    'permissions': {'db_name': {'database': [...], 'schema': {...}, 'table': {...}}}
                }
            }

        """
        usernames = [name for name in usernames if name]
        if not usernames:
            return {}

        start_time = time.perf_counter()
        try:
            databases_sql = """
                SELECT name
                FROM sys.databases
                WHERE state = 0
                  AND HAS_DBACCESS(name) = 1
                ORDER BY name
            """
            database_rows = connection.execute_query(databases_sql)
            database_list = [row[0] for row in database_rows if row and row[0]]
            if not database_list:
                return {}

            unique_usernames = list(dict.fromkeys(usernames))
            placeholders = ", ".join(["%s"] * len(unique_usernames))
            login_sids_sql = f"""
                SELECT name, sid
                FROM sys.server_principals
                WHERE name IN ({placeholders})
                  AND type IN ('S', 'U', 'G')
            """
            login_rows = connection.execute_query(login_sids_sql, tuple(unique_usernames))
            sid_to_logins: dict[bytes, list[str]] = {}
            for login_name, raw_sid in login_rows:
                normalized_sid = self._normalize_sid(raw_sid)
                if not login_name or normalized_sid is None:
                    continue
                sid_to_logins.setdefault(normalized_sid, []).append(login_name)

            if not sid_to_logins:
                return {}

            sid_literals = [literal for sid in sid_to_logins for literal in [self._sid_to_hex_literal(sid)] if literal]
            if not sid_literals:
                return {}
            sid_filter = ", ".join(sid_literals)

            principals_parts: list[str] = []
            roles_parts: list[str] = []
            perms_parts: list[str] = []

            for db in database_list:
                quoted_db = self._quote_identifier(db)
                principals_parts.append(
                    f"""
                    SELECT '{db}' AS db_name,
                           name COLLATE SQL_Latin1_General_CP1_CI_AS AS user_name,
                           principal_id,
                           sid
                    FROM {quoted_db}.sys.database_principals
                    WHERE type IN ('S', 'U', 'G')
                      AND name != 'dbo'
                      AND sid IN ({sid_filter})
                    """,
                )

                roles_parts.append(
                    f"""
                    SELECT '{db}' AS db_name,
                           role.name COLLATE SQL_Latin1_General_CP1_CI_AS AS role_name,
                           member.principal_id AS member_principal_id
                    FROM {quoted_db}.sys.database_role_members drm
                    JOIN {quoted_db}.sys.database_principals role
                      ON drm.role_principal_id = role.principal_id
                    JOIN {quoted_db}.sys.database_principals member
                      ON drm.member_principal_id = member.principal_id
                    WHERE member.sid IN ({sid_filter})
                    """,
                )

                perms_parts.append(
                    f"""
                    SELECT '{db}' AS db_name,
                           perm.permission_name COLLATE SQL_Latin1_General_CP1_CI_AS AS permission_name,
                           perm.grantee_principal_id,
                           perm.major_id,
                           perm.minor_id,
                           CASE
                               WHEN perm.class_desc = 'DATABASE' THEN 'DATABASE'
                               WHEN perm.class_desc = 'SCHEMA' THEN 'SCHEMA'
                               WHEN perm.class_desc = 'OBJECT_OR_COLUMN' AND perm.minor_id = 0 THEN 'OBJECT'
                               WHEN perm.class_desc = 'OBJECT_OR_COLUMN' AND perm.minor_id > 0 THEN 'COLUMN'
                               ELSE perm.class_desc
                           END AS permission_scope,
                           CASE
                               WHEN perm.class_desc = 'SCHEMA' THEN SCHEMA_NAME(perm.major_id)
                               WHEN perm.class_desc = 'OBJECT_OR_COLUMN' THEN OBJECT_SCHEMA_NAME(perm.major_id)
                               ELSE NULL
                           END AS schema_name,
                           CASE
                               WHEN perm.class_desc = 'OBJECT_OR_COLUMN' THEN OBJECT_NAME(perm.major_id)
                               ELSE NULL
                           END AS object_name,
                           CASE
                               WHEN perm.class_desc = 'OBJECT_OR_COLUMN' AND perm.minor_id > 0 THEN COL_NAME(perm.major_id, perm.minor_id)
                               ELSE NULL
                           END AS column_name
                    FROM {quoted_db}.sys.database_permissions perm
                    JOIN {quoted_db}.sys.database_principals dp
                      ON perm.grantee_principal_id = dp.principal_id
                    WHERE perm.state = 'G'
                      AND dp.sid IN ({sid_filter})
                    """,
                )

            principals_sql = " UNION ALL ".join(principals_parts)
            roles_sql = " UNION ALL ".join(roles_parts)
            perms_sql = " UNION ALL ".join(perms_parts)

            principal_rows = connection.execute_query(principals_sql)
            role_rows = connection.execute_query(roles_sql)
            permission_rows = connection.execute_query(perms_sql)

            principal_lookup: dict[str, dict[int, list[str]]] = {}
            for db_name, _, principal_id, sid in principal_rows:
                normalized_sid = self._normalize_sid(sid)
                if not db_name or principal_id is None or normalized_sid is None:
                    continue
                login_names = sid_to_logins.get(normalized_sid)
                if not login_names:
                    continue
                db_entry = principal_lookup.setdefault(db_name, {})
                db_entry.setdefault(principal_id, [])
                for login_name in login_names:
                    if login_name not in db_entry[principal_id]:
                        db_entry[principal_id].append(login_name)

            result: dict[str, JsonDict] = {login: {"roles": {}, "permissions": {}} for login in unique_usernames}

            for db_name, role_name, member_principal_id in role_rows:
                if not db_name or not role_name or member_principal_id is None:
                    continue
                login_names = principal_lookup.get(db_name, {}).get(member_principal_id)
                if not login_names:
                    continue
                for login_name in login_names:
                    roles = result.setdefault(login_name, {}).setdefault("roles", {})
                    role_list = roles.setdefault(db_name, [])
                    if role_name not in role_list:
                        role_list.append(role_name)

            for (
                db_name,
                permission_name,
                grantee_principal_id,
                _major_id,
                _minor_id,
                scope,
                schema_name,
                object_name,
                column_name,
            ) in permission_rows:
                if not db_name or not permission_name or grantee_principal_id is None:
                    continue
                login_names = principal_lookup.get(db_name, {}).get(grantee_principal_id)
                if not login_names:
                    continue
                for login_name in login_names:
                    permissions = result.setdefault(login_name, {}).setdefault("permissions", {})
                    db_entry = permissions.setdefault(
                        db_name,
                        {
                            "database": [],
                            "schema": {},
                            "table": {},
                            "column": {},
                        },
                    )
                    if scope == "DATABASE":
                        if permission_name not in db_entry["database"]:
                            db_entry["database"].append(permission_name)
                    elif scope == "SCHEMA" and schema_name:
                        schema_list = db_entry["schema"].setdefault(schema_name, [])
                        if permission_name not in schema_list:
                            schema_list.append(permission_name)
                    elif scope == "OBJECT" and object_name:
                        qualified_name = f"{schema_name}.{object_name}" if schema_name else object_name
                        table_list = db_entry["table"].setdefault(qualified_name, [])
                        if permission_name not in table_list:
                            table_list.append(permission_name)
                    elif scope == "COLUMN" and object_name and column_name:
                        qualified_name = f"{schema_name}.{object_name}" if schema_name else object_name
                        table_list = db_entry["table"].setdefault(qualified_name, [])
                        if permission_name not in table_list:
                            table_list.append(permission_name)
                        column_key = f"{qualified_name}.{column_name}"
                        column_list = db_entry["column"].setdefault(column_key, [])
                        if permission_name not in column_list:
                            column_list.append(permission_name)

            elapsed = time.perf_counter() - start_time
            self.logger.info(
                "sqlserver_batch_database_permissions_completed",
                module="sqlserver_account_adapter",
                user_count=len(unique_usernames),
                database_count=len(database_list),
                elapsed_time=f"{elapsed:.2f}s",
            )

            return result
        except SQLSERVER_ADAPTER_EXCEPTIONS as exc:
            self.logger.exception(
                "sqlserver_batch_database_permissions_failed",
                module="sqlserver_account_adapter",
                error=str(exc),
            )
            return {}

    @staticmethod
    def _normalize_sid(raw_sid: object) -> bytes | None:
        """标准化 SID 字节串.

        Args:
            raw_sid: 可能为 bytes/memoryview 等类型的 SID.

        Returns:
            bytes | None: 统一转换后的字节串,无法转换则返回 None.

        """
        if raw_sid is None:
            return None
        if isinstance(raw_sid, memoryview):
            return raw_sid.tobytes()
        if isinstance(raw_sid, bytearray):
            return bytes(raw_sid)
        if isinstance(raw_sid, bytes):
            return raw_sid
        return None

    @staticmethod
    def _sid_to_hex_literal(sid: bytes | None) -> str | None:
        """将 SID 字节串转换为十六进制文本表示.

        Args:
            sid: SID 字节串.

        Returns:
            str | None: 形如 0x... 的字面值,sid 为空时返回 None.

        """
        if not sid:
            return None
        return "0x" + sid.hex()

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """为 SQL Server 标识符加方括号并转义.

        Args:
            identifier: 原始标识符.

        Returns:
            str: 已转义并包裹方括号的标识符.

        """
        safe_identifier = identifier.replace("]", "]]")
        return f"[{safe_identifier}]"

    # 缓存操作
