"""
用户表单视图
"""

from flask import request

from app.forms.definitions.user import USER_FORM_DEFINITION
from app.routes.mixins.resource_form_view import ResourceFormView


class UserFormView(ResourceFormView):
    form_definition = USER_FORM_DEFINITION

    def get_success_message(self, instance):
        if request.view_args and request.view_args.get("user_id"):
            return "用户信息已更新"
        return "用户创建成功"
