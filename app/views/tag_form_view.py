"""
标签表单视图
"""

from flask import request, url_for

from app.forms.definitions.tag import TAG_FORM_DEFINITION
from app.views.mixins.resource_form_view import ResourceFormView


class TagFormView(ResourceFormView):
    form_definition = TAG_FORM_DEFINITION

    def _resolve_success_redirect(self, instance):
        if request.view_args and request.view_args.get("tag_id"):
            return url_for("tags.edit", tag_id=instance.id)
        return super()._resolve_success_redirect(instance)

    def get_success_message(self, instance):
        if request.view_args and request.view_args.get("tag_id"):
            return "标签更新成功"
        return "标签创建成功"
