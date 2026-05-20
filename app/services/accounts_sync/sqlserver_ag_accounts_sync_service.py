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


class _AgConnectionError(RuntimeError):
    """AG 连接失败并保留尝试过的 endpoint."""

    def __init__(self, message: str, attempted_endpoints: list[str]) -> None:
        super().__init__(message)
        self.attempted_endpoints = attempted_endpoints


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
        target: Instance | None = None
        attempted_endpoints: list[str] = []
        try:
            target, connection, attempted_endpoints = self._connect_to_ag(instance, ag)

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
            attempted_endpoints = getattr(exc, "attempted_endpoints", attempted_endpoints)
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
            return {
                "ag_id": ag.id,
                "ag_name": ag.name,
                "listener_name": ag.listener_name,
                "listener_host": ag.listener_host,
                "connection_endpoint": self._build_ag_connection_host(ag),
                "attempted_endpoints": attempted_endpoints,
                "status": "failed",
                "processed_records": 0,
                "error": str(exc),
            }
        finally:
            if connection is not None:
                connection.disconnect()

        ag.last_sync_at = time_utils.now()
        ag.last_sync_status = "completed"
        ag.last_error = None
        processed = int(inventory.get("processed_records", 0) or 0)
        return {
            "ag_id": ag.id,
            "ag_name": ag.name,
            "listener_name": ag.listener_name,
            "listener_host": ag.listener_host,
            "connection_endpoint": target.host if target else self._build_ag_connection_host(ag),
            "attempted_endpoints": attempted_endpoints,
            "status": "completed",
            "processed_records": processed,
            "inventory": inventory,
            "collection": collection,
        }

    @classmethod
    def _connect_to_ag(
        cls,
        instance: Instance,
        ag: SQLServerAvailabilityGroup,
    ) -> tuple[Instance, SyncConnection, list[str]]:
        target = cls._build_ag_connection_instance(instance, ag)
        connection = cast("SyncConnection | None", ConnectionFactory.create_connection(target))
        endpoint = cls._format_endpoint(target.host, target.port)
        if connection is not None and connection.connect():
            return target, connection, [endpoint]

        detail = cls._connection_failure_detail(connection)
        if connection is not None:
            connection.disconnect()
        raise _AgConnectionError(f"AG 监听器连接失败: {endpoint} {detail}", [endpoint])

    @classmethod
    def _build_ag_connection_instance(cls, instance: Instance, ag: SQLServerAvailabilityGroup) -> Instance:
        host = cls._build_ag_connection_host(ag)
        if not host:
            raise RuntimeError("群集域名未配置，无法生成 Linux 可解析的 AG 侦听器连接地址")
        target = Instance(
            id=instance.id,
            name=f"{instance.name}/{ag.name}",
            db_type=DatabaseType.SQLSERVER,
            host=host,
            port=ag.listener_port,
            database_name=ag.connection_database or "master",
            credential_id=ag.account_credential_id,
            is_active=True,
        )
        target.credential = ag.account_credential
        return target

    @staticmethod
    def _build_ag_connection_host(ag: SQLServerAvailabilityGroup) -> str | None:
        listener_name = (ag.listener_name or "").strip()
        domain_name = ((ag.cluster.domain_name if ag.cluster else None) or "").strip().strip(".")
        if listener_name and domain_name:
            if "." in listener_name:
                return listener_name
            return f"{listener_name}.{domain_name}"
        if listener_name and not domain_name and "." not in listener_name:
            return None
        return (ag.listener_host or "").strip() or None

    @staticmethod
    def _format_endpoint(host: str, port: int | None) -> str:
        return f"{host}:{port or 1433}"

    @staticmethod
    def _connection_failure_detail(connection: SyncConnection | None) -> str:
        if connection is None:
            return "未创建连接"
        error_type = str(getattr(connection, "last_error_type", "") or "").strip()
        error = str(getattr(connection, "last_error", "") or "").strip()
        if error_type and error:
            return f"{error_type}: {error}"
        if error:
            return error
        return "连接返回失败"

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
