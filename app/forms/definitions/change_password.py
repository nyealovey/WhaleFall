"""
修改密码表单定义
"""

from app.forms.definitions.base import FieldComponent, ResourceFormDefinition, ResourceFormField
from app.services.form_service.password_service import ChangePasswordFormService

CHANGE_PASSWORD_FORM_DEFINITION = ResourceFormDefinition(
    name="change_password",
    template="auth/change_password.html",
    service_class=ChangePasswordFormService,
    success_message="密码修改成功",
    redirect_endpoint="auth.profile",
    fields=[
        ResourceFormField(
            name="old_password",
            label="当前密码",
            component=FieldComponent.TEXT,
            required=True,
        ),
        ResourceFormField(
            name="new_password",
            label="新密码",
            component=FieldComponent.TEXT,
            required=True,
        ),
        ResourceFormField(
            name="confirm_password",
            label="确认新密码",
            component=FieldComponent.TEXT,
            required=True,
        ),
    ],
    extra_config={
        "show_strength_indicator": True,
    },
)
