"""实例列表 Service.

职责:
- 组织 repository 调用并将领域对象转换为稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.instances_repository import InstancesRepository
from app.core.types.instances import InstanceListFilters, InstanceListItem
from app.core.types.listing import PaginatedResult


class InstanceListService:
    """实例列表业务编排服务."""

    def __init__(self, repository: InstancesRepository | None = None) -> None:
        """初始化服务并注入实例仓库."""
        self._repository = repository or InstancesRepository()

    def list_instances(self, filters: InstanceListFilters) -> PaginatedResult[InstanceListItem]:
        """分页列出实例列表."""
        page_result, metrics = self._repository.list_instances(filters)
        items: list[InstanceListItem] = []
        for instance in page_result.items:
            last_sync = metrics.last_sync_times.get(instance.id)
            status_value = "deleted" if instance.deleted_at else ("active" if instance.is_active else "inactive")
            items.append(
                InstanceListItem(
                    id=instance.id,
                    name=instance.name,
                    db_type=instance.db_type,
                    host=instance.host,
                    port=instance.port,
                    description=instance.description or "",
                    is_active=instance.is_active,
                    deleted_at=instance.deleted_at.isoformat() if instance.deleted_at else None,
                    status=status_value,
                    main_version=instance.main_version,
                    active_db_count=metrics.database_counts.get(instance.id, 0),
                    active_account_count=metrics.account_counts.get(instance.id, 0),
                    last_sync_time=last_sync.isoformat() if last_sync else None,
                    tags=metrics.tags_map.get(instance.id, []),
                ),
            )

        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )
