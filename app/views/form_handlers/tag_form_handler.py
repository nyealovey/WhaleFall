"""标签表单处理器(View layer)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.constants.colors import ThemeColors
from app.core.constants.tag_categories import TAG_CATEGORY_CHOICES
from app.services.tags.tag_detail_read_service import TagDetailReadService
from app.services.tags.tag_write_service import TagWriteService
from app.core.types import ResourceContext, ResourceIdentifier, ResourcePayload

if TYPE_CHECKING:
    from app.models.tag import Tag


class TagFormHandler:
    """标签表单处理器.

    约束:
    - 不直接访问数据库
    - load/upsert 均通过 Service 完成
    """

    def __init__(
        self,
        *,
        detail_service: TagDetailReadService | None = None,
        write_service: TagWriteService | None = None,
    ) -> None:
        self._detail_service = detail_service or TagDetailReadService()
        self._write_service = write_service or TagWriteService()

    def load(self, resource_id: ResourceIdentifier) -> "Tag | None":
        """加载标签资源."""
        if not isinstance(resource_id, int):
            return None
        return self._detail_service.get_tag_by_id(resource_id)

    def upsert(self, payload: ResourcePayload, resource: "Tag | None" = None) -> "Tag":
        """创建或更新标签."""
        if resource is None:
            return self._write_service.create(payload)
        return self._write_service.update(resource.id, payload)

    def build_context(self, *, resource: "Tag | None") -> ResourceContext:
        """构造表单渲染上下文."""
        del resource
        color_options = [
            {
                "value": key,
                "name": info["name"],
                "description": info["description"],
                "css_class": info["css_class"],
            }
            for key, info in ThemeColors.COLOR_MAP.items()
        ]
        category_options = [{"value": value, "label": label} for value, label in TAG_CATEGORY_CHOICES]
        return {
            "color_options": color_options,
            "category_options": category_options,
        }

