"""实例详情-账户相关 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from app.core.constants import DatabaseType
from app.repositories.instance_accounts_repository import InstanceAccountsRepository
from app.services.accounts_permissions.snapshot_view import build_permission_snapshot_view
from app.core.types.instance_accounts import (
    InstanceAccountChangeHistoryAccount,
    InstanceAccountChangeHistoryResult,
    InstanceAccountChangeLogItem,
    InstanceAccountInfo,
    InstanceAccountListFilters,
    InstanceAccountListItem,
    InstanceAccountListResult,
    InstanceAccountPermissions,
    InstanceAccountPermissionsResult,
)
from app.utils.time_utils import time_utils


class InstanceAccountsService:
    """实例详情账户读取服务."""

    def __init__(self, repository: InstanceAccountsRepository | None = None) -> None:
        """初始化服务并注入实例账户仓库."""
        self._repository = repository or InstanceAccountsRepository()

    def list_accounts(self, filters: InstanceAccountListFilters) -> InstanceAccountListResult:
        """分页列出实例账户列表."""
        instance = self._repository.get_instance(filters.instance_id)
        summary = self._repository.fetch_summary(filters.instance_id)
        page_result = self._repository.list_accounts(filters)

        items: list[InstanceAccountListItem] = []
        for account in page_result.items:
            instance_account = getattr(account, "instance_account", None)
            is_active = bool(instance_account and getattr(instance_account, "is_active", False))
            type_specific = cast("dict[str, Any]", getattr(account, "type_specific", None) or {})

            item = InstanceAccountListItem(
                id=cast(int, getattr(account, "id", 0)),
                username=cast(str, getattr(account, "username", "")),
                is_superuser=bool(getattr(account, "is_superuser", False)),
                is_locked=bool(getattr(account, "is_locked", False)),
                is_deleted=not is_active,
                last_change_time=(
                    cast("Any", getattr(account, "last_change_time", None)).isoformat()
                    if getattr(account, "last_change_time", None)
                    else None
                ),
                type_specific=type_specific,
            )

            if filters.include_permissions:
                snapshot = build_permission_snapshot_view(account)
                categories = snapshot.get("categories")
                if instance.db_type == DatabaseType.SQLSERVER and isinstance(categories, dict):
                    server_roles = categories.get("server_roles")
                    server_permissions = categories.get("server_permissions")
                    database_roles = categories.get("database_roles")
                    database_permissions = categories.get("database_permissions")

                    item.server_roles = cast("list[str]", server_roles) if isinstance(server_roles, list) else []
                    item.server_permissions = (
                        cast("list[str]", server_permissions) if isinstance(server_permissions, list) else []
                    )
                    item.database_roles = (
                        cast("dict[str, Any]", database_roles) if isinstance(database_roles, dict) else {}
                    )
                    item.database_permissions = (
                        cast("dict[str, Any]", database_permissions) if isinstance(database_permissions, dict) else {}
                    )

            if instance.db_type == DatabaseType.MYSQL:
                item.host = cast(str, type_specific.get("host", "%"))
                item.plugin = cast(str, type_specific.get("plugin", ""))
            elif instance.db_type == DatabaseType.SQLSERVER:
                item.password_change_time = cast("str | None", type_specific.get("password_change_time"))
            elif instance.db_type == DatabaseType.ORACLE:
                item.oracle_id = cast("int | str | None", type_specific.get("oracle_id"))
                item.authentication_type = cast("str | None", type_specific.get("authentication_type"))
                item.account_status = cast("str | None", type_specific.get("account_status"))
                item.lock_date = cast("str | None", type_specific.get("lock_date"))
                item.expiry_date = cast("str | None", type_specific.get("expiry_date"))
                item.default_tablespace = cast("str | None", type_specific.get("default_tablespace"))
                item.created = cast("str | None", type_specific.get("created"))

            items.append(item)

        return InstanceAccountListResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
            summary=summary,
        )

    def get_account_permissions(self, instance_id: int, account_id: int) -> InstanceAccountPermissionsResult:
        """获取账户权限详情."""
        instance = self._repository.get_instance(instance_id)
        account = self._repository.get_account(instance_id=instance_id, account_id=account_id)

        snapshot = build_permission_snapshot_view(account)

        permissions = InstanceAccountPermissions(
            db_type=cast(str, getattr(instance, "db_type", "")).upper() if getattr(instance, "db_type", None) else "",
            username=cast(str, getattr(account, "username", "")),
            is_superuser=bool(getattr(account, "is_superuser", False)),
            last_sync_time=(
                time_utils.format_china_time(getattr(account, "last_sync_time", None))
                if getattr(account, "last_sync_time", None)
                else "未知"
            ),
            snapshot=snapshot,
        )

        account_info = InstanceAccountInfo(
            id=cast(int, getattr(account, "id", 0)),
            instance_id=instance_id,
            username=cast(str, getattr(account, "username", "")),
            instance_name=cast("str | None", getattr(instance, "name", None)),
            db_type=cast("str | None", getattr(instance, "db_type", None)),
        )

        return InstanceAccountPermissionsResult(
            permissions=permissions,
            account=account_info,
        )

    def get_change_history(self, instance_id: int, account_id: int) -> InstanceAccountChangeHistoryResult:
        """获取账户变更历史."""
        instance = self._repository.get_instance(instance_id)
        account = self._repository.get_account(instance_id=instance_id, account_id=account_id)
        username = cast(str, getattr(account, "username", ""))
        db_type = cast("str | None", getattr(instance, "db_type", None))

        change_logs = self._repository.list_change_logs(instance_id=instance_id, username=username, db_type=db_type)
        history_items: list[InstanceAccountChangeLogItem] = []
        for log_entry in change_logs:
            change_time = getattr(log_entry, "change_time", None)
            history_items.append(
                InstanceAccountChangeLogItem(
                    id=cast(int, getattr(log_entry, "id", 0)),
                    change_type=cast("str | None", getattr(log_entry, "change_type", None)),
                    change_time=(time_utils.format_china_time(change_time) if change_time else "未知"),
                    status=cast("str | None", getattr(log_entry, "status", None)),
                    message=cast("str | None", getattr(log_entry, "message", None)),
                    privilege_diff=getattr(log_entry, "privilege_diff", None),
                    other_diff=getattr(log_entry, "other_diff", None),
                    session_id=cast("str | None", getattr(log_entry, "session_id", None)),
                ),
            )

        return InstanceAccountChangeHistoryResult(
            account=InstanceAccountChangeHistoryAccount(
                id=cast(int, getattr(account, "id", 0)),
                username=username,
                db_type=db_type,
            ),
            history=history_items,
        )
