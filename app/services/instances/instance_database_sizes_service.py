"""实例详情-数据库容量(大小) Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.core.types.instance_database_sizes import (
    InstanceDatabaseSizesHistoryResult,
    InstanceDatabaseSizesLatestResult,
    InstanceDatabaseSizesQuery,
)
from app.repositories.instance_database_sizes_repository import InstanceDatabaseSizesRepository


class InstanceDatabaseSizesService:
    """实例数据库容量读取服务."""

    def __init__(self, repository: InstanceDatabaseSizesRepository | None = None) -> None:
        """初始化服务并注入仓库."""
        self._repository = repository or InstanceDatabaseSizesRepository()

    def fetch_sizes(
        self,
        options: InstanceDatabaseSizesQuery,
        *,
        latest_only: bool,
    ) -> InstanceDatabaseSizesLatestResult | InstanceDatabaseSizesHistoryResult:
        """查询数据库容量(最新或历史)."""
        return self._repository.fetch_latest(options) if latest_only else self._repository.fetch_history(options)
