"""Oracle 账户同步适配器（两阶段版）。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.constants import DatabaseType
from app.models.instance import Instance
from app.services.account_sync.adapters.base_adapter import BaseAccountAdapter
from app.services.account_sync.account_sync_filters import DatabaseFilterManager
from app.utils.structlog_config import get_sync_logger


class OracleAccountAdapter(BaseAccountAdapter):
    def __init__(self) -> None:
        self.logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()

    def _fetch_raw_accounts(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:  # noqa: ANN401
        try:
            users = self._fetch_users(connection)
            accounts: List[Dict[str, Any]] = []
            for user in users:
                username = user["username"]
                account_status = user["account_status"]
                is_locked = account_status.upper() != "OPEN"
                permissions = self._get_user_permissions(connection, username)
                permissions.setdefault("type_specific", {})["account_status"] = account_status
                accounts.append(
                    {
                        "username": username,
                        "is_superuser": user.get("is_dba", False),
                        "is_locked": is_locked,
                        "permissions": permissions,
                    }
                )
            return accounts
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "fetch_oracle_accounts_failed",
                module="oracle_account_adapter",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            return []

    def _normalize_account(self, instance: Instance, account: Dict[str, Any]) -> Dict[str, Any]:
        permissions = account.get("permissions", {})
        attributes = {
            "account_status": permissions.get("type_specific", {}).get("account_status"),
        }
        return {
            "username": account["username"],
            "display_name": account["username"],
            "db_type": DatabaseType.ORACLE,
            "is_superuser": account.get("is_superuser", False),
            "is_active": not account.get("is_locked", False),
            "attributes": attributes,
            "permissions": {
                "oracle_roles": permissions.get("oracle_roles", []),
                "system_privileges": permissions.get("system_privileges", []),
                "tablespace_privileges_oracle": permissions.get("tablespace_privileges", {}),
                "type_specific": permissions.get("type_specific", {}),
            },
        }

    # ------------------------------------------------------------------
    def _fetch_users(self, connection: Any) -> List[Dict[str, Any]]:
        filter_rules = self.filter_manager.get_filter_rules("oracle")
        exclude_users = filter_rules.get("exclude_users", [])
        placeholders = ",".join([":{}".format(i) for i in range(1, len(exclude_users) + 1)]) or "''"

        sql = f"
            SELECT username, account_status, default_tablespace
            FROM dba_users
            WHERE username NOT IN ({placeholders})
        "
        params = {f":{i+1}": user for i, user in enumerate(exclude_users)}
        rows = connection.execute_query(sql, params)
        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "username": row[0],
                    "account_status": row[1],
                    "default_tablespace": row[2],
                    "is_dba": row[0] == "SYS",
                }
            )
        return results

    def _get_user_permissions(self, connection: Any, username: str) -> Dict[str, Any]:
        permissions = {
            "oracle_roles": self._get_roles(connection, username),
            "system_privileges": self._get_system_privileges(connection, username),
            "tablespace_privileges": self._get_tablespace_privileges(connection, username),
            "type_specific": {},
        }
        return permissions

    def _get_roles(self, connection: Any, username: str) -> List[str]:
        sql = "SELECT granted_role FROM dba_role_privs WHERE grantee = :1"
        rows = connection.execute_query(sql, {":1": username})
        return [row[0] for row in rows if row and row[0]]

    def _get_system_privileges(self, connection: Any, username: str) -> List[str]:
        sql = "SELECT privilege FROM dba_sys_privs WHERE grantee = :1"
        rows = connection.execute_query(sql, {":1": username})
        return [row[0] for row in rows if row and row[0]]

    def _get_tablespace_privileges(self, connection: Any, username: str) -> Dict[str, Dict[str, Any]]:
        sql = "SELECT tablespace_name, privilege FROM dba_ts_privs WHERE grantee = :1"
        rows = connection.execute_query(sql, {":1": username})
        privileges: Dict[str, List[str]] = {}
        for row in rows:
            tablespace = row[0]
            privilege = row[1]
            if not tablespace or not privilege:
                continue
            privileges.setdefault(tablespace, []).append(privilege)
        return privileges
