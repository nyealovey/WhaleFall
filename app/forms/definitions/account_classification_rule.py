"""
账户分类规则表单定义
"""

from app.forms.definitions.base import FieldComponent, ResourceFormDefinition, ResourceFormField
from app.forms.definitions.account_classification_rule_constants import DB_TYPE_OPTIONS, OPERATOR_OPTIONS
from app.services.form_service.classification_rule_form_service import ClassificationRuleFormService

CLASSIFICATION_RULE_FORM_DEFINITION = ResourceFormDefinition(
    name="classification_rule",
    template="accounts/classification-rules/form.html",
    service_class=ClassificationRuleFormService,
    success_message="分类规则保存成功",
    redirect_endpoint="account_classification.index",
    fields=[
        ResourceFormField(
            name="classification_id",
            label="分类",
            component=FieldComponent.SELECT,
            required=True,
        ),
        ResourceFormField(
            name="rule_name",
            label="规则名称",
            required=True,
        ),
        ResourceFormField(
            name="db_type",
            label="数据库类型",
            component=FieldComponent.SELECT,
            required=True,
        ),
        ResourceFormField(
            name="operator",
            label="匹配逻辑",
            component=FieldComponent.SELECT,
            required=True,
            default="OR",
        ),
        ResourceFormField(
            name="rule_expression",
            label="权限配置",
            component=FieldComponent.TEXTAREA,
            help_text="JSON 格式的权限表达式，由前端权限配置器生成",
        ),
    ],
)
