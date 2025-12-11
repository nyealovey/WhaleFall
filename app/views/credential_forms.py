"""凭据表单视图."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask import request, url_for

from app.forms.definitions.credential import CREDENTIAL_FORM_DEFINITION
from app.views.mixins.resource_forms import ResourceFormView

if TYPE_CHECKING:
    from app.models.credential import Credential
else:
    Credential = Any


class CredentialFormView(ResourceFormView[Credential]):
    """统一处理凭据创建与编辑的视图.

    Attributes:
        form_definition: 凭据表单定义配置.

    """

    form_definition = CREDENTIAL_FORM_DEFINITION

    def _resolve_success_redirect(self, instance: Credential) -> str:
        """解析成功后的重定向地址.

        Args:
            instance: 凭据实例对象.

        Returns:
            重定向的 URL 字符串.

        """
        if request.view_args and request.view_args.get("credential_id"):
            return url_for("credentials.detail", credential_id=instance.id)
        return super()._resolve_success_redirect(instance)

    def get_success_message(self, instance: Credential) -> str:
        """获取成功消息.

        Args:
            instance: 凭据实例对象,当前实现未直接使用.

        Returns:
            成功消息字符串.

        """
        del instance
        if request.view_args and request.view_args.get("credential_id"):
            return "凭据更新成功!"
        return "凭据创建成功!"
