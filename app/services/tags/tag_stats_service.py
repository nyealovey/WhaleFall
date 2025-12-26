"""标签统计 Service.

职责:
- 组织 repository 调用并输出稳定统计结构
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.tags_repository import TagsRepository
from app.types.tags import TagStats


class TagStatsService:
    """标签统计读取服务."""

    def __init__(self, repository: TagsRepository | None = None) -> None:
        self._repository = repository or TagsRepository()

    def get_stats(self) -> TagStats:
        return self._repository.get_stats()

