"""标签列表 Service.

职责:
- 组织 repository 调用并将 ORM 对象转换为稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.tags_repository import TagsRepository
from app.core.types.listing import PaginatedResult
from app.core.types.tags import TagListFilters, TagListItem, TagStats


class TagListService:
    """标签列表业务编排服务."""

    def __init__(self, repository: TagsRepository | None = None) -> None:
        """初始化服务并注入标签仓库."""
        self._repository = repository or TagsRepository()

    def list_tags(self, filters: TagListFilters) -> tuple[PaginatedResult[TagListItem], TagStats]:
        """分页列出标签列表并返回统计."""
        page_result, stats = self._repository.list_tags(filters)
        items: list[TagListItem] = []
        for row in page_result.items:
            tag = row.tag
            items.append(
                TagListItem(
                    id=tag.id,
                    name=tag.name,
                    display_name=tag.display_name,
                    category=tag.category,
                    color=tag.color,
                    color_value=tag.color_value,
                    color_name=tag.color_name,
                    css_class=tag.css_class,
                    is_active=bool(tag.is_active),
                    created_at=tag.created_at.isoformat() if tag.created_at else None,
                    updated_at=tag.updated_at.isoformat() if tag.updated_at else None,
                    instance_count=row.instance_count,
                ),
            )
        return (
            PaginatedResult(
                items=items,
                total=page_result.total,
                page=page_result.page,
                pages=page_result.pages,
                limit=page_result.limit,
            ),
            stats,
        )
