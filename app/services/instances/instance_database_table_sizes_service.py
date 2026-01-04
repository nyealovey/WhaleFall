"""实例详情-数据库表容量 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.instance_database_table_sizes_repository import (
    InstanceDatabaseTableSizesRepository,
)
from app.types.instance_database_table_sizes import (
    InstanceDatabaseTableSizesQuery,
    InstanceDatabaseTableSizesResult,
)


class InstanceDatabaseTableSizesService:
    """实例数据库表容量读取服务."""

    def __init__(self, repository: InstanceDatabaseTableSizesRepository | None = None) -> None:
        self._repository = repository or InstanceDatabaseTableSizesRepository()

    def fetch_snapshot(self, options: InstanceDatabaseTableSizesQuery) -> InstanceDatabaseTableSizesResult:
        return self._repository.fetch_snapshot(options)
