"""标签详情 Service.

职责:
- 组织 repository 调用
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.errors import NotFoundError
from app.models.tag import Tag
from app.repositories.tags_repository import TagsRepository


class TagDetailReadService:
    """标签详情读取服务."""

    def __init__(self, repository: TagsRepository | None = None) -> None:
        """初始化服务并注入标签仓库."""
        self._repository = repository or TagsRepository()

    def get_tag_by_id(self, tag_id: int) -> Tag | None:
        """按 ID 获取标签(可为空)."""
        return self._repository.get_by_id(tag_id)

    def get_tag_or_error(self, tag_id: int) -> Tag:
        """按 ID 获取标签(不存在则抛错)."""
        tag = self.get_tag_by_id(tag_id)
        if tag is None:
            raise NotFoundError("标签不存在", extra={"tag_id": tag_id})
        return tag

