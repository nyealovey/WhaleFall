"""SQL Server 账户同步适配器(两阶段版)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
import json
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from app.constants import DatabaseType
from app.services.accounts_sync.accounts_sync_filters import DatabaseFilterManager
from app.services.accounts_sync.adapters.base_adapter import BaseAccountAdapter
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.utils.structlog_config import get_sync_logger

if TYPE_CHECKING:
    from re import Pattern

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
    SyncConnection = Any

import pymssql  # type: ignore[import-not-found]

SQLSERVER_DRIVER_EXCEPTIONS: tuple[type[BaseException], ...] = (pymssql.Error,)

SQLSERVER_ADAPTER_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionAdapterError,
    RuntimeError,
    LookupError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    ConnectionError,
    TimeoutError,
    OSError,
    *SQLSERVER_DRIVER_EXCEPTIONS,
)

SQLSERVER_DATABASE_PERMISSION_BATCH_SIZE = 20


@dataclass(frozen=True)
class DatabasePermissionTemplates:
    """封装数据库权限查询模板."""

    principals: str
    roles: str
    permissions: str


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

    @staticmethod
    def _normalize_str(value: object) -> str | None:
        """将输入转换为字符串,非字符串返回 None."""
        if isinstance(value, (str, bytes, bytearray)):
            return str(value)
        return None

    @staticmethod
    def _normalize_str_list(value: object) -> list[str]:
        """将序列转换为字符串列表,忽略非字符串元素."""
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [str(item) for item in value if isinstance(item, (str, bytes, bytearray))]
        return []

    @staticmethod
    def _get_connection(connection: object) -> SyncConnection:
        """将泛型连接对象转换为同步查询协议."""
        return cast("SyncConnection", connection)

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
        except SQLSERVER_ADAPTER_EXCEPTIONS as exc:
            self.logger.exception(
                "fetch_sqlserver_accounts_failed",
                module="sqlserver_account_adapter",
                instance=instance.name,
                error=str(exc),
            )
            return []
        else:
            accounts: list[RawAccount] = []
            for user in users:
                login_name = self._normalize_str(user.get("name"))
                if not login_name:
                    continue
                is_disabled = bool(user.get("is_disabled", False))
                is_superuser = bool(user.get("is_sysadmin", False))
                permissions: PermissionSnapshot = {
                    "type_specific": {
                        "is_disabled": is_disabled,
                    },
                }
                accounts.append(
                    {
                        "username": login_name,
                        "is_superuser": is_superuser,
                        "is_disabled": is_disabled,
                        "permissions": permissions,
                    },
                )
            self.logger.info(
                "fetch_sqlserver_accounts_success",
                module="sqlserver_account_adapter",
                instance=instance.name,
                account_count=len(accounts),
            )
            return accounts

    def _normalize_account(self, instance: Instance, account: RawAccount) -> RemoteAccount:
        """规范化 SQL Server 账户信息.

        将原始账户信息转换为统一格式.

        Args:
            instance: 实例对象.
            account: 原始账户信息字典.

        Returns:
            规范化后的账户信息字典.

        """
        del instance
        username = self._normalize_str(account.get("username"))
        if not username:
            username = ""
        permissions = cast("PermissionSnapshot", account.get("permissions") or {})
        type_specific = cast("JsonDict", permissions.setdefault("type_specific", {}))
        if "is_disabled" not in type_specific:
            type_specific["is_disabled"] = bool(account.get("is_disabled", False))
        is_disabled = bool(type_specific.get("is_disabled", account.get("is_disabled", False)))
        type_specific["is_disabled"] = is_disabled
        is_superuser = bool(account.get("is_superuser", False))
        normalized_permissions: PermissionSnapshot = {
            "server_roles": permissions.get("server_roles", []),
            "server_permissions": permissions.get("server_permissions", []),
            "database_roles": permissions.get("database_roles", {}),
            "database_permissions": permissions.get("database_permissions", {}),
            "type_specific": type_specific,
        }
        return {
            "username": username,
            "display_name": username,
            "db_type": DatabaseType.SQLSERVER,
            "is_superuser": is_superuser,
            "is_locked": bool(is_disabled),
            # SQL Server 登录被禁用仍视为清单内账户,仅通过 is_locked 字段表达锁定状态
            "is_active": True,
            "permissions": normalized_permissions,
        }

    def enrich_permissions(
        self,
        instance: Instance,
        connection: object,
        accounts: list[RemoteAccount],
        *,
        usernames: Sequence[str] | None = None,
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
            login: cast(
                "JsonValue",
                data.get("permissions") if isinstance(data, dict) else {},
            )
            for login, data in db_batch_permissions.items()
        }
        db_roles_map: dict[str, dict[str, list[str]]] = {
            login: cast(
                dict[str, list[str]],
                data.get("roles") if isinstance(data, dict) and isinstance(data.get("roles"), dict) else {},
            )
            for login, data in db_batch_permissions.items()
        }
        processed = 0
        for account in accounts:
            username = account.get("username")
            if not username or username not in target_usernames:
                continue
            processed += 1
            try:
                permissions = self._get_login_permissions(
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
        conn = self._get_connection(connection)
        rows = conn.execute_query(sql, tuple(params) if params else None)

        results: list[RawAccount] = []
        for row in rows:
            raw_name = row[0] if row else None
            name = self._normalize_str(raw_name)
            if not name:
                continue
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
        login_name: str,
        *,
        precomputed_server_roles: dict[str, list[str]] | None = None,
        precomputed_server_permissions: dict[str, list[str]] | None = None,
        precomputed_db_roles: dict[str, dict[str, list[str]]] | None = None,
        precomputed_db_permissions: dict[str, JsonValue] | None = None,
    ) -> PermissionSnapshot:
        """组装登录账户的权限快照.

        Args:
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

        permissions: PermissionSnapshot = {
            "server_roles": server_roles,
            "server_permissions": server_permissions,
            "database_roles": database_roles,
            "database_permissions": database_permissions,
            "type_specific": {},
        }
        return permissions

    @staticmethod
    def _deduplicate_preserve_order(values: object) -> list[str]:
        """去重并保持原始顺序.

        Args:
            values: 待处理的序列.

        Returns:
            list[str]: 去重后的新列表.

        """
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
            return []
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = value if isinstance(value, (str, bytes, bytearray)) else None
            if normalized is None:
                continue
            stringified = str(normalized)
            if stringified not in seen:
                seen.add(stringified)
                result.append(stringified)
        return result

    def _copy_database_permissions(self, data: object) -> dict[str, JsonValue]:
        """深拷贝数据库权限结构并去重.

        Args:
            data: 预计算的权限结构.

        Returns:
            dict[str, JsonValue]: 适合序列化/返回的副本.

        """
        if not isinstance(data, dict) or not data:
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

        login_payload = json.dumps(normalized, ensure_ascii=False)
        sql = """
            WITH target_logins AS (
                SELECT value COLLATE SQL_Latin1_General_CP1_CI_AS AS login_name
                FROM OPENJSON(%s)
            )
            SELECT member.name AS login_name, role.name AS role_name
            FROM sys.server_role_members rm
            JOIN sys.server_principals role ON rm.role_principal_id = role.principal_id
            JOIN sys.server_principals member ON rm.member_principal_id = member.principal_id
            JOIN target_logins ON member.name COLLATE SQL_Latin1_General_CP1_CI_AS = target_logins.login_name
        """
        conn = self._get_connection(connection)
        rows = conn.execute_query(sql, (login_payload,))
        result: dict[str, list[str]] = {}
        for login_name, role_name in rows:
            normalized_login = self._normalize_str(login_name)
            normalized_role = self._normalize_str(role_name)
            if not normalized_login or not normalized_role:
                continue
            result.setdefault(normalized_login, []).append(normalized_role)
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

        login_payload = json.dumps(normalized, ensure_ascii=False)
        sql = """
            WITH target_logins AS (
                SELECT value COLLATE SQL_Latin1_General_CP1_CI_AS AS login_name
                FROM OPENJSON(%s)
            )
            SELECT sp.name AS login_name, perm.permission_name
            FROM sys.server_permissions perm
            JOIN sys.server_principals sp ON perm.grantee_principal_id = sp.principal_id
            JOIN target_logins ON sp.name COLLATE SQL_Latin1_General_CP1_CI_AS = target_logins.login_name
        """
        conn = self._get_connection(connection)
        rows = conn.execute_query(sql, (login_payload,))
        result: dict[str, list[str]] = {}
        for login_name, permission_name in rows:
            normalized_login = self._normalize_str(login_name)
            normalized_permission = self._normalize_str(permission_name)
            if not normalized_login or not normalized_permission:
                continue
            result.setdefault(normalized_login, []).append(normalized_permission)
        for login_name, permissions in result.items():
            result[login_name] = self._deduplicate_preserve_order(permissions)
        return result

    def _get_all_users_database_permissions_batch(
        self,
        connection: object,
        usernames: Sequence[str],
    ) -> dict[str, JsonDict]:
        """批量查询所有用户的数据库权限(优化版).

        通过 UNION ALL 合并多个数据库的查询,并按批次执行,获取所有用户在所有数据库中的权限信息.
        在多用户、多数据库场景下,分批可以避免单条 SQL 过长导致编译/优化开销过大.

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
            database_list = self._get_accessible_databases(connection)
            if not database_list:
                return {}

            batch_size = SQLSERVER_DATABASE_PERMISSION_BATCH_SIZE
            if batch_size <= 0:
                batch_size = len(database_list)
            database_batch_count = (len(database_list) + batch_size - 1) // batch_size

            sid_to_logins, sid_payload = self._map_sids_to_logins(connection, usernames)
            if sid_to_logins and sid_payload:
                unique_usernames = list(dict.fromkeys(usernames))
                merged: dict[str, dict[str, Any]] = {
                    login: {"roles": {}, "permissions": {}} for login in unique_usernames
                }
                for offset in range(0, len(database_list), batch_size):
                    database_batch = database_list[offset : offset + batch_size]
                    principal_sql, roles_sql, perms_sql = self._build_database_permission_queries(database_batch)
                    principal_rows, role_rows, permission_rows = self._fetch_principal_data(
                        connection,
                        principal_sql,
                        roles_sql,
                        perms_sql,
                        sid_payload,
                    )
                    principal_lookup = self._build_principal_lookup(principal_rows, sid_to_logins)
                    self._apply_role_rows(merged, role_rows, principal_lookup)
                    self._apply_permission_rows(merged, permission_rows, principal_lookup)

                result: dict[str, JsonDict] = {login: cast(JsonDict, payload) for login, payload in merged.items()}

                # 若 SID 路径未返回任何角色/权限,尝试按用户名回退
                if self._is_permissions_empty(result):
                    self.logger.info(
                        "sqlserver_batch_permissions_sid_empty_fallback",
                        module="sqlserver_account_adapter",
                        user_count=len(set(usernames)),
                        database_count=len(database_list),
                        database_batch_size=batch_size,
                        database_batch_count=database_batch_count,
                    )
                    result = self._get_database_permissions_by_name(connection, usernames, database_list)
            else:
                # 回退到基于用户名的查询,避免因无法读取 SID 而导致权限为空
                result = self._get_database_permissions_by_name(connection, usernames, database_list)

            elapsed = time.perf_counter() - start_time
        except SQLSERVER_ADAPTER_EXCEPTIONS as exc:
            self.logger.exception(
                "sqlserver_batch_database_permissions_failed",
                module="sqlserver_account_adapter",
                error=str(exc),
            )
            return {}
        else:
            elapsed = time.perf_counter() - start_time
            self.logger.info(
                "sqlserver_batch_database_permissions_completed",
                module="sqlserver_account_adapter",
                user_count=len(set(usernames)),
                database_count=len(database_list),
                database_batch_size=batch_size,
                database_batch_count=database_batch_count,
                elapsed_time=f"{elapsed:.2f}s",
            )
            return result

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

    def _get_accessible_databases(self, connection: object) -> list[str]:
        """获取可访问数据库列表."""
        databases_sql = """
            SELECT name
            FROM sys.databases
            WHERE state = 0
              AND HAS_DBACCESS(name) = 1
            ORDER BY name
        """
        conn = self._get_connection(connection)
        rows = conn.execute_query(databases_sql)
        return [
            db_name
            for row in rows
            for db_name in [self._normalize_str(row[0]) if row and len(row) > 0 else None]
            if db_name
        ]

    def _map_sids_to_logins(
        self,
        connection: object,
        usernames: Sequence[str],
    ) -> tuple[dict[bytes, list[str]], str]:
        """构建 SID 到登录名的映射以及用于筛选的 JSON 负载."""
        unique_usernames = [name for name in dict.fromkeys(usernames) if name]
        if not unique_usernames:
            return {}, ""
        login_payload = json.dumps(unique_usernames, ensure_ascii=False)
        login_sids_sql = """
            WITH target_logins AS (
                SELECT value COLLATE SQL_Latin1_General_CP1_CI_AS AS login_name
                FROM OPENJSON(%s)
            )
            SELECT sp.name, sp.sid
            FROM sys.server_principals sp
            JOIN target_logins ON sp.name COLLATE SQL_Latin1_General_CP1_CI_AS = target_logins.login_name
            WHERE sp.type IN ('S', 'U', 'G')
        """
        conn = self._get_connection(connection)
        login_rows = conn.execute_query(login_sids_sql, (login_payload,))
        sid_to_logins: dict[bytes, list[str]] = {}
        for login_name, raw_sid in login_rows:
            normalized_sid = self._normalize_sid(raw_sid)
            normalized_login = self._normalize_str(login_name)
            if not normalized_login or normalized_sid is None:
                continue
            sid_to_logins.setdefault(normalized_sid, []).append(normalized_login)

        sid_literals = [literal for sid in sid_to_logins for literal in [self._sid_to_hex_literal(sid)] if literal]
        if not sid_literals:
            return {}, ""
        sid_payload = json.dumps(sid_literals)
        return sid_to_logins, sid_payload

    def _build_database_permission_queries(
        self,
        database_list: list[str],
    ) -> tuple[str, str, str]:
        """拼接查询数据库 principals/roles/permissions 的 SQL."""
        sid_cte = self._target_sid_cte()
        templates = self._get_database_permission_templates()
        principals_sql = self._compose_database_union(database_list, templates.principals)
        roles_sql = self._compose_database_union(database_list, templates.roles)
        perms_sql = self._compose_database_union(database_list, templates.permissions)
        return (
            sid_cte + "\n" + principals_sql,
            sid_cte + "\n" + roles_sql,
            sid_cte + "\n" + perms_sql,
        )

    @staticmethod
    def _target_sid_cte() -> str:
        """返回 target_sids 公共 CTE.

        Returns:
            str: 去除首尾空白的 target_sids CTE 片段.

        """
        return (
            """
            WITH target_sids AS (
                SELECT CONVERT(VARBINARY(128), value, 1) AS sid_value
                FROM OPENJSON(%s)
            )
            """
        ).strip()

    def _compose_database_union(self, database_list: list[str], template: str) -> str:
        """将单库模板渲染为 UNION ALL 语句.

        Args:
            database_list: 可访问数据库名称列表.
            template: 含数据库占位符的 SQL 模板字符串.

        Returns:
            str: 拼接后的 UNION ALL SQL,列表为空时返回空字符串.

        """
        rendered = [self._render_database_template(template, db) for db in database_list]
        fragments = [item for item in rendered if item]
        return " UNION ALL ".join(fragments)

    @staticmethod
    def _render_database_template(template: str, database: str) -> str:
        """将模板中的占位符替换为具体数据库名.

        占位符:
            __DB_IDENTIFIER__ -> 安全的标识符 [db]
            __DB_LITERAL__    -> 纯文本字面量 db
        """
        if not database:
            return ""
        identifier = SQLServerAccountAdapter._quote_identifier(database)
        return (
            template.replace("__DB_IDENTIFIER__", identifier)
            .replace("__DB_LITERAL__", database)
            .strip()
        )

    def _get_database_permission_templates(self) -> DatabasePermissionTemplates:
        """构建数据库权限查询模板集合.

        Returns:
            DatabasePermissionTemplates: 包含 principal/role/permission 查询片段的模板对象.

        """
        return DatabasePermissionTemplates(
            principals="""
                SELECT '__DB_LITERAL__' AS db_name,
                       name COLLATE SQL_Latin1_General_CP1_CI_AS AS user_name,
                       principal_id,
                       sid
                FROM __DB_IDENTIFIER__.sys.database_principals
                WHERE type IN ('S', 'U', 'G')
                  AND name != 'dbo'
                  AND sid IN (SELECT sid_value FROM target_sids)
            """,
            roles="""
                SELECT '__DB_LITERAL__' AS db_name,
                       role.name COLLATE SQL_Latin1_General_CP1_CI_AS AS role_name,
                       member.principal_id AS member_principal_id
                FROM __DB_IDENTIFIER__.sys.database_role_members drm
                JOIN __DB_IDENTIFIER__.sys.database_principals role
                  ON drm.role_principal_id = role.principal_id
                JOIN __DB_IDENTIFIER__.sys.database_principals member
                  ON drm.member_principal_id = member.principal_id
                WHERE member.sid IN (SELECT sid_value FROM target_sids)
            """,
            permissions="""
                SELECT '__DB_LITERAL__' AS db_name,
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
                           WHEN perm.class_desc = 'OBJECT_OR_COLUMN' AND perm.minor_id > 0 THEN (
                               COL_NAME(perm.major_id, perm.minor_id)
                           )
                           ELSE NULL
                       END AS column_name
                FROM __DB_IDENTIFIER__.sys.database_permissions perm
                JOIN __DB_IDENTIFIER__.sys.database_principals dp
                  ON perm.grantee_principal_id = dp.principal_id
                WHERE perm.state = 'G'
                  AND dp.sid IN (SELECT sid_value FROM target_sids)
            """,
        )

    @staticmethod
    def _fetch_principal_data(
        connection: object,
        principal_sql: str,
        roles_sql: str,
        perms_sql: str,
        sid_payload: str,
    ) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], list[tuple[Any, ...]]]:
        """执行合并后的 SQL 并返回结果."""
        params = (sid_payload,)
        conn = cast("SyncConnection", connection)
        principal_rows = [tuple(row) for row in conn.execute_query(principal_sql, params)]
        role_rows = [tuple(row) for row in conn.execute_query(roles_sql, params)]
        permission_rows = [tuple(row) for row in conn.execute_query(perms_sql, params)]
        return principal_rows, role_rows, permission_rows

    def _build_principal_lookup(
        self,
        principal_rows: Sequence[tuple[Any, ...]],
        sid_to_logins: dict[bytes, list[str]],
    ) -> dict[str, dict[int, list[str]]]:
        """构建数据库 + principal_id 到登录名的映射."""
        principal_lookup: dict[str, dict[int, list[str]]] = {}
        for db_name, _, principal_id, sid in principal_rows:
            normalized_sid = self._normalize_sid(sid)
            normalized_db = self._normalize_str(db_name)
            if not normalized_db or principal_id is None or normalized_sid is None:
                continue
            login_names = sid_to_logins.get(normalized_sid)
            if not login_names:
                continue
            db_entry = principal_lookup.setdefault(normalized_db, {})
            target = db_entry.setdefault(principal_id, [])
            for login_name in login_names:
                if login_name not in target:
                    target.append(login_name)
        return principal_lookup

    def _aggregate_database_permissions(
        self,
        usernames: Sequence[str],
        role_rows: Sequence[tuple[Any, ...]],
        permission_rows: Sequence[tuple[Any, ...]],
        principal_lookup: dict[str, dict[int, list[str]]],
    ) -> dict[str, JsonDict]:
        """根据查询结果组装最终权限结构."""
        unique_usernames = list(dict.fromkeys(usernames))
        result: dict[str, dict[str, Any]] = {login: {"roles": {}, "permissions": {}} for login in unique_usernames}
        self._apply_role_rows(result, role_rows, principal_lookup)
        self._apply_permission_rows(result, permission_rows, principal_lookup)
        return {login: cast(JsonDict, payload) for login, payload in result.items()}

    @staticmethod
    def _ensure_dict(container: dict[str, Any], key: str) -> dict[str, Any]:
        value = container.get(key)
        if isinstance(value, dict):
            return value
        container[key] = {}
        return cast("dict[str, Any]", container[key])

    @staticmethod
    def _ensure_list(container: dict[str, Any], key: str) -> list[Any]:
        value = container.get(key)
        if isinstance(value, list):
            return value
        container[key] = []
        return cast("list[Any]", container[key])

    def _apply_role_rows(
        self,
        result: dict[str, dict[str, Any]],
        role_rows: Sequence[tuple[Any, ...]],
        principal_lookup: dict[str, dict[int, list[str]]],
    ) -> None:
        for db_name, role_name, member_principal_id in role_rows:
            if not db_name or not role_name or member_principal_id is None:
                continue
            normalized_db = self._normalize_str(db_name)
            normalized_role = self._normalize_str(role_name)
            if not normalized_db or not normalized_role:
                continue
            login_names = principal_lookup.get(normalized_db, {}).get(member_principal_id)
            if not login_names:
                continue
            for login_name in login_names:
                account_entry = result.setdefault(login_name, {"roles": {}, "permissions": {}})
                roles = self._ensure_dict(account_entry, "roles")
                role_list = self._ensure_list(roles, normalized_db)
                if normalized_role not in role_list:
                    role_list.append(normalized_role)

    def _apply_permission_rows(
        self,
        result: dict[str, dict[str, Any]],
        permission_rows: Sequence[tuple[Any, ...]],
        principal_lookup: dict[str, dict[int, list[str]]],
    ) -> None:
        for row in permission_rows:
            (
                db_name,
                permission_name,
                grantee_principal_id,
                _major_id,
                _minor_id,
                scope,
                schema_name,
                object_name,
                column_name,
            ) = row
            normalized_db = self._normalize_str(db_name)
            normalized_permission = self._normalize_str(permission_name)
            normalized_scope = self._normalize_str(scope)
            if not normalized_db or not normalized_permission or grantee_principal_id is None or not normalized_scope:
                continue
            login_names = principal_lookup.get(normalized_db, {}).get(grantee_principal_id)
            if not login_names:
                continue
            for login_name in login_names:
                account_entry = result.setdefault(login_name, {"roles": {}, "permissions": {}})
                permissions = self._ensure_dict(account_entry, "permissions")
                db_entry = permissions.get(normalized_db)
                if not isinstance(db_entry, dict):
                    db_entry = {
                        "database": [],
                        "schema": {},
                        "table": {},
                        "column": {},
                    }
                    permissions[normalized_db] = db_entry
                self._append_permission_entry(
                    cast("JsonDict", db_entry),
                    normalized_scope,
                    normalized_permission,
                    (schema_name, object_name),
                    column_name,
                )

    def _get_database_permissions_by_name(
        self,
        connection: object,
        usernames: Sequence[str],
        database_list: list[str],
    ) -> dict[str, JsonDict]:
        """基于用户名回退查询数据库权限,用于无法读取 SID 的场景."""
        login_payload = json.dumps([name for name in dict.fromkeys(usernames) if name], ensure_ascii=False)
        if not login_payload or not database_list:
            return {}

        batch_size = SQLSERVER_DATABASE_PERMISSION_BATCH_SIZE
        if batch_size <= 0:
            batch_size = len(database_list)

        unique_usernames = [name for name in dict.fromkeys(usernames) if name]
        merged: dict[str, dict[str, Any]] = {login: {"roles": {}, "permissions": {}} for login in unique_usernames}
        for offset in range(0, len(database_list), batch_size):
            database_batch = database_list[offset : offset + batch_size]
            principals_sql, roles_sql, perms_sql = self._build_db_permission_queries_by_name(database_batch)
            principal_rows, role_rows, permission_rows = self._fetch_principal_data_by_name(
                connection,
                principals_sql,
                roles_sql,
                perms_sql,
                login_payload,
            )
            principal_lookup = self._build_principal_lookup_by_name(principal_rows)
            self._apply_role_rows(merged, role_rows, principal_lookup)
            self._apply_permission_rows(merged, permission_rows, principal_lookup)

        return {login: cast(JsonDict, payload) for login, payload in merged.items()}

    def _build_db_permission_queries_by_name(self, database_list: list[str]) -> tuple[str, str, str]:
        """构建基于用户名匹配的数据库权限查询 SQL."""
        target_cte = (
            """
            WITH target_logins AS (
                SELECT value COLLATE SQL_Latin1_General_CP1_CI_AS AS login_name
                FROM OPENJSON(%s)
            )
            """
        ).strip()
        templates = DatabasePermissionTemplates(
            principals="""
                SELECT '__DB_LITERAL__' AS db_name,
                       dp.name COLLATE SQL_Latin1_General_CP1_CI_AS AS user_name,
                       dp.principal_id,
                       dp.sid
                FROM __DB_IDENTIFIER__.sys.database_principals dp
                JOIN target_logins tl ON dp.name COLLATE SQL_Latin1_General_CP1_CI_AS = tl.login_name
                WHERE dp.type IN ('S', 'U', 'G')
                  AND dp.name != 'dbo'
            """,
            roles="""
                SELECT '__DB_LITERAL__' AS db_name,
                       role.name COLLATE SQL_Latin1_General_CP1_CI_AS AS role_name,
                       member.principal_id AS member_principal_id
                FROM __DB_IDENTIFIER__.sys.database_role_members drm
                JOIN __DB_IDENTIFIER__.sys.database_principals role
                  ON drm.role_principal_id = role.principal_id
                JOIN __DB_IDENTIFIER__.sys.database_principals member
                  ON drm.member_principal_id = member.principal_id
                JOIN target_logins tl ON member.name COLLATE SQL_Latin1_General_CP1_CI_AS = tl.login_name
            """,
            permissions="""
                SELECT '__DB_LITERAL__' AS db_name,
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
                           WHEN perm.class_desc = 'OBJECT_OR_COLUMN' AND perm.minor_id > 0 THEN (
                               COL_NAME(perm.major_id, perm.minor_id)
                           )
                           ELSE NULL
                       END AS column_name
                FROM __DB_IDENTIFIER__.sys.database_permissions perm
                JOIN __DB_IDENTIFIER__.sys.database_principals dp
                  ON perm.grantee_principal_id = dp.principal_id
                JOIN target_logins tl ON dp.name COLLATE SQL_Latin1_General_CP1_CI_AS = tl.login_name
                WHERE perm.state = 'G'
            """,
        )
        principals_sql = target_cte + "\n" + self._compose_database_union(database_list, templates.principals)
        roles_sql = target_cte + "\n" + self._compose_database_union(database_list, templates.roles)
        perms_sql = target_cte + "\n" + self._compose_database_union(database_list, templates.permissions)
        return principals_sql, roles_sql, perms_sql

    @staticmethod
    def _fetch_principal_data_by_name(
        connection: object,
        principal_sql: str,
        roles_sql: str,
        perms_sql: str,
        login_payload: str,
    ) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], list[tuple[Any, ...]]]:
        """执行基于用户名的权限查询."""
        params = (login_payload,)
        conn = cast("SyncConnection", connection)
        principal_rows = [tuple(row) for row in conn.execute_query(principal_sql, params)]
        role_rows = [tuple(row) for row in conn.execute_query(roles_sql, params)]
        permission_rows = [tuple(row) for row in conn.execute_query(perms_sql, params)]
        return principal_rows, role_rows, permission_rows

    def _build_principal_lookup_by_name(
        self,
        principal_rows: Sequence[tuple[Any, ...]],
    ) -> dict[str, dict[int, list[str]]]:
        """从 username 直接构建 principal 映射."""
        principal_lookup: dict[str, dict[int, list[str]]] = {}
        for db_name, user_name, principal_id, _sid in principal_rows:
            normalized_db = self._normalize_str(db_name)
            normalized_user = self._normalize_str(user_name)
            if not normalized_db or principal_id is None or not normalized_user:
                continue
            db_entry = principal_lookup.setdefault(normalized_db, {})
            target = db_entry.setdefault(principal_id, [])
            if normalized_user not in target:
                target.append(normalized_user)
        return principal_lookup

    @staticmethod
    def _is_permissions_empty(result: dict[str, JsonDict]) -> bool:
        """判断聚合结果是否完全为空权限."""
        if not result:
            return True
        for payload in result.values():
            perms = payload.get("permissions") or {}
            roles = payload.get("roles") or {}
            if perms or roles:
                return False
        return True

    @staticmethod
    def _ensure_permission_list(container: JsonDict, key: str) -> list[str]:
        """确保权限容器中的指定键为列表并返回引用."""
        value = container.get(key)
        if isinstance(value, list):
            return cast("list[str]", value)
        container[key] = []
        return cast("list[str]", container[key])

    @staticmethod
    def _ensure_permission_map(container: JsonDict, key: str) -> dict[str, list[str]]:
        """确保权限容器中的指定键为映射并返回引用."""
        value = container.get(key)
        if isinstance(value, dict):
            return cast("dict[str, list[str]]", value)
        container[key] = {}
        return cast("dict[str, list[str]]", container[key])

    @staticmethod
    def _ensure_permission_list_in_map(container: dict[str, list[str]], key: str) -> list[str]:
        """确保映射中键对应列表并返回引用."""
        value = container.get(key)
        if isinstance(value, list):
            return value
        container[key] = []
        return container[key]

    def _append_permission_entry(
        self,
        db_entry: JsonDict,
        scope: str,
        permission_name: str,
        object_scope: tuple[str | None, str | None],
        column_name: str | None,
    ) -> None:
        """将权限写入对应层级."""
        if scope == "DATABASE":
            self._append_database_permission(db_entry, permission_name)
            return
        schema_name, object_name = object_scope
        if scope == "SCHEMA":
            self._append_schema_permission(db_entry, permission_name, schema_name)
            return
        self._append_object_permission(
            db_entry,
            permission_name,
            schema_name,
            object_name,
            column_name,
            scope,
        )

    def _append_database_permission(self, db_entry: JsonDict, permission_name: str) -> None:
        """记录数据库级权限."""
        database_list = self._ensure_permission_list(db_entry, "database")
        if permission_name not in database_list:
            database_list.append(permission_name)

    def _append_schema_permission(
        self, db_entry: JsonDict, permission_name: str, schema_name: str | None,
    ) -> None:
        """记录模式级权限."""
        if not schema_name:
            return
        schema_map = self._ensure_permission_map(db_entry, "schema")
        schema_list = self._ensure_permission_list_in_map(schema_map, schema_name)
        if permission_name not in schema_list:
            schema_list.append(permission_name)

    def _append_object_permission(
        self,
        db_entry: JsonDict,
        permission_name: str,
        schema_name: str | None,
        object_name: str | None,
        column_name: str | None,
        scope: str,
    ) -> None:
        """记录表或列级权限."""
        if not object_name:
            return
        table_map = self._ensure_permission_map(db_entry, "table")
        qualified_name = f"{schema_name}.{object_name}" if schema_name else object_name
        table_list = self._ensure_permission_list_in_map(table_map, qualified_name)
        if permission_name not in table_list:
            table_list.append(permission_name)
        if scope != "COLUMN" or not column_name:
            return
        column_map = self._ensure_permission_map(db_entry, "column")
        column_key = f"{qualified_name}.{column_name}"
        column_list = self._ensure_permission_list_in_map(column_map, column_key)
        if permission_name not in column_list:
            column_list.append(permission_name)

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
