"""AccountsLedgersPage 权限详情 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from app.constants import DatabaseType, ErrorCategory, ErrorSeverity, HttpStatus
from app.errors import AppError
from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository
from app.services.accounts_permissions.legacy_adapter import build_ledger_permissions_payload
from app.services.accounts_permissions.snapshot_view import build_permission_snapshot_view
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
        instance_db_type = cast(str, getattr(instance, "db_type", None) or "").lower()

        snapshot = build_permission_snapshot_view(account)
        if "SNAPSHOT_MISSING" in (snapshot.get("errors") or []):
            raise AppError(
                message_key="SNAPSHOT_MISSING",
                status_code=HttpStatus.CONFLICT,
                category=ErrorCategory.BUSINESS,
                severity=ErrorSeverity.MEDIUM,
            )
        snapshot_payload = build_ledger_permissions_payload(snapshot, instance_db_type)

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
            permissions.global_privileges = cast("list[str]", snapshot_payload.get("global_privileges") or [])
            permissions.database_privileges = cast("dict[str, Any]", snapshot_payload.get("database_privileges") or {})
        elif instance and instance.db_type == DatabaseType.POSTGRESQL:
            permissions.predefined_roles = cast("list[str]", snapshot_payload.get("predefined_roles") or [])
            permissions.role_attributes = cast("dict[str, Any]", snapshot_payload.get("role_attributes") or {})
            permissions.database_privileges_pg = cast("dict[str, Any]", snapshot_payload.get("database_privileges_pg") or {})
        elif instance and instance.db_type == DatabaseType.SQLSERVER:
            permissions.server_roles = cast("list[str]", snapshot_payload.get("server_roles") or [])
            permissions.server_permissions = cast("list[str]", snapshot_payload.get("server_permissions") or [])
            permissions.database_roles = cast("dict[str, Any]", snapshot_payload.get("database_roles") or {})
            raw_db_perms = snapshot_payload.get("database_permissions") or {}
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
            permissions.oracle_roles = cast("list[str]", snapshot_payload.get("oracle_roles") or [])
            permissions.oracle_system_privileges = cast("list[str]", snapshot_payload.get("oracle_system_privileges") or [])

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
