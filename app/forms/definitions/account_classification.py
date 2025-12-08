"""账户分类表单定义."""

from app.forms.definitions.base import FieldComponent, ResourceFormDefinition, ResourceFormField
from app.services.form_service.classification_service import ClassificationFormService

CLASSIFICATION_FORM_DEFINITION = ResourceFormDefinition(
    name="account_classification",
    template="accounts/account-classification/classifications_form.html",
    service_class=ClassificationFormService,
    success_message="账户分类保存成功",
    redirect_endpoint="account_classification.index",
    fields=[
        ResourceFormField(
            name="name",
            label="分类名称",
            required=True,
        ),
        ResourceFormField(
            name="description",
            label="描述",
            component=FieldComponent.TEXTAREA,
            props={"rows": 3},
        ),
        ResourceFormField(
            name="risk_level",
            label="风险等级",
            component=FieldComponent.SELECT,
            default="medium",
        ),
        ResourceFormField(
            name="color",
            label="显示颜色",
            component=FieldComponent.SELECT,
            required=True,
        ),
        ResourceFormField(
            name="icon_name",
            label="图标",
            component=FieldComponent.SELECT,
            default="fa-tag",
        ),
        ResourceFormField(
            name="priority",
            label="优先级",
            component=FieldComponent.NUMBER,
            default=0,
            help_text="数字越大优先级越高，用于控制显示顺序和规则匹配顺序",
        ),
    ],
)
