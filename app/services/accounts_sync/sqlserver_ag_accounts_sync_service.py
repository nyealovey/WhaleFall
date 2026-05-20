"""SQL Server contained AG 账户同步服务."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from app.core.constants import DatabaseType
from app.models.instance import Instance
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerClusterInstance
from app.services.accounts_sync.adapters.factory import get_account_adapter
from app.services.accounts_sync.inventory_manager import AccountInventoryManager
from app.services.accounts_sync.permission_manager import AccountPermissionManager, PermissionSyncError
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.core.types import RemoteAccount, SyncConnection


class SQLServerAgAccountsSyncService:
    """同步实例所属群集内启用 contained 的 AG 账户."""

    def __init__(
        self,
        *,
        inventory_manager: AccountInventoryManager | None = None,
        permission_manager: AccountPermissionManager | None = None,
    ) -> None:
        self._inventory_manager = inventory_manager or AccountInventoryManager()
        self._permission_manager = permission_manager or AccountPermissionManager()
        self._logger = get_sync_logger()

    def sync_for_instance(self, instance: Instance, *, session_id: str | None = None) -> dict[str, Any]:
        """同步实例所属群集下所有启用 contained 的 AG 账户."""
        if str(instance.db_type).lower() != DatabaseType.SQLSERVER:
            return {"status": "skipped", "processed_records": 0, "items": []}

        binding = SQLServerClusterInstance.query.filter_by(instance_id=instance.id).first()
        if binding is None:
            return {"status": "skipped", "processed_records": 0, "items": []}
        if not binding.cluster or not binding.cluster.is_enabled:
            return {"status": "skipped", "processed_records": 0, "items": []}

        ags = (
            SQLServerAvailabilityGroup.query.filter_by(
                cluster_id=binding.cluster_id,
                contained_enabled=True,
                is_enabled=True,
            )
            .filter(SQLServerAvailabilityGroup.account_credential_id.isnot(None))
            .order_by(SQLServerAvailabilityGroup.name.asc())
            .all()
        )
        items = [self._sync_one_ag(instance, ag, session_id=session_id) for ag in ags]
        processed = sum(int(item.get("processed_records", 0) or 0) for item in items)
        failed = sum(1 for item in items if item.get("status") == "failed")
        return {
            "status": "failed" if failed else "completed",
            "processed_records": processed,
            "total_ag": len(items),
            "failed_ag": failed,
            "items": items,
        }

    def _sync_one_ag(
        self,
        instance: Instance,
        ag: SQLServerAvailabilityGroup,
        *,
        session_id: str | None,
    ) -> dict[str, Any]:
        connection: SyncConnection | None = None
        try:
            target = self._build_ag_connection_instance(instance, ag)
            connection = cast("SyncConnection | None", ConnectionFactory.create_connection(target))
            self._ensure_ag_connection(connection)

            adapter = get_account_adapter(DatabaseType.SQLSERVER)
            remote_accounts = adapter.fetch_remote_accounts(target, connection)
            remote_accounts = adapter.enrich_permissions(target, connection, remote_accounts)
            scoped_accounts = self._with_ag_owner(remote_accounts, ag)
            inventory, active_accounts = self._inventory_manager.synchronize(instance, scoped_accounts)
            collection = self._permission_manager.synchronize(
                instance,
                scoped_accounts,
                active_accounts,
                session_id=session_id,
            )
        except (PermissionSyncError, RuntimeError, ValueError, LookupError, ConnectionError, TimeoutError, OSError) as exc:
            ag.last_sync_at = time_utils.now()
            ag.last_sync_status = "failed"
            ag.last_error = str(exc)
            self._logger.exception(
                "sqlserver_ag_accounts_sync_failed",
                module="accounts_sync",
                phase="sqlserver_ag",
                instance_id=instance.id,
                instance_name=instance.name,
                availability_group_id=ag.id,
                availability_group_name=ag.name,
                error=str(exc),
            )
            return {"ag_id": ag.id, "ag_name": ag.name, "status": "failed", "processed_records": 0, "error": str(exc)}
        finally:
            if connection is not None:
                connection.disconnect()

        ag.last_sync_at = time_utils.now()
        ag.last_sync_status = "completed"
        ag.last_error = None
        processed = int(collection.get("processed_records", 0) or 0)
        return {
            "ag_id": ag.id,
            "ag_name": ag.name,
            "status": "completed",
            "processed_records": processed,
            "inventory": inventory,
            "collection": collection,
        }

    @staticmethod
    def _build_ag_connection_instance(instance: Instance, ag: SQLServerAvailabilityGroup) -> Instance:
        target = Instance(
            id=instance.id,
            name=f"{instance.name}/{ag.name}",
            db_type=DatabaseType.SQLSERVER,
            host=ag.listener_host,
            port=ag.listener_port,
            database_name=ag.connection_database or "master",
            credential_id=ag.account_credential_id,
            is_active=True,
        )
        target.credential = ag.account_credential
        return target

    @staticmethod
    def _ensure_ag_connection(connection: SyncConnection | None) -> None:
        if connection is None or not connection.connect():
            raise RuntimeError("AG 监听器连接失败")

    @staticmethod
    def _with_ag_owner(
        remote_accounts: list[RemoteAccount],
        ag: SQLServerAvailabilityGroup,
    ) -> list[RemoteAccount]:
        scoped_accounts: list[RemoteAccount] = []
        for account in remote_accounts:
            scoped = dict(cast("dict[str, Any]", account))
            scoped["owner_type"] = "sqlserver_ag"
            scoped["owner_id"] = ag.id
            scoped["cluster_id"] = ag.cluster_id
            scoped["availability_group_id"] = ag.id
            permissions_value = scoped.get("permissions")
            permissions = dict(cast("dict[str, Any]", permissions_value)) if isinstance(permissions_value, dict) else {}
            type_specific_value = permissions.get("type_specific")
            type_specific = (
                dict(cast("dict[str, Any]", type_specific_value)) if isinstance(type_specific_value, dict) else {}
            )
            type_specific["security_scope"] = "contained_availability_group"
            type_specific["availability_group_name"] = ag.name
            permissions["type_specific"] = type_specific
            scoped["permissions"] = permissions
            scoped_accounts.append(cast("RemoteAccount", scoped))
        return scoped_accounts
