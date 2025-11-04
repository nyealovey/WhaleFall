"""SQL Server 账户同步适配器（两阶段版）。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.constants import DatabaseType
from app.models.instance import Instance
from app.services.account_sync.adapters.base_adapter import BaseAccountAdapter
from app.services.account_sync.account_sync_filters import DatabaseFilterManager
from app.utils.structlog_config import get_sync_logger
from app.services.cache_service import cache_manager


class SQLServerAccountAdapter(BaseAccountAdapter):
    def __init__(self) -> None:
        self.logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()

    def _fetch_raw_accounts(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:  # noqa: ANN401
        try:
            users = self._fetch_logins(connection)
            accounts: List[Dict[str, Any]] = []
            for user in users:
                login_name = user["name"]
                is_disabled = user.get("is_disabled", False)
                is_superuser = user.get("is_sysadmin", False)
                permissions = self._get_login_permissions(connection, login_name)
                permissions.setdefault("type_specific", {})["is_disabled"] = is_disabled
                accounts.append(
                    {
                        "username": login_name,
                        "is_superuser": is_superuser,
                        "is_disabled": is_disabled,
                        "permissions": permissions,
                    }
                )
            return accounts
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "fetch_sqlserver_accounts_failed",
                module="sqlserver_account_adapter",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            return []

    def _normalize_account(self, instance: Instance, account: Dict[str, Any]) -> Dict[str, Any]:
        permissions = account.get("permissions", {})
        attributes = {
            "is_disabled": account.get("is_disabled", False),
        }
        return {
            "username": account["username"],
            "display_name": account["username"],
            "db_type": DatabaseType.SQLSERVER,
            "is_superuser": account.get("is_superuser", False),
            "is_active": not account.get("is_disabled", False),
            "attributes": attributes,
            "permissions": {
                "server_roles": permissions.get("server_roles", []),
                "server_permissions": permissions.get("server_permissions", []),
                "database_roles": permissions.get("database_roles", {}),
                "database_permissions": permissions.get("database_permissions", {}),
                "type_specific": permissions.get("type_specific", {}),
            },
        }

    # ------------------------------------------------------------------
    # 查询逻辑来源于旧实现
    # ------------------------------------------------------------------
    def _fetch_logins(self, connection: Any) -> List[Dict[str, Any]]:
        filter_rules = self.filter_manager.get_filter_rules("sqlserver")
        exclude_users = filter_rules.get("exclude_users", [])
        exclude_patterns = filter_rules.get("exclude_patterns", [])

        sql = """
            SELECT
                sp.name,
                sp.type_desc,
                sp.is_disabled,
                IS_SRVROLEMEMBER('sysadmin', sp.name) AS is_sysadmin
            FROM sys.server_principals sp
            WHERE sp.type IN ('S', 'U', 'G')
        """
        params: list[Any] = []
        if exclude_users:
            placeholders = ", ".join(["%s"] * len(exclude_users))
            sql += f" AND sp.name NOT IN ({placeholders})"
            params.extend(exclude_users)
        rows = connection.execute_query(sql, tuple(params) if params else None)

        results: List[Dict[str, Any]] = []
        for row in rows:
            name = row[0]
            if any(pattern and pattern in name for pattern in exclude_patterns):
                continue
            results.append(
                {
                    "name": name,
                    "type_desc": row[1],
                    "is_disabled": bool(row[2]),
                    "is_sysadmin": bool(row[3]),
                }
            )
        return results

    def _get_login_permissions(self, connection: Any, login_name: str) -> Dict[str, Any]:
        permissions = {
            "server_roles": self._get_server_roles(connection, login_name),
            "server_permissions": self._get_server_permissions(connection, login_name),
            "database_roles": self._get_database_roles(connection, login_name),
            "database_permissions": self._get_database_permissions(connection, login_name),
            "type_specific": {},
        }
        return permissions

    def _get_server_roles(self, connection: Any, login_name: str) -> List[str]:
        sql = """
            SELECT DISTINCT role.name
            FROM sys.server_role_members rm
            JOIN sys.server_principals role ON rm.role_principal_id = role.principal_id
            JOIN sys.server_principals member ON rm.member_principal_id = member.principal_id
            WHERE member.name = %s
        """
        rows = connection.execute_query(sql, (login_name,))
        return [row[0] for row in rows if row and row[0]]

    def _get_server_permissions(self, connection: Any, login_name: str) -> List[str]:
        sql = """
            SELECT DISTINCT permission_name
            FROM sys.server_permissions perm
            JOIN sys.server_principals sp ON perm.grantee_principal_id = sp.principal_id
            WHERE sp.name = %s
        """
        rows = connection.execute_query(sql, (login_name,))
        return [row[0] for row in rows if row and row[0]]

    def _get_database_roles(self, connection: Any, login_name: str) -> Dict[str, List[str]]:
        sql = """
            SELECT dp.name AS database_name, mp.name AS role_name
            FROM sys.server_principals sp
            JOIN sys.database_principals mp ON mp.sid = sp.sid
            JOIN sys.databases dp ON dp.owner_sid = mp.sid
            WHERE sp.name = %s
        """
        rows = connection.execute_query(sql, (login_name,))
        db_roles: Dict[str, List[str]] = {}
        for row in rows:
            database = row[0]
            role = row[1]
            if not database or not role:
                continue
            db_roles.setdefault(database, []).append(role)
        return db_roles

    def _get_database_permissions(self, connection: Any, login_name: str) -> Dict[str, List[str]]:
        rows: List[tuple[Any, Any]] = []
        databases = connection.execute_query("SELECT name FROM sys.databases")
        for db_name_tuple in databases:
            database = db_name_tuple[0]
            if not database:
                continue
            safe_db_name = database.replace("]", "]]")
            quoted_db = f"[{safe_db_name}]"
            sql = f"""
                SELECT '{database}' AS database_name, perm.permission_name
                FROM {quoted_db}.sys.database_permissions perm
                JOIN {quoted_db}.sys.database_principals dp ON perm.grantee_principal_id = dp.principal_id
                WHERE dp.name = %s
            """
            db_rows = connection.execute_query(sql, (login_name,))
            rows.extend(db_rows)
        db_perms: Dict[str, List[str]] = {}
        for row in rows:
            database = row[0]
            permission = row[1]
            if not database or not permission:
                continue
            db_perms.setdefault(database, []).append(permission)
        return db_perms

    # 缓存操作
    def clear_user_cache(self, instance: Instance, username: str) -> bool:
        try:
            return cache_manager.invalidate_user_cache(instance.id, username)
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "clear_sqlserver_user_cache_failed",
                instance=instance.name,
                username=username,
                error=str(exc),
            )
            return False

    def clear_instance_cache(self, instance: Instance) -> bool:
        try:
            return cache_manager.invalidate_instance_cache(instance.id)
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "clear_sqlserver_instance_cache_failed",
                instance=instance.name,
                error=str(exc),
            )
            return False
