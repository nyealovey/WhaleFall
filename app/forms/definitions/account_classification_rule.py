"""
账户分类规则表单定义
"""

from app.forms.definitions.base import FieldComponent, ResourceFormDefinition, ResourceFormField
from app.services.account_classification.rule_form_service import ClassificationRuleFormService

DB_TYPE_OPTIONS = [
    {"value": "mysql", "label": "MySQL"},
    {"value": "postgresql", "label": "PostgreSQL"},
    {"value": "sqlserver", "label": "SQL Server"},
    {"value": "oracle", "label": "Oracle"},
]

OPERATOR_OPTIONS = [
    {"value": "OR", "label": "OR (任一条件满足)"},
    {"value": "AND", "label": "AND (全部条件满足)"},
]

CLASSIFICATION_RULE_FORM_DEFINITION = ResourceFormDefinition(
    name="classification_rule",
    template="accounts/classification_rules/form.html",
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
