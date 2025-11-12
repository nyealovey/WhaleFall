"""
实例表单视图
"""

from flask import request, url_for

from app.forms.definitions.instance import INSTANCE_FORM_DEFINITION
from app.views.mixins.resource_form_view import ResourceFormView


class InstanceFormView(ResourceFormView):
    """统一处理实例创建与编辑的视图。"""

    form_definition = INSTANCE_FORM_DEFINITION

    def _resolve_success_redirect(self, instance):
        if request.view_args and (request.view_args.get("resource_id") or request.view_args.get("instance_id")):
            return url_for("instance_detail.detail", instance_id=instance.id)
        return super()._resolve_success_redirect(instance)

    def get_success_message(self, instance):
        if request.view_args and (request.view_args.get("resource_id") or request.view_args.get("instance_id")):
            return "实例更新成功！"
        return "实例创建成功！"
