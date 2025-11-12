"""
凭据表单视图
"""

from flask import request, url_for

from app.forms.definitions.credential import CREDENTIAL_FORM_DEFINITION
from app.routes.mixins.resource_form_view import ResourceFormView


class CredentialFormView(ResourceFormView):
    form_definition = CREDENTIAL_FORM_DEFINITION

    def _resolve_success_redirect(self, instance):
        if request.view_args and request.view_args.get("credential_id"):
            return url_for("credentials.detail", credential_id=instance.id)
        return super()._resolve_success_redirect(instance)

    def get_success_message(self, instance):
        if request.view_args and request.view_args.get("credential_id"):
            return "凭据更新成功！"
        return "凭据创建成功！"
