"""标签表单处理器."""

from __future__ import annotations

from typing import cast

from app.constants.colors import ThemeColors
from app.models.tag import Tag
from app.services.tags.tag_write_service import TagWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload


class TagFormHandler:
    """标签表单处理器."""

    def __init__(self, service: TagWriteService | None = None) -> None:
        """初始化表单处理器并注入写服务."""
        self._service = service or TagWriteService()

    def load(self, resource_id: ResourceIdentifier) -> Tag | None:
        """加载标签资源."""
        if not isinstance(resource_id, int):
            return None
        return cast("Tag | None", Tag.query.get(resource_id))

    def upsert(self, payload: ResourcePayload, resource: Tag | None = None) -> Tag:
        """创建或更新标签."""
        if resource is None:
            return self._service.create(payload)
        return self._service.update(resource.id, payload)

    def build_context(self, *, resource: Tag | None) -> ResourceContext:
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
        category_options = [{"value": value, "label": label} for value, label in Tag.get_category_choices()]
        return {
            "color_options": color_options,
            "category_options": category_options,
        }
