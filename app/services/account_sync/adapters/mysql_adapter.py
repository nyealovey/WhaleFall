"""
MySQL账户同步适配器（两阶段版）
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.constants import DatabaseType
from app.models.instance import Instance
from app.services.account_sync.adapters.base_adapter import BaseAccountAdapter
from app.services.account_sync.account_sync_filters import DatabaseFilterManager
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.structlog_config import get_sync_logger


class MySQLAccountAdapter(BaseAccountAdapter):
    """负责拉取 MySQL 账户信息与权限快照。"""

    def __init__(self) -> None:
        self.logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()

    # ------------------------------------------------------------------
    # BaseAccountAdapter 实现
    # ------------------------------------------------------------------
    def _fetch_raw_accounts(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:  # noqa: ANN401
        try:
            where_clause, params = self._build_filter_conditions()
            user_sql = (
                "SELECT "
                "    User as username, "
                "    Host as host, "
                "    Super_priv as is_superuser "
                "FROM mysql.user "
                f"WHERE User != '' AND {where_clause} "
                "ORDER BY User, Host"
            )
            users = connection.execute_query(user_sql, params)

            accounts: List[Dict[str, Any]] = []
            for username, host, is_superuser in users:
                unique_username = f"{username}@{host}"
                permissions = self._get_user_permissions(connection, username, host)

                # 获取锁定状态
                is_locked_sql = "SELECT account_locked FROM mysql.user WHERE User = %s AND Host = %s"
                is_locked_result = connection.execute_query(is_locked_sql, (username, host))
                is_locked = is_locked_result[0][0] == "Y" if is_locked_result else False

                permissions.setdefault("type_specific", {})["host"] = host
                permissions["type_specific"]["original_username"] = username
                permissions["type_specific"]["is_locked"] = is_locked

                accounts.append(
                    {
                        "username": unique_username,
                        "original_username": username,
                        "host": host,
                        "is_superuser": is_superuser == "Y",
                        "is_locked": is_locked,
                        "permissions": permissions,
                    }
                )

            self.logger.info(
                "fetch_mysql_accounts_success",
                module="mysql_account_adapter",
                instance=instance.name,
                account_count=len(accounts),
            )
            return accounts
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "fetch_mysql_accounts_failed",
                module="mysql_account_adapter",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            return []

    def _normalize_account(self, instance: Instance, account: Dict[str, Any]) -> Dict[str, Any]:
        permissions = account.get("permissions", {})
        type_specific = permissions.get("type_specific", {})
        attributes = {
            "host": account.get("host"),
            "original_username": account.get("original_username"),
            "is_locked": account.get("is_locked", False),
            "grant_statements": type_specific.get("grant_statements"),
            "plugin": type_specific.get("plugin"),
            "password_last_changed": type_specific.get("password_last_changed"),
        }
        return {
            "username": account["username"],
            "display_name": account["username"],
            "db_type": DatabaseType.MYSQL,
            "is_superuser": account.get("is_superuser", False),
            "is_active": not account.get("is_locked", False),
            "attributes": attributes,
            "permissions": {
                "global_privileges": permissions.get("global_privileges", []),
                "database_privileges": permissions.get("database_privileges", {}),
                "type_specific": type_specific,
            },
        }

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------
    def _build_filter_conditions(self) -> tuple[str, List[Any]]:  # noqa: ANN401
        filter_rules = self.filter_manager.get_filter_rules("mysql")
        builder = SafeQueryBuilder(db_type="mysql")
        builder.add_database_specific_condition("User", filter_rules.get("exclude_users", []), filter_rules.get("exclude_patterns", []))
        return builder.build_where_clause()

    def _get_user_permissions(self, connection: Any, username: str, host: str) -> Dict[str, Any]:  # noqa: ANN401
        try:
            grants = connection.execute_query("SHOW GRANTS FOR %s@%s", (username, host))
            grant_statements = [row[0] for row in grants]

            global_privileges: List[str] = []
            database_privileges: Dict[str, List[str]] = {}

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
            type_specific = {
                "grant_statements": grant_statements,
            }
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
        except Exception as exc:  # noqa: BLE001
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
                "type_specific": {"grant_statements": [], "can_grant": False, "is_locked": False},
            }

    def _parse_grant_statement(
        self,
        grant_statement: str,
        global_privileges: List[str],
        database_privileges: Dict[str, List[str]],
    ) -> None:
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
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "mysql_parse_grant_failed",
                module="mysql_account_adapter",
                statement=grant_statement,
                error=str(exc),
                exc_info=True,
            )

    def _extract_privileges(self, privilege_str: str, *, is_global: bool) -> List[str]:
        privileges_part = privilege_str.split(" ON ")[0].strip()
        if "ALL PRIVILEGES" in privileges_part.upper():
            return self._expand_all_privileges(is_global)
        return [priv.strip().upper() for priv in privileges_part.split(",") if priv.strip()]

    def _expand_all_privileges(self, is_global: bool) -> List[str]:
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
