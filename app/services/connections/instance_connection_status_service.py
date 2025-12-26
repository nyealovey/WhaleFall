"""实例连接状态 Service.

职责:
- 组织 InstancesRepository 调用并输出稳定结构
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.errors import NotFoundError
from app.repositories.instances_repository import InstancesRepository
from app.types import JsonDict
from app.utils.time_utils import time_utils


class InstanceConnectionStatusService:
    """实例连接状态读取服务."""

    def __init__(self, repository: InstancesRepository | None = None) -> None:
        self._repository = repository or InstancesRepository()

    def get_status(self, instance_id: int) -> JsonDict:
        instance = self._repository.get_instance(instance_id)
        if not instance:
            raise NotFoundError("实例不存在")
        return self._build_connection_status_payload(instance)

    @staticmethod
    def _build_connection_status_payload(instance: object) -> JsonDict:
        resolved = instance
        last_connected_raw = getattr(resolved, "last_connected", None)
        last_connected = last_connected_raw.isoformat() if hasattr(last_connected_raw, "isoformat") else None

        status = "unknown"
        if last_connected_raw:
            last_connected_time = last_connected_raw
            if isinstance(last_connected_time, str):
                last_connected_time = datetime.fromisoformat(last_connected_time)
            delta = time_utils.now() - last_connected_time
            if delta < timedelta(hours=1):
                status = "good"
            elif delta < timedelta(days=1):
                status = "warning"
            else:
                status = "poor"

        return {
            "instance_id": getattr(resolved, "id", 0),
            "instance_name": getattr(resolved, "name", ""),
            "db_type": getattr(resolved, "db_type", ""),
            "host": getattr(resolved, "host", ""),
            "port": getattr(resolved, "port", None),
            "last_connected": last_connected,
            "status": status,
            "is_active": bool(getattr(resolved, "is_active", False)),
        }

