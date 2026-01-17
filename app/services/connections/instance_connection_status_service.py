"""实例连接状态 Service.

职责:
- 组织 InstancesRepository 调用并输出稳定结构
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.exceptions import NotFoundError
from app.core.types import JsonDict
from app.models.instance import Instance
from app.repositories.instances_repository import InstancesRepository
from app.utils.time_utils import time_utils


class InstanceConnectionStatusService:
    """实例连接状态读取服务."""

    def __init__(self, repository: InstancesRepository | None = None) -> None:
        """初始化服务并注入实例仓库."""
        self._repository = repository or InstancesRepository()

    def get_status(self, instance_id: int) -> JsonDict:
        """获取实例连接状态."""
        instance = self._repository.get_instance(instance_id)
        if not instance:
            raise NotFoundError("实例不存在")
        return self._build_connection_status_payload(instance)

    @staticmethod
    def _build_connection_status_payload(instance: Instance) -> JsonDict:
        last_connected_raw = instance.last_connected
        if isinstance(last_connected_raw, datetime):
            last_connected = last_connected_raw.isoformat()
        elif isinstance(last_connected_raw, str):
            last_connected = last_connected_raw
        else:
            last_connected = None

        status = "unknown"
        if last_connected_raw:
            last_connected_time = last_connected_raw
            if isinstance(last_connected_time, str):
                last_connected_time = datetime.fromisoformat(last_connected_time)
            if isinstance(last_connected_time, datetime) and last_connected_time.tzinfo is None:
                last_connected_time = last_connected_time.replace(tzinfo=time_utils.now().tzinfo)
            delta = time_utils.now() - last_connected_time
            if delta < timedelta(hours=1):
                status = "good"
            elif delta < timedelta(days=1):
                status = "warning"
            else:
                status = "poor"

        return {
            "instance_id": int(instance.id),
            "instance_name": instance.name,
            "db_type": instance.db_type,
            "host": instance.host,
            "port": instance.port,
            "last_connected": last_connected,
            "status": status,
            "is_active": bool(instance.is_active),
        }
