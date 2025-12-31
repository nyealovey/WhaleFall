"""标签选项/下拉数据 Service.

覆盖 TagsIndexPage 与 TagsBatchAssignPage 的 read APIs.
"""

from __future__ import annotations

from typing import Any, cast

from app.repositories.tags_options_repository import TagsOptionsRepository
from app.types.tags_options import (
    TaggableInstance,
    TagOptionItem,
    TagOptionsResult,
    TagsBulkInstancesResult,
    TagsBulkTagsResult,
)


class TagOptionsService:
    """标签选项读取服务."""

    def __init__(self, repository: TagsOptionsRepository | None = None) -> None:
        self._repository = repository or TagsOptionsRepository()

    def list_taggable_instances(self) -> TagsBulkInstancesResult:
        instances = self._repository.list_instances()
        return TagsBulkInstancesResult(
            instances=[self._to_instance(instance) for instance in instances],
        )

    def list_all_tags(self) -> TagsBulkTagsResult:
        tags = self._repository.list_all_tags()
        category_names = dict(self._repository.list_categories())
        return TagsBulkTagsResult(
            tags=[self._to_tag(tag) for tag in tags],
            category_names=cast("dict[str, str]", category_names),
        )

    def list_tag_options(self, category: str | None) -> TagOptionsResult:
        tags = self._repository.list_active_tags(category=category)
        normalized_category = (category or "").strip() or None
        return TagOptionsResult(
            tags=[self._to_tag(tag) for tag in tags],
            category=normalized_category,
        )

    def list_categories(self) -> list:
        return self._repository.list_categories()

    @staticmethod
    def _to_instance(instance: Any) -> TaggableInstance:
        return TaggableInstance(
            id=int(getattr(instance, "id", 0) or 0),
            name=cast(str, getattr(instance, "name", "") or ""),
            host=cast(str, getattr(instance, "host", "") or ""),
            port=cast("int | None", getattr(instance, "port", None)),
            db_type=cast(str, getattr(instance, "db_type", "") or ""),
        )

    @staticmethod
    def _to_tag(tag: Any) -> TagOptionItem:
        return TagOptionItem(
            id=int(getattr(tag, "id", 0) or 0),
            name=cast(str, getattr(tag, "name", "") or ""),
            display_name=cast(str, getattr(tag, "display_name", "") or ""),
            category=cast(str, getattr(tag, "category", "") or ""),
            color=cast(str, getattr(tag, "color", "") or ""),
            color_value=cast(str, getattr(tag, "color_value", "") or ""),
            color_name=cast(str, getattr(tag, "color_name", "") or ""),
            css_class=cast(str, getattr(tag, "css_class", "") or ""),
            is_active=bool(getattr(tag, "is_active", False)),
            created_at=(tag.created_at.isoformat() if getattr(tag, "created_at", None) else None),
            updated_at=(tag.updated_at.isoformat() if getattr(tag, "updated_at", None) else None),
        )
