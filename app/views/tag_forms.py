"""标签表单视图."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask import request, url_for

from app.forms.definitions.tag import TAG_FORM_DEFINITION
from app.views.form_handlers.tag_form_handler import TagFormHandler
from app.views.mixins.resource_forms import ResourceFormView

if TYPE_CHECKING:
    from app.models.tag import Tag
else:
    Tag = Any


class TagFormView(ResourceFormView[Tag]):
    """统一处理标签创建与编辑的视图.

    Attributes:
        form_definition: 标签表单定义配置.

    """

    form_definition = TAG_FORM_DEFINITION
    service_class = TagFormHandler

    def _resolve_success_redirect(self, instance: Tag) -> str:
        """解析成功后的重定向地址.

        Args:
            instance: 标签实例对象.

        Returns:
            重定向的 URL 字符串.

        """
        if request.view_args and request.view_args.get("tag_id"):
            return url_for("tags.edit", tag_id=instance.id)
        return super()._resolve_success_redirect(instance)

    def get_success_message(self, instance: Tag) -> str:
        """获取成功消息.

        Args:
            instance: 标签实例对象,当前实现未依赖该参数.

        Returns:
            成功消息字符串.

        """
        del instance
        if request.view_args and request.view_args.get("tag_id"):
            return "标签更新成功"
        return "标签创建成功"
