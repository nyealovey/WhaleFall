"""实例审计信息同步动作服务."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app import db
from app.core.constants import DatabaseType, HttpStatus
from app.core.constants.sync_constants import SyncCategory, SyncOperationType
from app.core.exceptions import NotFoundError
from app.models.instance import Instance
from app.models.instance_config_snapshot import InstanceConfigSnapshot
from app.repositories.instance_config_snapshots_repository import InstanceConfigSnapshotsRepository
from app.repositories.instances_repository import InstancesRepository
from app.services.config_sync.sqlserver_audit_info_sync_service import (
    AUDIT_INFO_CONFIG_KEY,
    SQLServerAuditInfoSyncService,
)
from app.services.sync_session_service import SyncItemStats, sync_session_service
from app.utils.database_type_utils import normalize_database_type
from app.utils.time_utils import time_utils


@dataclass(frozen=True, slots=True)
class InstanceAuditSyncActionResult:
    """实例审计同步动作结果."""

    success: bool
    message: str
    result: dict[str, Any]
    http_status: int = 200
    message_key: str = "OPERATION_SUCCESS"
    extra: Mapping[str, Any] | None = None


class InstanceAuditSyncActionsService:
    """实例审计同步动作编排服务."""

    def __init__(
        self,
        *,
        sync_service: SQLServerAuditInfoSyncService | None = None,
        snapshot_repository: InstanceConfigSnapshotsRepository | None = None,
        instances_repository: InstancesRepository | None = None,
    ) -> None:
        self._sync_service = sync_service or SQLServerAuditInfoSyncService()
        self._snapshot_repository = snapshot_repository or InstanceConfigSnapshotsRepository()
        self._instances_repository = instances_repository or InstancesRepository()

    def sync_instance_audit_info(
        self,
        *,
        instance_id: int,
        actor_id: int | None = None,
    ) -> InstanceAuditSyncActionResult:
        instance = self._get_instance(instance_id)
        if not instance.is_active:
            return InstanceAuditSyncActionResult(
                success=False,
                message=f"实例 {instance.name} 已停用，无法同步审计信息",
                result={},
                http_status=HttpStatus.BAD_REQUEST,
                message_key="INVALID_REQUEST",
                extra={"instance_id": instance.id},
            )

        if normalize_database_type(instance.db_type) != DatabaseType.SQLSERVER:
            return InstanceAuditSyncActionResult(
                success=False,
                message="当前实例类型暂不支持审计信息采集",
                result={},
                http_status=HttpStatus.CONFLICT,
                message_key="INVALID_REQUEST",
                extra={"instance_id": instance.id, "db_type": instance.db_type},
            )

        session = sync_session_service.create_session(
            sync_type=SyncOperationType.MANUAL_SINGLE.value,
            sync_category=SyncCategory.CONFIG.value,
            created_by=actor_id,
        )
        records = sync_session_service.add_instance_records(
            session.session_id,
            [instance.id],
            sync_category=SyncCategory.CONFIG.value,
        )
        session.total_instances = 1
        db.session.flush()
        record = records[0]
        sync_session_service.start_instance_sync(record.id)

        try:
            sync_payload = self._sync_service.sync_instance_audit(instance=instance)
            summary = sync_payload.get("summary", {})
            snapshot = sync_payload.get("snapshot")
            facts = sync_payload.get("facts")
            created = self._save_snapshot(instance=instance, snapshot=snapshot, facts=facts)
            sync_session_service.complete_instance_sync(
                record.id,
                stats=SyncItemStats(
                    items_synced=int(summary.get("audit_count", 0)) + int(summary.get("specification_count", 0)),
                    items_created=1 if created else 0,
                    items_updated=0 if created else 1,
                    items_deleted=0,
                ),
                sync_details={
                    "version": 1,
                    "config_key": AUDIT_INFO_CONFIG_KEY,
                    "summary": dict(summary),
                },
            )
        except Exception as exc:
            sync_session_service.fail_instance_sync(
                record.id,
                error_message=str(exc),
                sync_details={"version": 1, "config_key": AUDIT_INFO_CONFIG_KEY},
            )
            return InstanceAuditSyncActionResult(
                success=False,
                message=str(exc) or "同步审计信息失败",
                result={"session_id": session.session_id},
                http_status=HttpStatus.CONFLICT,
                message_key="SYNC_DATA_ERROR",
                extra={"instance_id": instance.id},
            )

        partial_success = bool(summary.get("partial_success"))
        message = (
            "审计信息同步部分成功，已保存服务器级结果"
            if partial_success
            else "审计信息同步成功"
        )
        return InstanceAuditSyncActionResult(
            success=True,
            message=message,
            result={
                "session_id": session.session_id,
                "summary": dict(summary),
                "config_key": AUDIT_INFO_CONFIG_KEY,
            },
        )

    def _save_snapshot(
        self,
        *,
        instance: Instance,
        snapshot: object,
        facts: object,
    ) -> bool:
        existing = self._snapshot_repository.get_by_instance_and_key(
            instance_id=instance.id,
            config_key=AUDIT_INFO_CONFIG_KEY,
        )
        created = existing is None
        row = existing or InstanceConfigSnapshot(
            instance_id=instance.id,
            db_type=normalize_database_type(instance.db_type),
            config_key=AUDIT_INFO_CONFIG_KEY,
        )
        row.db_type = normalize_database_type(instance.db_type)
        row.snapshot = snapshot if isinstance(snapshot, dict) else None
        row.facts = facts if isinstance(facts, dict) else None
        row.last_sync_time = time_utils.now()
        if created:
            self._snapshot_repository.add(row)
        else:
            self._snapshot_repository.flush()
        return created

    def _get_instance(self, instance_id: int) -> Instance:
        instance = self._instances_repository.get_instance(instance_id)
        if instance is None or instance.deleted_at is not None:
            raise NotFoundError("实例不存在")
        return instance
