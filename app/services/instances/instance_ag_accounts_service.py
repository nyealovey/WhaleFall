"""实例详情中的 SQL Server AG 账户读取服务."""

from __future__ import annotations

from typing import Any, cast

from app.models.account_permission import AccountPermission
from app.models.instance_account import InstanceAccount
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance


class InstanceAgAccountsService:
    """按实例所属群集读取 contained AG 账户."""

    def list_for_instance(self, instance_id: int) -> dict[str, Any]:
        binding = SQLServerClusterInstance.query.filter_by(instance_id=instance_id).first()
        if binding is None:
            return {"cluster": None, "items": [], "total": 0}

        cluster = cast(SQLServerCluster, binding.cluster)
        if not cluster.is_enabled:
            return {"cluster": None, "items": [], "total": 0}

        query = (
            AccountPermission.query.join(
                InstanceAccount,
                AccountPermission.instance_account_id == InstanceAccount.id,
            )
            .join(
                SQLServerAvailabilityGroup,
                AccountPermission.availability_group_id == SQLServerAvailabilityGroup.id,
            )
            .filter(
                AccountPermission.owner_type == "sqlserver_ag",
                AccountPermission.cluster_id == cluster.id,
                InstanceAccount.is_active.is_(True),
                SQLServerAvailabilityGroup.is_enabled.is_(True),
                SQLServerAvailabilityGroup.contained_enabled.is_(True),
            )
            .order_by(SQLServerAvailabilityGroup.name.asc(), AccountPermission.username.asc())
        )
        items = [self._serialize_account(row) for row in query.all()]
        return {
            "cluster": {
                "id": cluster.id,
                "name": cluster.name,
            },
            "items": items,
            "total": len(items),
        }

    @staticmethod
    def _serialize_account(account: AccountPermission) -> dict[str, Any]:
        ag = SQLServerAvailabilityGroup.query.get(account.availability_group_id)
        type_specific = account.type_specific if isinstance(account.type_specific, dict) else {}
        return {
            "id": account.id,
            "username": account.username,
            "db_type": account.db_type,
            "owner_type": account.owner_type,
            "owner_id": account.owner_id,
            "cluster_id": account.cluster_id,
            "availability_group_id": account.availability_group_id,
            "availability_group_name": ag.name if ag else None,
            "listener_name": ag.listener_name if ag else None,
            "listener_host": ag.listener_host if ag else None,
            "is_locked": account.is_locked,
            "is_superuser": account.is_superuser,
            "last_sync_time": account.last_sync_time.isoformat() if account.last_sync_time else None,
            "type_specific": type_specific,
        }
