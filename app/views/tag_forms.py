"""
标签表单视图
"""

from flask import request, url_for

from app.forms.definitions.tag import TAG_FORM_DEFINITION
from app.views.mixins.resource_forms import ResourceFormView


class TagFormView(ResourceFormView):
    """统一处理标签创建与编辑的视图。
    
    Attributes:
        form_definition: 标签表单定义配置。

    """

    form_definition = TAG_FORM_DEFINITION

    def _resolve_success_redirect(self, instance):
        """解析成功后的重定向地址。
        
        Args:
            instance: 标签实例对象。
            
        Returns:
            重定向的 URL 字符串。

        """
        if request.view_args and request.view_args.get("tag_id"):
            return url_for("tags.edit", tag_id=instance.id)
        return super()._resolve_success_redirect(instance)

    def get_success_message(self, instance):
        """获取成功消息。
        
        Args:
            instance: 标签实例对象。
            
        Returns:
            成功消息字符串。

        """
        if request.view_args and request.view_args.get("tag_id"):
            return "标签更新成功"
        return "标签创建成功"
