"""实例审计信息读取服务."""

from __future__ import annotations

from typing import Any

from app.core.constants import DatabaseType
from app.core.exceptions import NotFoundError
from app.repositories.instance_config_snapshots_repository import InstanceConfigSnapshotsRepository
from app.repositories.instances_repository import InstancesRepository
from app.services.config_sync.sqlserver_audit_info_sync_service import AUDIT_INFO_CONFIG_KEY
from app.utils.database_type_utils import normalize_database_type

UNSUPPORTED_AUDIT_MESSAGE = "当前实例类型暂不支持审计信息采集"
AUDIT_NOT_COLLECTED_MESSAGE = "尚未采集审计信息"


class InstanceAuditInfoReadService:
    """实例审计信息读取服务."""

    def __init__(
        self,
        repository: InstanceConfigSnapshotsRepository | None = None,
        instances_repository: InstancesRepository | None = None,
    ) -> None:
        self._repository = repository or InstanceConfigSnapshotsRepository()
        self._instances_repository = instances_repository or InstancesRepository()

    def get_audit_info(self, instance_id: int) -> dict[str, Any]:
        instance = self._instances_repository.get_instance(instance_id)
        if instance is None or instance.deleted_at is not None:
            raise NotFoundError("实例不存在")

        db_type = normalize_database_type(instance.db_type)
        base_payload = {
            "instance_id": int(instance.id),
            "instance_name": instance.name,
            "db_type": db_type,
            "config_key": AUDIT_INFO_CONFIG_KEY,
        }
        if db_type != DatabaseType.SQLSERVER:
            return {
                **base_payload,
                "supported": False,
                "available": False,
                "last_sync_time": None,
                "snapshot": None,
                "facts": None,
                "message": UNSUPPORTED_AUDIT_MESSAGE,
            }

        snapshot_row = self._repository.get_by_instance_and_key(
            instance_id=instance.id,
            config_key=AUDIT_INFO_CONFIG_KEY,
        )
        if snapshot_row is None:
            return {
                **base_payload,
                "supported": True,
                "available": False,
                "last_sync_time": None,
                "snapshot": None,
                "facts": None,
                "message": AUDIT_NOT_COLLECTED_MESSAGE,
            }

        return {
            **base_payload,
            "supported": True,
            "available": snapshot_row.snapshot is not None,
            "last_sync_time": (
                snapshot_row.last_sync_time.isoformat() if snapshot_row.last_sync_time is not None else None
            ),
            "snapshot": snapshot_row.snapshot,
            "facts": snapshot_row.facts,
            "message": "获取审计信息成功",
        }

