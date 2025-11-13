"""
用户表单定义
"""

from app.forms.definitions.base import FieldComponent, ResourceFormDefinition, ResourceFormField
from app.services.form_service.users_form_service import UserFormService

USER_FORM_DEFINITION = ResourceFormDefinition(
    name="user",
    template="users/form.html",
    service_class=UserFormService,
    success_message="用户保存成功",
    redirect_endpoint="users.index",
    fields=[
        ResourceFormField(
            name="username",
            label="用户名",
            required=True,
            help_text="仅支持字母、数字和下划线，长度3-20位",
        ),
        ResourceFormField(
            name="password",
            label="密码",
            required=True,
            help_text="至少8位，包含大小写字母与数字",
        ),
        ResourceFormField(
            name="role",
            label="角色",
            component=FieldComponent.SELECT,
            required=True,
        ),
        ResourceFormField(
            name="is_active",
            label="激活状态",
            component=FieldComponent.SWITCH,
            default=True,
        ),
    ],
    extra_config={
        "password_optional_on_edit": True,
    },
)
