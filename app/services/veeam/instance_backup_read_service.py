"""实例备份信息读取服务."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.core.exceptions import NotFoundError
from app.repositories.instances_repository import InstancesRepository
from app.repositories.veeam_repository import VeeamRepository
from app.utils.time_utils import time_utils


def resolve_backup_status(*, latest_backup_at: str | None) -> str:
    """根据最近备份时间推导备份状态."""
    if not latest_backup_at:
        return "not_backed_up"
    resolved = time_utils.to_utc(latest_backup_at)
    if resolved is None:
        return "not_backed_up"
    if time_utils.now() - resolved <= timedelta(hours=24):
        return "backed_up"
    return "backup_stale"


class InstanceBackupInfoReadService:
    """实例备份信息读取服务."""

    def __init__(
        self,
        *,
        instances_repository: InstancesRepository | None = None,
        veeam_repository: VeeamRepository | None = None,
    ) -> None:
        self._instances_repository = instances_repository or InstancesRepository()
        self._veeam_repository = veeam_repository or VeeamRepository()

    def get_backup_info(self, instance_id: int) -> dict[str, Any]:
        """获取实例备份信息."""
        instance = self._instances_repository.get_instance(instance_id)
        if instance is None or instance.deleted_at is not None:
            raise NotFoundError("实例不存在")

        matched = self._veeam_repository.find_best_backup_for_instance_name(instance.name)
        latest_backup_at = matched.get("latest_backup_at") if isinstance(matched, dict) else None
        return {
            "instance_id": int(instance.id),
            "instance_name": instance.name,
            "backup_status": resolve_backup_status(
                latest_backup_at=latest_backup_at if isinstance(latest_backup_at, str) else None
            ),
            "backup_last_time": latest_backup_at if isinstance(latest_backup_at, str) else None,
            "matched_machine_name": matched.get("matched_machine_name") if isinstance(matched, dict) else None,
            "match_candidates": matched.get("match_candidates") if isinstance(matched, dict) else [instance.name],
            "backup_id": matched.get("backup_id") if isinstance(matched, dict) else None,
            "backup_file_id": matched.get("backup_file_id") if isinstance(matched, dict) else None,
            "job_name": matched.get("job_name") if isinstance(matched, dict) else None,
            "restore_point_name": matched.get("restore_point_name") if isinstance(matched, dict) else None,
            "source_record_id": matched.get("source_record_id") if isinstance(matched, dict) else None,
            "restore_point_size_bytes": matched.get("restore_point_size_bytes") if isinstance(matched, dict) else None,
            "backup_chain_size_bytes": matched.get("backup_chain_size_bytes") if isinstance(matched, dict) else None,
            "restore_point_count": matched.get("restore_point_count") if isinstance(matched, dict) else None,
            "last_sync_time": matched.get("last_sync_time") if isinstance(matched, dict) else None,
            "message": "获取备份信息成功",
        }
