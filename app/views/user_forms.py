"""用户表单视图."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask import request

from app.forms.definitions.user import USER_FORM_DEFINITION
from app.views.mixins.resource_forms import ResourceFormView

if TYPE_CHECKING:
    from app.models.user import User
else:
    User = Any


class UserFormView(ResourceFormView[User]):
    """统一处理用户创建与编辑的视图.

    Attributes:
        form_definition: 用户表单定义配置.

    """

    form_definition = USER_FORM_DEFINITION

    def get_success_message(self, instance: User) -> str:
        """获取成功消息.

        Args:
            instance: 用户实例对象,当前未使用.

        Returns:
            成功消息字符串.

        """
        del instance
        if request.view_args and request.view_args.get("user_id"):
            return "用户信息已更新"
        return "用户创建成功"
