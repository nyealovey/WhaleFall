"""实例数据库详情 Service.

职责:
- 组织 repository 调用
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.models.instance_database import InstanceDatabase
from app.repositories.instance_databases_repository import InstanceDatabasesRepository


class InstanceDatabaseDetailReadService:
    """实例数据库详情读取服务."""

    def __init__(self, repository: InstanceDatabasesRepository | None = None) -> None:
        """初始化服务并注入实例数据库仓库."""
        self._repository = repository or InstanceDatabasesRepository()

    def get_by_id(self, database_id: int) -> InstanceDatabase | None:
        """按 ID 获取实例数据库记录(可为空)."""
        return self._repository.get_by_id(database_id)

    def get_by_id_or_error(self, database_id: int) -> InstanceDatabase:
        """按 ID 获取实例数据库记录(不存在则抛错)."""
        record = self.get_by_id(database_id)
        if record is None:
            raise NotFoundError("数据库不存在", extra={"database_id": database_id})
        return record

