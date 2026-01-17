"""标签选项/下拉数据 Service.

覆盖 TagsIndexPage 与 TagsBatchAssignPage 的 read APIs.
"""

from __future__ import annotations

from typing import Any, cast

from app.core.types.tags_options import (
    TaggableInstance,
    TagOptionItem,
    TagOptionsResult,
    TagsBulkInstancesResult,
    TagsBulkTagsResult,
)
from app.repositories.tags_options_repository import TagsOptionsRepository


class TagOptionsService:
    """标签选项读取服务."""

    def __init__(self, repository: TagsOptionsRepository | None = None) -> None:
        """初始化服务并注入标签选项仓库."""
        self._repository = repository or TagsOptionsRepository()

    @staticmethod
    def _coalesce_int(value: Any) -> int:
        # 仅将 None 视为缺省；避免 `value or 0` 这类 truthy 兜底链混淆语义。
        return int(value) if value is not None else 0

    @staticmethod
    def _coalesce_str(value: Any) -> str:
        # 仅将 None 视为缺省；避免 `value or ""` 覆盖合法 falsy（例如 0）。
        return str(value) if value is not None else ""

    def list_taggable_instances(self) -> TagsBulkInstancesResult:
        """列出可批量打标签的实例列表."""
        instances = self._repository.list_instances()
        return TagsBulkInstancesResult(
            instances=[self._to_instance(instance) for instance in instances],
        )

    def list_all_tags(self) -> TagsBulkTagsResult:
        """列出全部标签及分类映射."""
        tags = self._repository.list_all_tags()
        category_names = dict(self._repository.list_categories())
        return TagsBulkTagsResult(
            tags=[self._to_tag(tag) for tag in tags],
            category_names=cast("dict[str, str]", category_names),
        )

    def list_tag_options(self, category: str | None) -> TagOptionsResult:
        """获取标签下拉选项."""
        tags = self._repository.list_active_tags(category=category)
        normalized_category: str | None = None
        if category is not None:
            cleaned = category.strip()
            if cleaned != "":
                normalized_category = cleaned
        return TagOptionsResult(
            tags=[self._to_tag(tag) for tag in tags],
            category=normalized_category,
        )

    def list_categories(self) -> list:
        """列出标签分类."""
        return self._repository.list_categories()

    @staticmethod
    def _to_instance(instance: Any) -> TaggableInstance:
        resolved = cast("Any", instance)
        return TaggableInstance(
            id=TagOptionsService._coalesce_int(getattr(resolved, "id", None)),
            name=TagOptionsService._coalesce_str(getattr(resolved, "name", None)),
            host=TagOptionsService._coalesce_str(getattr(resolved, "host", None)),
            port=cast("int | None", getattr(resolved, "port", None)),
            db_type=TagOptionsService._coalesce_str(getattr(resolved, "db_type", None)),
        )

    @staticmethod
    def _to_tag(tag: Any) -> TagOptionItem:
        resolved = cast("Any", tag)
        return TagOptionItem(
            id=TagOptionsService._coalesce_int(getattr(resolved, "id", None)),
            name=TagOptionsService._coalesce_str(getattr(resolved, "name", None)),
            display_name=TagOptionsService._coalesce_str(getattr(resolved, "display_name", None)),
            category=TagOptionsService._coalesce_str(getattr(resolved, "category", None)),
            color=TagOptionsService._coalesce_str(getattr(resolved, "color", None)),
            color_value=TagOptionsService._coalesce_str(getattr(resolved, "color_value", None)),
            color_name=TagOptionsService._coalesce_str(getattr(resolved, "color_name", None)),
            css_class=TagOptionsService._coalesce_str(getattr(resolved, "css_class", None)),
            is_active=bool(getattr(resolved, "is_active", False)),
            created_at=(resolved.created_at.isoformat() if getattr(resolved, "created_at", None) else None),
            updated_at=(resolved.updated_at.isoformat() if getattr(resolved, "updated_at", None) else None),
        )
