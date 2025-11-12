"""
账户分类与规则表单视图
"""

from flask import request, url_for

from app.forms.definitions.account_classification import CLASSIFICATION_FORM_DEFINITION
from app.forms.definitions.account_classification_rule import CLASSIFICATION_RULE_FORM_DEFINITION
from app.routes.mixins.resource_form_view import ResourceFormView


class AccountClassificationFormView(ResourceFormView):
    form_definition = CLASSIFICATION_FORM_DEFINITION

    def _resolve_success_redirect(self, instance):
        return url_for("account_classification.index")

    def _success_redirect_kwargs(self, instance):
        return {}

    def get_success_message(self, instance):
        return "账户分类更新成功" if request.view_args.get("resource_id") else "账户分类创建成功"


class ClassificationRuleFormView(ResourceFormView):
    form_definition = CLASSIFICATION_RULE_FORM_DEFINITION

    def _resolve_success_redirect(self, instance):
        return url_for("account_classification.index")

    def get_success_message(self, instance):
        return "分类规则更新成功" if request.view_args.get("resource_id") else "分类规则创建成功"
