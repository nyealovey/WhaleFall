"""
MySQL账户同步适配器（两阶段版）
"""

from __future__ import annotations

import re
from typing import Any
from collections.abc import Sequence

from app.constants import DatabaseType
from app.models.instance import Instance
from app.services.accounts_sync.adapters.base_adapter import BaseAccountAdapter
from app.services.accounts_sync.accounts_sync_filters import DatabaseFilterManager
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.structlog_config import get_sync_logger


class MySQLAccountAdapter(BaseAccountAdapter):
    """负责拉取 MySQL 账户信息与权限快照。

    实现 MySQL 数据库的账户查询和权限采集功能。
    通过 mysql.user 表和 SHOW GRANTS 语句采集账户信息和权限。

    Attributes:
        logger: 同步日志记录器。
        filter_manager: 数据库过滤管理器。

    Example:
        >>> adapter = MySQLAccountAdapter()
        >>> accounts = adapter.fetch_accounts(instance, connection)
        >>> enriched = adapter.enrich_permissions(instance, connection, accounts)

    """

    def __init__(self) -> None:
        self.logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()

    # ------------------------------------------------------------------
    # BaseAccountAdapter 实现
    # ------------------------------------------------------------------
    def _fetch_raw_accounts(self, instance: Instance, connection: Any) -> list[dict[str, Any]]:
        """拉取 MySQL 原始账户信息。

        从 mysql.user 表中查询账户基本信息，包括用户名、主机、超级用户标志等。

        Args:
            instance: 实例对象。
            connection: MySQL 数据库连接对象。

        Returns:
            原始账户信息列表，每个元素包含：
            - username: 唯一用户名（格式：user@host）
            - original_username: 原始用户名
            - host: 主机名
            - is_superuser: 是否为超级用户
            - is_locked: 是否被锁定
            - permissions: 权限信息字典

        Example:
            >>> accounts = adapter._fetch_raw_accounts(instance, connection)
            >>> print(accounts[0])
            {
                'username': 'root@localhost',
                'original_username': 'root',
                'host': 'localhost',
                'is_superuser': True,
                'is_locked': False,
                'permissions': {...}
            }

        """
        try:
            where_clause, params = self._build_filter_conditions()
            user_sql = (
                "SELECT "
                "    User as username, "
                "    Host as host, "
                "    Super_priv as is_superuser, "
                "    account_locked as is_locked, "
                "    Grant_priv as can_grant, "
                "    plugin as plugin, "
                "    password_last_changed as password_last_changed "
                "FROM mysql.user "
                f"WHERE User != '' AND {where_clause} "
                "ORDER BY User, Host"
            )
            users = connection.execute_query(user_sql, params)

            accounts: list[dict[str, Any]] = []
            for username, host, is_superuser, is_locked_flag, can_grant_flag, plugin, password_last_changed in users:
                unique_username = f"{username}@{host}"
                is_locked = (is_locked_flag or "").upper() == "Y"
                accounts.append(
                    {
                        "username": unique_username,
                        "original_username": username,
                        "host": host,
                        "is_superuser": is_superuser == "Y",
                        "is_locked": is_locked,
                        "permissions": {
                            "type_specific": {
                                "host": host,
                                "original_username": username,
                                "is_locked": is_locked,
                                "plugin": plugin,
                                "password_last_changed": password_last_changed.isoformat()
                                if password_last_changed
                                else None,
                                "can_grant": (can_grant_flag or "").upper() == "Y",
                            }
                        },
                    }
                )

            self.logger.info(
                "fetch_mysql_accounts_success",
                module="mysql_account_adapter",
                instance=instance.name,
                account_count=len(accounts),
            )
            return accounts
        except Exception as exc:
            self.logger.error(
                "fetch_mysql_accounts_failed",
                module="mysql_account_adapter",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            return []

    def _normalize_account(self, instance: Instance, account: dict[str, Any]) -> dict[str, Any]:
        """规范化 MySQL 账户信息。

        将原始账户信息转换为统一格式。

        Args:
            instance: 实例对象。
            account: 原始账户信息字典。

        Returns:
            规范化后的账户信息字典，包含：
            - username: 唯一用户名
            - display_name: 显示名称
            - db_type: 数据库类型
            - is_superuser: 是否为超级用户
            - is_locked: 是否被锁定
            - is_active: 是否激活
            - permissions: 权限信息

        """
        permissions = account.get("permissions", {})
        type_specific = permissions.setdefault("type_specific", {})
        type_specific.setdefault("host", account.get("host"))
        type_specific.setdefault("original_username", account.get("original_username"))
        type_specific.setdefault("is_locked", account.get("is_locked", False))
        is_locked = bool(type_specific.get("is_locked", account.get("is_locked", False)))
        return {
            "username": account["username"],
            "display_name": account["username"],
            "db_type": DatabaseType.MYSQL,
            "is_superuser": account.get("is_superuser", False),
            "is_locked": is_locked,
            "is_active": True,
            "permissions": {
                "global_privileges": permissions.get("global_privileges", []),
                "database_privileges": permissions.get("database_privileges", {}),
                "type_specific": type_specific,
            },
        }

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------
    def _build_filter_conditions(self) -> tuple[str, list[Any]]:
        """构建 MySQL 账户过滤条件。

        根据过滤规则生成 WHERE 子句和参数。

        Returns:
            包含 WHERE 子句和参数列表的元组。

        """
        filter_rules = self.filter_manager.get_filter_rules("mysql")
        builder = SafeQueryBuilder(db_type="mysql")
        builder.add_database_specific_condition("User", filter_rules.get("exclude_users", []), filter_rules.get("exclude_patterns", []))
        return builder.build_where_clause()

    def _get_user_permissions(self, connection: Any, username: str, host: str) -> dict[str, Any]:
        """获取 MySQL 用户权限详情。

        通过 SHOW GRANTS 语句查询用户的全局权限和数据库级权限。

        Args:
            connection: MySQL 数据库连接对象。
            username: 用户名。
            host: 主机名。

        Returns:
            权限信息字典，包含：
            - global_privileges: 全局权限列表
            - database_privileges: 数据库级权限字典
            - type_specific: 数据库特定信息

        Example:
            >>> perms = adapter._get_user_permissions(connection, 'root', 'localhost')
            >>> print(perms['global_privileges'])
            ['SELECT', 'INSERT', 'UPDATE', ...]

        """
        try:
            grants = connection.execute_query("SHOW GRANTS FOR %s@%s", (username, host))
            grant_statements = [row[0] for row in grants]

            global_privileges: list[str] = []
            database_privileges: dict[str, list[str]] = {}

            for statement in grant_statements:
                self._parse_grant_statement(statement, global_privileges, database_privileges)
            user_attrs_sql = """
                SELECT
                    Grant_priv as can_grant,
                    account_locked as is_locked,
                    plugin as plugin,
                    password_last_changed as password_last_changed
                FROM mysql.user
                WHERE User = %s AND Host = %s
            """
            attrs = connection.execute_query(user_attrs_sql, (username, host))
            type_specific: dict[str, Any] = {}
            if attrs:
                can_grant, is_locked, plugin, password_last_changed = attrs[0]
                type_specific.update(
                    {
                        "can_grant": can_grant == "Y",
                        "is_locked": is_locked == "Y",
                        "plugin": plugin,
                        "password_last_changed": password_last_changed.isoformat() if password_last_changed else None,
                    }
                )
            return {
                "global_privileges": global_privileges,
                "database_privileges": database_privileges,
                "type_specific": type_specific,
            }
        except Exception as exc:
            self.logger.error(
                "fetch_mysql_permissions_failed",
                module="mysql_account_adapter",
                username=username,
                host=host,
                error=str(exc),
                exc_info=True,
            )
            return {
                "global_privileges": [],
                "database_privileges": {},
                "type_specific": {"can_grant": False, "is_locked": False},
            }

    def enrich_permissions(
        self,
        instance: Instance,
        connection: Any,
        accounts: list[dict[str, Any]],
        *,
        usernames: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """丰富 MySQL 账户的权限信息。

        为指定账户查询详细的权限信息，包括全局权限和数据库级权限。

        Args:
            instance: 实例对象。
            connection: MySQL 数据库连接对象。
            accounts: 账户信息列表。
            usernames: 可选的目标用户名列表。如果为 None，处理所有账户。

        Returns:
            丰富后的账户信息列表，每个账户的 permissions 字段包含详细权限。

        Example:
            >>> enriched = adapter.enrich_permissions(instance, connection, accounts)
            >>> print(enriched[0]['permissions']['global_privileges'])
            ['SELECT', 'INSERT', 'UPDATE', ...]

        """
        target_usernames = {account["username"] for account in accounts} if usernames is None else set(usernames)
        if not target_usernames:
            return accounts

        processed = 0
        for account in accounts:
            username = account.get("username")
            if not username or username not in target_usernames:
                continue
            permissions_container = account.get("permissions") or {}
            existing_type_specific = permissions_container.get("type_specific") or {}
            original_username = existing_type_specific.get("original_username") or account.get("original_username")
            host = existing_type_specific.get("host") if "host" in existing_type_specific else account.get("host")
            if (not original_username or host is None) and "@" in username:
                user_part, host_part = username.split("@", 1)
                original_username = original_username or user_part
                host = host if host is not None else host_part
            if not original_username or host is None:
                continue

            processed += 1
            try:
                permissions = self._get_user_permissions(connection, original_username, host)
                type_specific = permissions.setdefault("type_specific", {})
                for key, value in existing_type_specific.items():
                    if value is not None:
                        type_specific.setdefault(key, value)
                account["permissions"] = permissions
                account["is_locked"] = bool(
                    type_specific.get("is_locked", account.get("is_locked", False))
                )
            except Exception as exc:
                self.logger.error(
                    "fetch_mysql_permissions_failed",
                    module="mysql_account_adapter",
                    instance=instance.name,
                    username=original_username,
                    host=host,
                    error=str(exc),
                    exc_info=True,
                )
                account.setdefault("permissions", {}).setdefault("errors", []).append(str(exc))

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
        """解析 MySQL GRANT 语句。

        从 GRANT 语句中提取权限信息，并分类为全局权限或数据库级权限。

        Args:
            grant_statement: GRANT 语句字符串。
            global_privileges: 全局权限列表（会被修改）。
            database_privileges: 数据库级权限字典（会被修改）。

        Returns:
            None: 权限信息会写入传入的列表/字典。

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
        except Exception as exc:
            self.logger.warning(
                "mysql_parse_grant_failed",
                module="mysql_account_adapter",
                statement=grant_statement,
                error=str(exc),
                exc_info=True,
            )

    def _extract_privileges(self, privilege_str: str, *, is_global: bool) -> list[str]:
        """从权限字符串中提取权限列表。

        Args:
            privilege_str: 权限字符串。
            is_global: 是否为全局权限。

        Returns:
            权限名称列表。

        """
        privileges_part = privilege_str.split(" ON ")[0].strip()
        if "ALL PRIVILEGES" in privileges_part.upper():
            return self._expand_all_privileges(is_global)
        return [priv.strip().upper() for priv in privileges_part.split(",") if priv.strip()]

    def _expand_all_privileges(self, is_global: bool) -> list[str]:
        """返回 ALL PRIVILEGES 展开的权限列表。

        Args:
            is_global: True 表示全局权限，False 表示数据库级权限。

        Returns:
            list[str]: 权限名称列表。

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
