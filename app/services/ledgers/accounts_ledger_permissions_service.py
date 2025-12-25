"""AccountsLedgersPage 权限详情 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from app.constants import DatabaseType
from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository
from app.types.accounts_permissions import (
    AccountLedgerPermissionAccount,
    AccountLedgerPermissions,
    AccountLedgerPermissionsResult,
)
from app.utils.time_utils import time_utils


class AccountsLedgerPermissionsService:
    """账户台账-权限详情读取服务."""

    def __init__(self, repository: AccountsLedgerRepository | None = None) -> None:
        self._repository = repository or AccountsLedgerRepository()

    def get_permissions(self, account_id: int) -> AccountLedgerPermissionsResult:
        account = self._repository.get_account_with_instance(account_id)
        instance = getattr(account, "instance", None)

        permissions = AccountLedgerPermissions(
            db_type=(cast(str, getattr(instance, "db_type", "")) or "").upper(),
            username=cast(str, getattr(account, "username", "")),
            is_superuser=bool(getattr(account, "is_superuser", False)),
            last_sync_time=(
                time_utils.format_china_time(getattr(account, "last_sync_time", None))
                if getattr(account, "last_sync_time", None)
                else "未知"
            ),
        )

        if instance and instance.db_type == DatabaseType.MYSQL:
            permissions.global_privileges = cast("list[str]", getattr(account, "global_privileges", None) or [])
            permissions.database_privileges = cast("dict[str, Any]", getattr(account, "database_privileges", None) or {})
        elif instance and instance.db_type == DatabaseType.POSTGRESQL:
            permissions.predefined_roles = cast("list[str]", getattr(account, "predefined_roles", None) or [])
            permissions.role_attributes = cast("dict[str, Any]", getattr(account, "role_attributes", None) or {})
            permissions.database_privileges_pg = cast(
                "dict[str, Any]",
                getattr(account, "database_privileges_pg", None) or {},
            )
            permissions.tablespace_privileges = cast(
                "dict[str, Any]",
                getattr(account, "tablespace_privileges", None) or {},
            )
        elif instance and instance.db_type == DatabaseType.SQLSERVER:
            permissions.server_roles = cast("list[str]", getattr(account, "server_roles", None) or [])
            permissions.server_permissions = cast("list[str]", getattr(account, "server_permissions", None) or [])
            permissions.database_roles = cast("dict[str, Any]", getattr(account, "database_roles", None) or {})

            raw_db_perms = getattr(account, "database_permissions", None) or {}
            simplified: dict[str, list[str]] = {}
            if isinstance(raw_db_perms, dict):
                for db_name, entry in raw_db_perms.items():
                    if not isinstance(entry, dict):
                        continue
                    db_perm_list: list[str] = []
                    db_level = entry.get("database")
                    if isinstance(db_level, list):
                        db_perm_list.extend([p for p in db_level if isinstance(p, str)])
                    simplified[cast(str, db_name)] = db_perm_list
            permissions.database_permissions = simplified
        elif instance and instance.db_type == DatabaseType.ORACLE:
            permissions.oracle_roles = cast("list[str]", getattr(account, "oracle_roles", None) or [])
            permissions.oracle_system_privileges = cast("list[str]", getattr(account, "system_privileges", None) or [])
            permissions.oracle_tablespace_privileges = cast(
                "dict[str, Any]",
                getattr(account, "tablespace_privileges_oracle", None) or {},
            )

        account_payload = AccountLedgerPermissionAccount(
            id=cast(int, getattr(account, "id", 0)),
            username=cast(str, getattr(account, "username", "")),
            instance_name=cast(str, getattr(instance, "name", None) or "未知实例"),
            db_type=cast(str, getattr(instance, "db_type", None) or ""),
        )
        return AccountLedgerPermissionsResult(
            permissions=permissions,
            account=account_payload,
        )

