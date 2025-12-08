"""
实例表单视图
"""

from flask import request, url_for

from app.forms.definitions.instance import INSTANCE_FORM_DEFINITION
from app.views.mixins.resource_forms import ResourceFormView


class InstanceFormView(ResourceFormView):
    """统一处理实例创建与编辑的视图。
    
    Attributes:
        form_definition: 实例表单定义配置。

    """

    form_definition = INSTANCE_FORM_DEFINITION

    def _resolve_success_redirect(self, instance):
        """解析成功后的重定向地址。
        
        Args:
            instance: 实例对象。
            
        Returns:
            重定向的 URL 字符串。

        """
        if request.view_args and (request.view_args.get("resource_id") or request.view_args.get("instance_id")):
            return url_for("instances_detail.detail", instance_id=instance.id)
        return super()._resolve_success_redirect(instance)

    def get_success_message(self, instance):
        """获取成功消息。
        
        Args:
            instance: 实例对象。
            
        Returns:
            成功消息字符串。

        """
        if request.view_args and (request.view_args.get("resource_id") or request.view_args.get("instance_id")):
            return "实例更新成功！"
        return "实例创建成功！"
