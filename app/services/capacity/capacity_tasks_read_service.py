"""容量相关 tasks 读能力 Service.

职责:
- 为 `app/tasks/capacity_*` 提供最小读能力,避免 tasks 直接 `.query`
- 不返回 Response、不 commit
"""

from __future__ import annotations

from app.models.instance import Instance
from app.repositories.filter_options_repository import FilterOptionsRepository


class CapacityTasksReadService:
    """容量任务读取服务."""

    def __init__(self, repository: FilterOptionsRepository | None = None) -> None:
        self._repository = repository or FilterOptionsRepository()

    def list_active_instances(self, *, db_type: str | None = None) -> list[Instance]:
        """获取启用的实例列表(可按 db_type 过滤)."""
        return self._repository.list_active_instances(db_type=db_type)

