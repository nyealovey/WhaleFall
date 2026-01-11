"""修改密码表单视图."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from flask_login import current_user

from app.forms.definitions.change_password import CHANGE_PASSWORD_FORM_DEFINITION
from app.views.form_handlers.change_password_form_handler import ChangePasswordFormHandler
from app.views.mixins.resource_forms import ResourceFormView

if TYPE_CHECKING:
    from app.models.user import User
else:
    User = Any


class ChangePasswordFormView(ResourceFormView[User]):
    """统一处理修改密码的视图.

    Attributes:
        form_definition: 修改密码表单定义配置.

    """

    form_definition = CHANGE_PASSWORD_FORM_DEFINITION
    service_class = ChangePasswordFormHandler

    def _load_resource(self, resource_id: int | None) -> User | None:
        """加载用户资源.

        Args:
            resource_id: 资源 ID,当前实现忽略该参数,统一从会话获取用户.

        Returns:
            当前登录用户对象,如果未登录则返回 None.

        """
        del resource_id
        if current_user.is_authenticated:
            return cast("User", current_user)
        return None
