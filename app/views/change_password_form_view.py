"""
修改密码表单视图
"""

from flask_login import current_user

from app.forms.definitions.change_password import CHANGE_PASSWORD_FORM_DEFINITION
from app.views.mixins.resource_form_view import ResourceFormView


class ChangePasswordFormView(ResourceFormView):
    form_definition = CHANGE_PASSWORD_FORM_DEFINITION

    def _load_resource(self, resource_id):
        if current_user.is_authenticated:
            return current_user
        return None
