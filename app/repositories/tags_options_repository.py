"""标签选项/下拉数据 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from app import db
from app.models.instance import Instance
from app.models.tag import Tag


class TagsOptionsRepository:
    """标签选项读模型 Repository."""

    @staticmethod
    def list_instances() -> list[Instance]:
        """列出所有实例."""
        return Instance.query.all()

    @staticmethod
    def list_all_tags() -> list[Tag]:
        """列出全部标签."""
        return Tag.query.all()

    @staticmethod
    def list_active_tags(*, category: str | None = None) -> list[Tag]:
        """列出可用标签(可按分类过滤)."""
        normalized = category.strip() if category is not None else ""
        if normalized:
            return Tag.get_tags_by_category(normalized)
        return Tag.get_active_tags()

    @staticmethod
    def list_categories() -> list[str]:
        """列出标签分类.

        标签分类是完全自定义的，因此直接从 tags 表中读取去重后的 category 列表。
        """
        category_column = cast(Any, Tag.category)
        rows = db.session.query(category_column).distinct().order_by(category_column.asc()).all()
        return [category for (category,) in rows if category]
