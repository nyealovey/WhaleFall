"""实例详情中的 SQL Server AG 账户读取服务."""

from __future__ import annotations

from typing import Any, cast

from app.models.account_permission import AccountPermission
from app.models.instance_account import InstanceAccount
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance
from app.services.ledgers.accounts_ledger_list_service import LOCKED_REASON_LABELS


class InstanceAgAccountsService:
    """按实例所属群集读取 contained AG 账户."""

    def list_for_instance(self, instance_id: int, *, search: str = "", include_deleted: bool = False) -> dict[str, Any]:
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
                SQLServerAvailabilityGroup.is_enabled.is_(True),
                SQLServerAvailabilityGroup.contained_enabled.is_(True),
            )
            .order_by(SQLServerAvailabilityGroup.name.asc(), AccountPermission.username.asc())
        )
        if not include_deleted:
            query = query.filter(InstanceAccount.is_active.is_(True))
        normalized_search = search.strip()
        if normalized_search:
            query = query.filter(AccountPermission.username.contains(normalized_search))
        items = [self._serialize_account(row) for row in query.all()]
        return {
            "cluster": {
                "id": cluster.id,
                "name": cluster.name,
            },
            "items": items,
            "total": len(items),
            "summary": self._summarize(items),
        }

    @staticmethod
    def _serialize_account(account: AccountPermission) -> dict[str, Any]:
        ag = SQLServerAvailabilityGroup.query.get(account.availability_group_id)
        instance_account = account.instance_account
        is_active = bool(instance_account.is_active) if instance_account else True
        type_specific = account.type_specific if isinstance(account.type_specific, dict) else {}
        return {
            "id": account.instance_account_id,
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
            "is_active": is_active,
            "is_deleted": not is_active,
            "availability_reasons": InstanceAgAccountsService._build_availability_reasons(account.permission_facts),
            "last_change_time": account.last_change_time.isoformat() if account.last_change_time else None,
            "last_sync_time": account.last_sync_time.isoformat() if account.last_sync_time else None,
            "type_specific": type_specific,
        }

    @staticmethod
    def _build_availability_reasons(permission_facts: object) -> list[str]:
        if not isinstance(permission_facts, dict):
            return []
        capability_reasons = permission_facts.get("capability_reasons")
        if not isinstance(capability_reasons, dict):
            return []
        locked_reasons = capability_reasons.get("LOCKED")
        if not isinstance(locked_reasons, list):
            return []
        labels: list[str] = []
        for reason in locked_reasons:
            if not isinstance(reason, str):
                continue
            label = LOCKED_REASON_LABELS.get(reason)
            if label and label not in labels:
                labels.append(label)
        return labels

    @staticmethod
    def _summarize(items: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "total": len(items),
            "active": sum(1 for item in items if not item["is_deleted"]),
            "deleted": sum(1 for item in items if item["is_deleted"]),
            "superuser": sum(1 for item in items if item["is_superuser"]),
        }
