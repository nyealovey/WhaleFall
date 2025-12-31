"""实例详情 Service.

职责:
- 组织 repository 调用
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.models.instance import Instance
from app.repositories.instances_repository import InstancesRepository


class InstanceDetailReadService:
    """实例详情读取服务."""

    def __init__(self, repository: InstancesRepository | None = None) -> None:
        self._repository = repository or InstancesRepository()

    def get_active_instance(self, instance_id: int) -> Instance:
        return self._repository.get_active_instance(instance_id)
