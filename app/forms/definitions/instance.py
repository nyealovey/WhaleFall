"""
实例表单定义
"""

from app.forms.definitions.base import FieldComponent, FieldOption, ResourceFormDefinition, ResourceFormField
from app.services.form_service.instances_form_service import InstanceFormService

INSTANCE_FORM_DEFINITION = ResourceFormDefinition(
    name="instance",
    template="instances/form.html",
    service_class=InstanceFormService,
    success_message="实例保存成功！",
    redirect_endpoint="instance.index",
    fields=[
        ResourceFormField(
            name="name",
            label="实例名称",
            required=True,
            help_text="用于标识数据库实例的名称，必须唯一",
        ),
        ResourceFormField(
            name="db_type",
            label="数据库类型",
            component=FieldComponent.SELECT,
            required=True,
            placeholder="请选择数据库类型",
        ),
        ResourceFormField(
            name="host",
            label="主机地址",
            required=True,
            placeholder="例如: localhost 或 192.168.1.100",
        ),
        ResourceFormField(
            name="port",
            label="端口号",
            component=FieldComponent.NUMBER,
            required=True,
            placeholder="5432",
        ),
        ResourceFormField(
            name="credential_id",
            label="凭据",
            component=FieldComponent.SELECT,
            required=True,
            placeholder="请选择凭据",
        ),
        ResourceFormField(
            name="database_name",
            label="数据库名称",
            help_text="不同数据库会有默认名称，可根据实际情况调整",
        ),
        ResourceFormField(
            name="description",
            label="描述",
            component=FieldComponent.TEXTAREA,
            props={"rows": 3},
        ),
        ResourceFormField(
            name="is_active",
            label="启用此实例",
            component=FieldComponent.SWITCH,
            default=True,
        ),
    ],
)
