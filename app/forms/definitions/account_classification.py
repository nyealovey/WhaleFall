"""账户分类表单定义."""

from app.forms.definitions.base import FieldComponent, ResourceFormDefinition, ResourceFormField

CLASSIFICATION_FORM_DEFINITION = ResourceFormDefinition(
    name="account_classification",
    template="accounts/account-classification/classifications_form.html",
    success_message="账户分类保存成功",
    redirect_endpoint="accounts_classifications.index",
    fields=[
        ResourceFormField(
            name="code",
            label="分类标识(code)",
            required=True,
        ),
        ResourceFormField(
            name="display_name",
            label="分类名称",
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
            default=4,
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
            help_text="数字越大优先级越高,仅影响排序",
        ),
    ],
)
