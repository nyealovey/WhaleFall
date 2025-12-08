"""凭据表单定义."""

from app.forms.definitions.base import FieldComponent, ResourceFormDefinition, ResourceFormField
from app.services.form_service.credential_service import CredentialFormService

CREDENTIAL_FORM_DEFINITION = ResourceFormDefinition(
    name="credential",
    template="credentials/form.html",
    service_class=CredentialFormService,
    success_message="凭据保存成功!",
    redirect_endpoint="credentials.index",
    fields=[
        ResourceFormField(
            name="name",
            label="凭据名称",
            required=True,
            help_text="用于标识此凭据的唯一名称",
        ),
        ResourceFormField(
            name="credential_type",
            label="凭据类型",
            component=FieldComponent.SELECT,
            required=True,
        ),
        ResourceFormField(
            name="username",
            label="用户名",
            required=True,
        ),
        ResourceFormField(
            name="password",
            label="密码",
            required=True,
        ),
        ResourceFormField(
            name="db_type",
            label="数据库类型",
            component=FieldComponent.SELECT,
        ),
        ResourceFormField(
            name="description",
            label="描述",
            component=FieldComponent.TEXTAREA,
            props={"rows": 3},
        ),
        ResourceFormField(
            name="is_active",
            label="启用此凭据",
            component=FieldComponent.SWITCH,
            default=True,
        ),
    ],
)
