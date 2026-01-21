"""MySQL账户同步适配器(两阶段版)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol, cast

from app.core.constants import DatabaseType
from app.schemas.external_contracts.mysql_account import MySQLRawAccountSchema
from app.services.accounts_sync.accounts_sync_filters import DatabaseFilterManager
from app.services.accounts_sync.adapters.base_adapter import BaseAccountAdapter
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.structlog_config import get_sync_logger

if TYPE_CHECKING:
    from app.core.types import JsonDict, PermissionSnapshot, RawAccount, RemoteAccount
    from app.models.instance import Instance


class _MySQLConnectionProtocol(Protocol):
    """最小化的 MySQL 连接协议,提供 execute_query 方法."""

    def execute_query(self, sql: str, params: Sequence[str] | None = None) -> Sequence[tuple[Any, ...]]: ...


class MySQLAccountAdapter(BaseAccountAdapter):
    """负责拉取 MySQL 账户信息与权限快照.

    实现 MySQL 数据库的账户查询和权限采集功能.
    通过 mysql.user 表和 SHOW GRANTS 语句采集账户信息和权限.

    Attributes:
        logger: 同步日志记录器.
        filter_manager: 数据库过滤管理器.

    Example:
        >>> adapter = MySQLAccountAdapter()
        >>> accounts = adapter.fetch_accounts(instance, connection)
        >>> enriched = adapter.enrich_permissions(instance, connection, accounts)

    """

    def __init__(self) -> None:
        """初始化 MySQL 账户适配器.

        准备结构化日志记录器以及过滤规则管理器,以便复用统一的过滤策略.

        """
        self.logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()

    MYSQL_ADAPTER_EXCEPTIONS: tuple[type[Exception], ...] = (
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        ConnectionError,
    )

    # ------------------------------------------------------------------
    # BaseAccountAdapter 实现
    # ------------------------------------------------------------------
    def _fetch_mysql_user_rows(
        self,
        conn: _MySQLConnectionProtocol,
        *,
        where_clause: str,
        params: Sequence[str],
        supports_roles: bool,
    ) -> tuple[Sequence[tuple[Any, ...]], bool]:
        user_select = (
            "SELECT "
            "    User as username, "
            "    Host as host, "
            "    Super_priv as is_superuser, "
            "    account_locked as is_locked, "
            "    Grant_priv as can_grant, "
            "    plugin as plugin, "
            "    password_last_changed as password_last_changed"
        )
        user_from_where = " FROM mysql.user " "WHERE " + where_clause + " ORDER BY User, Host"

        user_sql = user_select + (", is_role as is_role" if supports_roles else "") + user_from_where

        has_is_role_column = supports_roles
        try:
            users = conn.execute_query(user_sql, params)
        except self.MYSQL_ADAPTER_EXCEPTIONS as exc:
            # 部分 MySQL 兼容实现/托管版会隐藏 mysql.user 的 is_role 列，即使版本号为 8.x。
            # 这种情况下退回到不选 is_role，并通过 role_edges/default_roles 推断角色集合。
            error_message = str(exc).lower()
            if supports_roles and "unknown column" in error_message and "is_role" in error_message:
                has_is_role_column = False
                users = conn.execute_query(user_select + user_from_where, params)
            else:
                raise
        return users, has_is_role_column

    def _fetch_assigned_role_usernames(self, connection: object) -> set[str]:
        direct_map, default_map = self._prefetch_roles(connection, target_usernames=set())
        role_usernames: set[str] = set()
        for roles in direct_map.values():
            role_usernames.update(roles)
        for roles in default_map.values():
            role_usernames.update(roles)
        return role_usernames

    def _fetch_raw_accounts(self, instance: Instance, connection: object) -> list[RawAccount]:
        """拉取 MySQL 原始账户信息.

        从 mysql.user 表中查询账户基本信息,包括用户名、主机、超级用户标志等.

        Args:
            instance: 实例对象.
            connection: MySQL 数据库连接对象.

        Returns:
            原始账户信息列表,每个元素包含:
            - username: 唯一用户名(格式:user@host)
            - is_superuser: 是否为超级用户
            - is_locked: 是否被锁定
            - permissions: 权限信息字典

        Example:
            >>> accounts = adapter._fetch_raw_accounts(instance, connection)
            >>> print(accounts[0])
            {
                'username': 'root@localhost',
                'is_superuser': True,
                'is_locked': False,
                'permissions': {...}
            }

        """
        try:
            where_clause, params = self._build_filter_conditions()
            conn = cast(_MySQLConnectionProtocol, connection)
            supports_roles = self._supports_roles(instance)

            users, has_is_role_column = self._fetch_mysql_user_rows(
                conn,
                where_clause=where_clause,
                params=params,
                supports_roles=supports_roles,
            )
            role_usernames = (
                self._fetch_assigned_role_usernames(connection) if supports_roles and not has_is_role_column else set()
            )

            accounts: list[RawAccount] = []
            for row in users:
                if has_is_role_column:
                    (
                        username,
                        host,
                        is_superuser,
                        is_locked_flag,
                        can_grant_flag,
                        plugin,
                        password_last_changed,
                        is_role,
                    ) = row
                else:
                    username, host, is_superuser, is_locked_flag, can_grant_flag, plugin, password_last_changed = row
                    is_role = None

                unique_username = f"{username}@{host}"
                is_locked_flag_text = "" if is_locked_flag is None else str(is_locked_flag)
                is_locked = is_locked_flag_text.upper() == "Y"
                account_kind = "user"
                is_role_flag = isinstance(is_role, str) and is_role.upper() == "Y"
                if is_role_flag or (supports_roles and unique_username in role_usernames):
                    account_kind = "role"

                accounts.append(
                    {
                        "username": unique_username,
                        "is_superuser": is_superuser == "Y",
                        # 角色本身不可登录,不展示为 "锁定".
                        "is_locked": is_locked if account_kind != "role" else False,
                        "permissions": {
                            "type_specific": {
                                "host": host,
                                "original_username": username,
                                "super_priv": is_superuser == "Y",
                                "account_locked": is_locked,
                                "account_kind": account_kind,
                                "grant_priv": ("" if can_grant_flag is None else str(can_grant_flag)).upper() == "Y",
                                "plugin": plugin,
                                "password_last_changed": (
                                    password_last_changed.isoformat() if password_last_changed else None
                                ),
                            },
                        },
                    },
                )

        except self.MYSQL_ADAPTER_EXCEPTIONS as exc:
            # 采集失败时必须抛异常,避免上游误判为 "远端 0 账号" 从而清空清单。
            self.logger.exception(
                "fetch_mysql_accounts_failed",
                module="mysql_account_adapter",
                instance=instance.name,
                error=str(exc),
            )
            raise

        else:
            self.logger.info(
                "fetch_mysql_accounts_success",
                module="mysql_account_adapter",
                instance=instance.name,
                account_count=len(accounts),
                supports_roles=supports_roles,
            )
            return accounts

    def _supports_roles(self, instance: Instance) -> bool:
        """判断当前 MySQL 实例是否支持内置角色(MySQL 8.0+).

        说明：
        - 版本信息由连接测试/实例同步阶段写入 `instance.main_version` 等字段；
          账号同步阶段只做内部判断，不额外探测系统表/元数据。
        - MySQL 5.7 不支持角色；MySQL 8.0+ 支持角色。
        """
        database_version_value = getattr(instance, "database_version", None)
        if isinstance(database_version_value, str) and database_version_value.strip():
            normalized_database_version = database_version_value.strip().lower()
            # MariaDB 走 MySQL 类型时,系统表结构与 MySQL 8.0 不同,不可直接读取 is_role / role_edges。
            if "mariadb" in normalized_database_version:
                return False

        version_value = getattr(instance, "main_version", None) or getattr(instance, "detailed_version", None)
        if not isinstance(version_value, str) or not version_value.strip():
            self.logger.warning(
                "detect_mysql_roles_support_missing_version",
                module="mysql_account_adapter",
                instance=instance.name,
                fallback=True,
                fallback_reason="instance.main_version/detailed_version missing",
            )
            return False

        normalized = version_value.strip().lower()
        match = re.match(r"(\d+)", normalized)
        if match is None:
            return False

        try:
            major = int(match.group(1))
        except ValueError:
            return False

        return major >= 8

    def _normalize_account(self, instance: Instance, account: RawAccount) -> RemoteAccount:
        """规范化 MySQL 账户信息.

        将原始账户信息转换为统一格式.

        Args:
            instance: 实例对象.
            account: 原始账户信息字典.

        Returns:
            规范化后的账户信息字典,包含:
            - username: 唯一用户名
            - display_name: 显示名称
            - db_type: 数据库类型
            - is_superuser: 是否为超级用户
            - is_locked: 是否被锁定
            - is_active: 是否激活
            - permissions: 权限信息

        """
        _ = instance
        parsed = MySQLRawAccountSchema.model_validate(account)
        username = parsed.username
        permissions = parsed.permissions
        type_specific = permissions.type_specific
        normalized: RemoteAccount = {
            "username": username,
            "display_name": username,
            "db_type": DatabaseType.MYSQL,
            "is_superuser": parsed.is_superuser,
            "is_locked": parsed.is_locked,
            "is_active": True,
            "permissions": cast(
                "PermissionSnapshot",
                {
                    "mysql_global_privileges": permissions.mysql_global_privileges,
                    "mysql_database_privileges": permissions.mysql_database_privileges,
                    "mysql_granted_roles": permissions.mysql_granted_roles,
                    "type_specific": type_specific,
                },
            ),
        }
        return normalized

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------
    def _resolve_account_identity(
        self,
        account: RemoteAccount,
    ) -> tuple[str, str, str, JsonDict] | None:
        """从标准化账号结构中解析用于权限查询的身份信息.

        返回:
        - username: 唯一用户名（可能包含 host）
        - original_username: 用于 SHOW GRANTS 的用户名部分
        - host: 用于 SHOW GRANTS 的 host 部分
        - existing_type_specific: 合并回 permissions.type_specific 的额外字段
        """
        username_value = account.get("username")
        if not isinstance(username_value, str) or not username_value:
            return None

        permissions_value = account.get("permissions")
        if not isinstance(permissions_value, dict):
            return None

        type_specific_value = permissions_value.get("type_specific")
        existing_type_specific = cast("JsonDict", type_specific_value) if isinstance(type_specific_value, dict) else {}

        original_username_val = existing_type_specific.get("original_username")
        original_username = (
            original_username_val.strip()
            if isinstance(original_username_val, str) and original_username_val.strip()
            else None
        )

        host_val = existing_type_specific.get("host")
        host = host_val.strip() if isinstance(host_val, str) and host_val.strip() else None

        if (not original_username or host is None) and "@" in username_value:
            user_part, host_part = username_value.split("@", 1)
            if not original_username:
                original_username = user_part
            if host is None:
                host = host_part

        if not original_username or host is None:
            return None

        return username_value, original_username, host, existing_type_specific

    def _append_permissions_error(self, account: RemoteAccount, message: str) -> None:
        permissions_value = account.get("permissions")
        if not isinstance(permissions_value, dict):
            permissions_value = {}
            account["permissions"] = cast("PermissionSnapshot", permissions_value)
        permissions = cast("PermissionSnapshot", permissions_value)

        errors_list = permissions.get("errors")
        if not isinstance(errors_list, list):
            errors_list = []
            permissions["errors"] = errors_list
        errors_list.append(message)

    def _build_filter_conditions(self) -> tuple[str, list[str]]:
        """构建 MySQL 账户过滤条件.

        根据过滤规则生成 WHERE 子句和参数.

        Returns:
            包含 WHERE 子句和参数列表的元组.

        """
        filter_rules = self.filter_manager.get_filter_rules("mysql")
        builder = SafeQueryBuilder(db_type="mysql")
        builder.add_condition("User != ''")
        exclude_users = cast("list[str]", filter_rules.get("exclude_users", []))
        exclude_patterns = cast("list[str]", filter_rules.get("exclude_patterns", []))
        builder.add_database_specific_condition("User", exclude_users, exclude_patterns)
        where_clause, params = builder.build_where_clause()
        params_str = [str(param) for param in params]
        return where_clause, params_str

    def _prefetch_roles(
        self,
        connection: object,
        *,
        target_usernames: set[str],
    ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """批量拉取 MySQL role 关系.

        说明:
        - 直授角色：mysql.role_edges
        - 默认角色：mysql.default_roles
        - 输出 key 统一为 `user@host`，用于与我们的 username 唯一键对齐。
        """

        def _dedupe(values: list[str]) -> list[str]:
            seen: set[str] = set()
            output: list[str] = []
            for value in values:
                if value in seen:
                    continue
                seen.add(value)
                output.append(value)
            return output

        direct_map: dict[str, list[str]] = {}
        default_map: dict[str, list[str]] = {}

        conn = cast(_MySQLConnectionProtocol, connection)

        direct_sql = (
            "SELECT "
            "  CONCAT(TO_USER, '@', TO_HOST) AS grantee, "
            "  CONCAT(FROM_USER, '@', FROM_HOST) AS role, "
            "  WITH_ADMIN_OPTION AS with_admin_option "
            "FROM mysql.role_edges"
        )
        try:
            rows = conn.execute_query(direct_sql)
        except self.MYSQL_ADAPTER_EXCEPTIONS as exc:
            self.logger.warning(
                "fetch_mysql_role_edges_failed",
                module="mysql_account_adapter",
                error=str(exc),
            )
        else:
            for grantee, role, *_rest in rows:
                if not isinstance(grantee, str) or not isinstance(role, str):
                    continue
                grantee_key = grantee.strip()
                role_value = role.strip()
                if not grantee_key or not role_value:
                    continue
                if target_usernames and grantee_key not in target_usernames:
                    continue
                direct_map.setdefault(grantee_key, []).append(role_value)

        default_sql = (
            "SELECT "
            "  CONCAT(USER, '@', HOST) AS grantee, "
            "  CONCAT(DEFAULT_ROLE_USER, '@', DEFAULT_ROLE_HOST) AS role "
            "FROM mysql.default_roles"
        )
        try:
            rows = conn.execute_query(default_sql)
        except self.MYSQL_ADAPTER_EXCEPTIONS as exc:
            self.logger.warning(
                "fetch_mysql_default_roles_failed",
                module="mysql_account_adapter",
                error=str(exc),
            )
        else:
            for grantee, role, *_rest in rows:
                if not isinstance(grantee, str) or not isinstance(role, str):
                    continue
                grantee_key = grantee.strip()
                role_value = role.strip()
                if not grantee_key or not role_value:
                    continue
                if target_usernames and grantee_key not in target_usernames:
                    continue
                default_map.setdefault(grantee_key, []).append(role_value)

        return (
            {key: _dedupe(values) for key, values in direct_map.items()},
            {key: _dedupe(values) for key, values in default_map.items()},
        )

    def _prepare_roles_enrichment(
        self,
        instance: Instance,
        connection: object,
        accounts: list[RemoteAccount],
    ) -> tuple[
        bool,
        dict[str, list[str]],
        dict[str, list[str]],
        dict[str, list[str]],
        dict[str, list[str]],
    ]:
        """为 MySQL enrich_permissions 预取角色相关映射。

        返回:
        - supports_roles: 是否支持角色（8.0+）
        - direct_roles_map: grantee -> [role]
        - default_roles_map: grantee -> [role]
        - role_members_direct_map: role -> [user]
        - role_members_default_map: role -> [user]
        """

        supports_roles = self._supports_roles(instance)
        if not supports_roles:
            return False, {}, {}, {}, {}

        # role_edges/default_roles 的过滤条件与 membership 维度不同（grantee vs role），
        # 这里统一全量拉取后在内存中做映射，保证角色详情可展示“包含用户”。
        direct_roles_map, default_roles_map = self._prefetch_roles(connection, target_usernames=set())

        known_usernames, role_usernames = self._collect_mysql_usernames_by_kind(accounts)
        role_members_direct_map = self._invert_grantee_roles_map(
            direct_roles_map,
            known_usernames=known_usernames,
            role_usernames=role_usernames,
        )
        role_members_default_map = self._invert_grantee_roles_map(
            default_roles_map,
            known_usernames=known_usernames,
            role_usernames=role_usernames,
        )

        return (
            True,
            direct_roles_map,
            default_roles_map,
            role_members_direct_map,
            role_members_default_map,
        )

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            output.append(value)
        return output

    @staticmethod
    def _collect_mysql_usernames_by_kind(accounts: list[RemoteAccount]) -> tuple[set[str], set[str]]:
        known_usernames: set[str] = set()
        role_usernames: set[str] = set()
        for account in accounts:
            username_value = account.get("username")
            if not isinstance(username_value, str) or not username_value:
                continue
            known_usernames.add(username_value)
            permissions_value = account.get("permissions")
            if not isinstance(permissions_value, dict):
                continue
            type_specific_value = permissions_value.get("type_specific")
            if not isinstance(type_specific_value, dict):
                continue
            account_kind_value = type_specific_value.get("account_kind")
            if isinstance(account_kind_value, str) and account_kind_value.lower() == "role":
                role_usernames.add(username_value)
        return known_usernames, role_usernames

    def _invert_grantee_roles_map(
        self,
        grantee_roles_map: dict[str, list[str]],
        *,
        known_usernames: set[str],
        role_usernames: set[str],
    ) -> dict[str, list[str]]:
        role_members_map: dict[str, list[str]] = {}
        restrict_to_known = bool(known_usernames)
        for grantee, roles in grantee_roles_map.items():
            if restrict_to_known and grantee not in known_usernames:
                continue
            if grantee in role_usernames:
                continue
            for role in roles:
                role_members_map.setdefault(role, []).append(grantee)
        return {key: self._dedupe_strings(values) for key, values in role_members_map.items()}

    def _get_user_permissions(self, connection: object, username: str, host: str) -> PermissionSnapshot:
        """获取 MySQL 用户权限详情.

        通过 SHOW GRANTS 语句查询用户的全局权限和数据库级权限.

        Args:
            connection: MySQL 数据库连接对象.
            username: 用户名.
            host: 主机名.

        Returns:
            权限信息字典,包含:
            - mysql_global_privileges: 全局权限列表
            - mysql_database_privileges: 数据库级权限字典
            - type_specific: 数据库特定信息

        Example:
            >>> perms = adapter._get_user_permissions(connection, 'root', 'localhost')
            >>> print(perms['mysql_global_privileges'])
            ['SELECT', 'INSERT', 'UPDATE', ...]

        """
        try:
            conn = cast(_MySQLConnectionProtocol, connection)
            grants = conn.execute_query("SHOW GRANTS FOR %s@%s", (username, host))
            grant_statements = [row[0] for row in grants]

            global_privileges: list[str] = []
            database_privileges: dict[str, list[str]] = {}

            for statement in grant_statements:
                self._parse_grant_statement(statement, global_privileges, database_privileges)
            user_attrs_sql = """
                SELECT
                    Super_priv as super_priv,
                    Grant_priv as grant_priv,
                    account_locked as account_locked,
                    plugin as plugin,
                    password_last_changed as password_last_changed
                FROM mysql.user
                WHERE User = %s AND Host = %s
            """
            attrs = conn.execute_query(user_attrs_sql, (username, host))
            type_specific: JsonDict = {}
            if attrs:
                super_priv, grant_priv, account_locked, plugin, password_last_changed = attrs[0]
                type_specific.update(
                    {
                        "super_priv": super_priv == "Y",
                        "grant_priv": grant_priv == "Y",
                        "account_locked": account_locked == "Y",
                        "plugin": plugin,
                        "password_last_changed": password_last_changed.isoformat() if password_last_changed else None,
                    },
                )
            permissions_snapshot: PermissionSnapshot = {
                "mysql_global_privileges": global_privileges,
                "mysql_database_privileges": database_privileges,
                "type_specific": type_specific,
            }
        except self.MYSQL_ADAPTER_EXCEPTIONS as exc:
            self.logger.exception(
                "fetch_mysql_permissions_failed",
                module="mysql_account_adapter",
                username=username,
                host=host,
                error=str(exc),
            )
            return {
                "mysql_global_privileges": [],
                "mysql_database_privileges": {},
                "type_specific": {},
            }
        else:
            return permissions_snapshot

    def enrich_permissions(
        self,
        instance: Instance,
        connection: object,
        accounts: list[RemoteAccount],
        *,
        usernames: Sequence[str] | None = None,
    ) -> list[RemoteAccount]:
        """丰富 MySQL 账户的权限信息.

        为指定账户查询详细的权限信息,包括全局权限和数据库级权限.

        Args:
            instance: 实例对象.
            connection: MySQL 数据库连接对象.
            accounts: 账户信息列表.
            usernames: 可选的目标用户名列表.如果为 None,处理所有账户.

        Returns:
            丰富后的账户信息列表,每个账户的 permissions 字段包含详细权限.

        Example:
            >>> enriched = adapter.enrich_permissions(instance, connection, accounts)
            >>> print(enriched[0]['permissions']['mysql_global_privileges'])
            ['SELECT', 'INSERT', 'UPDATE', ...]

        """
        if usernames is None:
            target_usernames = {
                cast(str, username)
                for account in accounts
                for username in [account.get("username")]
                if isinstance(username, str) and username
            }
        else:
            target_usernames = set(usernames)
        if not target_usernames:
            return accounts

        (
            supports_roles,
            direct_roles_map,
            default_roles_map,
            role_members_direct_map,
            role_members_default_map,
        ) = self._prepare_roles_enrichment(instance, connection, accounts)

        processed = 0
        for account in accounts:
            resolved = self._resolve_account_identity(account)
            if resolved is None:
                continue
            username, original_username, host, existing_type_specific = resolved
            if username not in target_usernames:
                continue

            processed += 1
            try:
                permissions = self._get_user_permissions(connection, original_username, host)
                permissions_type_specific = permissions.get("type_specific")
                type_specific = (
                    cast("JsonDict", permissions_type_specific) if isinstance(permissions_type_specific, dict) else {}
                )
                permissions["type_specific"] = type_specific
                for key, value in existing_type_specific.items():
                    if value is not None:
                        type_specific[key] = value

                permissions["mysql_granted_roles"] = {
                    "direct": direct_roles_map.get(username, []),
                    "default": default_roles_map.get(username, []),
                }
                account_kind_value = existing_type_specific.get("account_kind")
                if supports_roles and isinstance(account_kind_value, str) and account_kind_value.lower() == "role":
                    permissions["mysql_role_members"] = {
                        "direct": role_members_direct_map.get(username, []),
                        "default": role_members_default_map.get(username, []),
                    }
                account["permissions"] = permissions
            except self.MYSQL_ADAPTER_EXCEPTIONS as exc:
                self.logger.exception(
                    "fetch_mysql_permissions_failed",
                    module="mysql_account_adapter",
                    instance=instance.name,
                    username=original_username,
                    host=host,
                    error=str(exc),
                )
                self._append_permissions_error(account, str(exc))

        self.logger.info(
            "fetch_mysql_permissions_completed",
            module="mysql_account_adapter",
            instance=instance.name,
            processed_accounts=processed,
        )
        return accounts

    def _parse_grant_statement(
        self,
        grant_statement: str,
        global_privileges: list[str],
        database_privileges: dict[str, list[str]],
    ) -> None:
        """解析 MySQL GRANT 语句.

        从 GRANT 语句中提取权限信息,并分类为全局权限或数据库级权限.

        Args:
            grant_statement: GRANT 语句字符串.
            global_privileges: 全局权限列表(会被修改).
            database_privileges: 数据库级权限字典(会被修改).

        Returns:
            None: 权限信息会写入传入的列表/字典.

        Example:
            >>> global_privs = []
            >>> db_privs = {}
            >>> adapter._parse_grant_statement(
            ...     'GRANT SELECT ON `mydb`.* TO `user`@`host`',
            ...     global_privs,
            ...     db_privs
            ... )
            >>> print(db_privs)
            {'mydb': ['SELECT']}

        """
        try:
            has_grant_option = "WITH GRANT OPTION" in grant_statement.upper()
            simple_grant = grant_statement.upper().replace("GRANT ", "").replace(" WITH GRANT OPTION", "")

            global_match = re.match(r"(.+?) ON \*\.\*", simple_grant)
            if global_match:
                privs = self._extract_privileges(global_match.group(1), is_global=True)
                global_privileges.extend(privs)
                if has_grant_option and "GRANT OPTION" not in global_privileges:
                    global_privileges.append("GRANT OPTION")
                return

            db_match = re.match(r"(.+?) ON `(.+?)`\.\*", simple_grant)
            if db_match:
                privs = self._extract_privileges(db_match.group(1), is_global=False)
                db_name = db_match.group(2).replace("``", "`")
                existing = database_privileges.setdefault(db_name, [])
                for priv in privs:
                    if priv not in existing:
                        existing.append(priv)
                if has_grant_option and "GRANT OPTION" not in existing:
                    existing.append("GRANT OPTION")
                return
        except self.MYSQL_ADAPTER_EXCEPTIONS as exc:
            self.logger.warning(
                "mysql_parse_grant_failed",
                module="mysql_account_adapter",
                statement=grant_statement,
                error=str(exc),
            )

    def _extract_privileges(self, privilege_str: str, *, is_global: bool) -> list[str]:
        """从权限字符串中提取权限列表.

        Args:
            privilege_str: 权限字符串.
            is_global: 是否为全局权限.

        Returns:
            权限名称列表.

        """
        privileges_part = privilege_str.split(" ON ")[0].strip()
        if "ALL PRIVILEGES" in privileges_part.upper():
            return self._expand_all_privileges(is_global=is_global)
        return [priv.strip().upper() for priv in privileges_part.split(",") if priv.strip()]

    def _expand_all_privileges(self, *, is_global: bool) -> list[str]:
        """返回 ALL PRIVILEGES 展开的权限列表.

        Args:
            is_global: True 表示全局权限,False 表示数据库级权限.

        Returns:
            list[str]: 权限名称列表.

        """
        if is_global:
            return [
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "CREATE",
                "DROP",
                "RELOAD",
                "SHUTDOWN",
                "PROCESS",
                "FILE",
                "REFERENCES",
                "INDEX",
                "ALTER",
                "SHOW DATABASES",
                "SUPER",
                "CREATE TEMPORARY TABLES",
                "LOCK TABLES",
                "EXECUTE",
                "REPLICATION SLAVE",
                "REPLICATION CLIENT",
                "CREATE VIEW",
                "SHOW VIEW",
                "CREATE ROUTINE",
                "ALTER ROUTINE",
                "CREATE USER",
                "EVENT",
                "TRIGGER",
                "CREATE TABLESPACE",
                "USAGE",
            ]
        return [
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "CREATE",
            "DROP",
            "REFERENCES",
            "INDEX",
            "ALTER",
            "CREATE TEMPORARY TABLES",
            "LOCK TABLES",
            "EXECUTE",
            "CREATE VIEW",
            "SHOW VIEW",
            "CREATE ROUTINE",
            "ALTER ROUTINE",
            "EVENT",
            "TRIGGER",
            "USAGE",
        ]
