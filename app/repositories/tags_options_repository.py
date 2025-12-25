"""标签选项/下拉数据 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from app.models.instance import Instance
from app.models.tag import Tag


class TagsOptionsRepository:
    """标签选项读模型 Repository."""

    @staticmethod
    def list_instances() -> list[Instance]:
        return Instance.query.all()

    @staticmethod
    def list_all_tags() -> list[Tag]:
        return Tag.query.all()

    @staticmethod
    def list_active_tags(*, category: str | None = None) -> list[Tag]:
        normalized = (category or "").strip()
        if normalized:
            return Tag.get_tags_by_category(normalized)
        return Tag.get_active_tags()

    @staticmethod
    def list_categories() -> list:
        return Tag.get_category_choices()

