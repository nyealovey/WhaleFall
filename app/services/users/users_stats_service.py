"""用户统计 Service.

职责:
- 组织 repository 调用并输出稳定 DTO/结构
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.users_repository import UsersRepository


class UsersStatsService:
    """用户统计读取服务."""

    def __init__(self, repository: UsersRepository | None = None) -> None:
        self._repository = repository or UsersRepository()

    def get_stats(self) -> dict[str, int]:
        return self._repository.fetch_stats()

