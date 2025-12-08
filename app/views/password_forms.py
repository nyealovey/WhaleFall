"""修改密码表单视图."""

from flask_login import current_user

from app.forms.definitions.change_password import CHANGE_PASSWORD_FORM_DEFINITION
from app.views.mixins.resource_forms import ResourceFormView


class ChangePasswordFormView(ResourceFormView):
    """统一处理修改密码的视图。.

    Attributes:
        form_definition: 修改密码表单定义配置。

    """

    form_definition = CHANGE_PASSWORD_FORM_DEFINITION

    def _load_resource(self, resource_id):
        """加载用户资源。.

        Args:
            resource_id: 资源 ID（未使用）。

        Returns:
            当前登录用户对象，如果未登录则返回 None。

        """
        if current_user.is_authenticated:
            return current_user
        return None
