"""PostgreSQL 账户同步适配器（两阶段版）。"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from app.constants import DatabaseType
from app.models.instance import Instance
from app.services.account_sync.adapters.base_adapter import BaseAccountAdapter
from app.services.account_sync.account_sync_filters import DatabaseFilterManager
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.structlog_config import get_sync_logger


class PostgreSQLAccountAdapter(BaseAccountAdapter):
    def __init__(self) -> None:
        self.logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()

    def _fetch_raw_accounts(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:  # noqa: ANN401
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
                "FROM pg_roles "
                f"WHERE {where_clause} "
                "ORDER BY rolname"
            )
            rows = connection.execute_query(roles_sql, params)
            accounts: List[Dict[str, Any]] = []
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
                accounts.append(
                    {
                        "username": username,
                        "is_superuser": is_superuser,
                        "can_login": bool(can_login),
                        # 权限在 collection 阶段按需加载
                        "permissions": {
                            "type_specific": type_specific,
                            "role_attributes": role_attributes,
                        },
                    }
                )
            self.logger.info(
                "fetch_postgresql_accounts_success",
                module="postgresql_account_adapter",
                instance=instance.name,
                account_count=len(accounts),
            )
            return accounts
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "fetch_postgresql_accounts_failed",
                module="postgresql_account_adapter",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            return []

    def _normalize_account(self, instance: Instance, account: Dict[str, Any]) -> Dict[str, Any]:
        permissions = account.get("permissions") or {}
        type_specific = permissions.setdefault("type_specific", {})
        permissions.setdefault("role_attributes", {})
        if "can_login" not in type_specific and account.get("can_login") is not None:
            type_specific["can_login"] = bool(account.get("can_login"))
        return {
            "username": account["username"],
            "display_name": account["username"],
            "db_type": DatabaseType.POSTGRESQL,
            "is_superuser": account.get("is_superuser", False),
            "is_active": bool(type_specific.get("can_login", True)),
            "permissions": {
                "predefined_roles": permissions.get("predefined_roles", []),
                "role_attributes": permissions.get("role_attributes", {}),
                "database_privileges_pg": permissions.get("database_privileges_pg", {}),
                "tablespace_privileges": permissions.get("tablespace_privileges", {}),
                "system_privileges": permissions.get("system_privileges", []),
                "type_specific": type_specific,
            },
        }

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _build_filter_conditions(self) -> tuple[str, List[Any]]:  # noqa: ANN401
        rules = self.filter_manager.get_filter_rules("postgresql")
        builder = SafeQueryBuilder(db_type="postgresql")
        builder.add_database_specific_condition(
            "rolname",
            rules.get("exclude_users", []),
            rules.get("exclude_patterns", []),
        )
        return builder.build_where_clause()

    def _get_role_permissions(
        self,
        connection: Any,
        username: str,
        *,
        is_superuser: bool,
    ) -> Dict[str, Any]:
        permissions: Dict[str, Any] = {
            "predefined_roles": [],
            "role_attributes": {},
            "database_privileges_pg": {},
            "tablespace_privileges": {},
            "system_privileges": [],
            "type_specific": {},
        }
        try:
            permissions["role_attributes"] = self._get_role_attributes(connection, username)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "fetch_pg_role_attributes_failed",
                role=username,
                error=str(exc),
                exc_info=True,
            )
        try:
            permissions["predefined_roles"] = self._get_predefined_roles(connection, username)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "fetch_pg_predefined_roles_failed",
                role=username,
                error=str(exc),
                exc_info=True,
            )
        try:
            permissions["database_privileges_pg"] = self._get_database_privileges(connection, username)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "fetch_pg_database_privileges_failed",
                role=username,
                error=str(exc),
                exc_info=True,
            )
        try:
            permissions["tablespace_privileges"] = self._get_tablespace_privileges(connection, username)
        except Exception as exc:  # noqa: BLE001
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
        connection: Any,
        accounts: List[Dict[str, Any]],
        *,
        usernames: Sequence[str] | None = None,
    ) -> List[Dict[str, Any]]:
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
                existing_permissions = account.get("permissions") or {}
                seed_type_specific = existing_permissions.get("type_specific") or {}
                seed_role_attributes = existing_permissions.get("role_attributes") or {}

                permissions = self._get_role_permissions(
                    connection,
                    username,
                    is_superuser=bool(account.get("is_superuser")),
                )
                type_specific = permissions.setdefault("type_specific", {})
                for key, value in seed_type_specific.items():
                    if value is not None:
                        type_specific.setdefault(key, value)
                role_attributes = permissions.setdefault("role_attributes", {})
                for key, value in seed_role_attributes.items():
                    if value is not None:
                        role_attributes.setdefault(key, value)
                if "can_login" not in type_specific and role_attributes.get("can_login") is not None:
                    type_specific["can_login"] = bool(role_attributes["can_login"])
                if seed_type_specific.get("valid_until") is not None and "valid_until" not in type_specific:
                    type_specific["valid_until"] = seed_type_specific["valid_until"]
                for propagated_key in (
                    "can_create_role",
                    "can_create_db",
                    "can_replicate",
                    "can_bypass_rls",
                    "can_inherit",
                    "can_login",
                ):
                    value = role_attributes.get(propagated_key)
                    if value is not None:
                        type_specific.setdefault(propagated_key, value)
                account["permissions"] = permissions
            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    "fetch_pg_permissions_failed",
                    module="postgresql_account_adapter",
                    instance=instance.name,
                    username=username,
                    error=str(exc),
                    exc_info=True,
                )
                account.setdefault("permissions", {}).setdefault("errors", []).append(str(exc))

        self.logger.info(
            "fetch_postgresql_permissions_completed",
            module="postgresql_account_adapter",
            instance=instance.name,
            processed_accounts=processed,
        )
        return accounts

    # 以下辅助查询函数沿用旧实现
    def _get_role_attributes(self, connection: Any, username: str) -> Dict[str, Any]:
        sql = """
            SELECT rolcreaterole, rolcreatedb, rolreplication, rolbypassrls, rolcanlogin, rolinherit
            FROM pg_roles
            WHERE rolname = %s
        """
        result = connection.execute_query(sql, (username,))
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

    def _get_predefined_roles(self, connection: Any, username: str) -> List[str]:
        sql = """
            SELECT
                pg_get_userbyid(roleid) as role_name
            FROM pg_auth_members
            WHERE member = (SELECT oid FROM pg_roles WHERE rolname = %s)
        """
        rows = connection.execute_query(sql, (username,))
        return [row[0] for row in rows if row and row[0]]

    def _get_database_privileges(self, connection: Any, username: str) -> Dict[str, List[str]]:
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
        rows = connection.execute_query(sql, (username,) * 6)
        privileges: Dict[str, List[str]] = {}
        for row in rows:
            if not row or not row[0]:
                continue
            datname, priv_list = row
            filtered = [priv for priv in (priv_list or []) if priv]
            if filtered:
                privileges[datname] = filtered
        return privileges

    def _get_tablespace_privileges(self, connection: Any, username: str) -> Dict[str, List[str]]:
        sql = """
            SELECT
                spcname,
                ARRAY[
                    CASE WHEN has_tablespace_privilege(%s, spcname, 'CREATE') THEN 'CREATE' END
                ]::text[] AS privileges
            FROM pg_tablespace
            WHERE has_tablespace_privilege(%s, spcname, 'CREATE')
        """
        rows = connection.execute_query(sql, (username, username))
        privileges: Dict[str, List[str]] = {}
        for row in rows:
            if not row or not row[0]:
                continue
            spcname, priv_list = row
            filtered = [priv for priv in (priv_list or []) if priv]
            if filtered:
                privileges[spcname] = filtered
        return privileges
