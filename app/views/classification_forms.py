"""账户分类与规则表单视图."""

from flask import request, url_for

from app.forms.definitions.account_classification import CLASSIFICATION_FORM_DEFINITION
from app.forms.definitions.account_classification_rule import CLASSIFICATION_RULE_FORM_DEFINITION
from app.views.mixins.resource_forms import ResourceFormView


class AccountClassificationFormView(ResourceFormView):
    """统一处理账户分类创建与编辑的视图.

    Attributes:
        form_definition: 账户分类表单定义配置.

    """

    form_definition = CLASSIFICATION_FORM_DEFINITION

    def _resolve_success_redirect(self, instance):
        """解析成功后的重定向地址.

        Args:
            instance: 账户分类实例对象.

        Returns:
            重定向的 URL 字符串.

        """
        return url_for("account_classification.index")

    def _success_redirect_kwargs(self, instance):
        """获取重定向的额外参数.

        Args:
            instance: 账户分类实例对象.

        Returns:
            空字典.

        """
        return {}

    def get_success_message(self, instance) -> str:
        """获取成功消息.

        Args:
            instance: 账户分类实例对象.

        Returns:
            成功消息字符串.

        """
        return "账户分类更新成功" if request.view_args.get("resource_id") else "账户分类创建成功"


class ClassificationRuleFormView(ResourceFormView):
    """统一处理分类规则创建与编辑的视图.

    Attributes:
        form_definition: 分类规则表单定义配置.

    """

    form_definition = CLASSIFICATION_RULE_FORM_DEFINITION

    def _resolve_success_redirect(self, instance):
        """解析成功后的重定向地址.

        Args:
            instance: 分类规则实例对象.

        Returns:
            重定向的 URL 字符串.

        """
        return url_for("account_classification.index")

    def get_success_message(self, instance) -> str:
        """获取成功消息.

        Args:
            instance: 分类规则实例对象.

        Returns:
            成功消息字符串.

        """
        return "分类规则更新成功" if request.view_args.get("resource_id") else "分类规则创建成功"
