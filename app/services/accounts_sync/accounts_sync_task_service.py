"""账户同步任务编排 Service(Tasks 专用).

职责:
- 为 tasks 提供最小的读取能力(例如活跃实例列表),避免 tasks 直接 `.query`
- 不返回 Response、不 commit
"""

from __future__ import annotations

from app.models.instance import Instance
from app.repositories.filter_options_repository import FilterOptionsRepository


class AccountsSyncTaskService:
    """账户同步任务所需的数据读取服务."""

    def __init__(self, repository: FilterOptionsRepository | None = None) -> None:
        self._repository = repository or FilterOptionsRepository()

    def list_active_instances(self) -> list[Instance]:
        """获取启用的数据库实例列表."""
        return self._repository.list_active_instances()

