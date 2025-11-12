"""
通用资源表单视图
------------------
集成 GET/POST 逻辑，依赖 ResourceFormDefinition 与 BaseResourceService。
"""

from __future__ import annotations

from typing import Any, Mapping

from flask import (
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.views import MethodView

from app.constants import FlashCategory
from app.forms.definitions import ResourceFormDefinition
from app.services.resource_form_service import BaseResourceService, ServiceResult


class ResourceFormView(MethodView):
    """通用 GET/POST 视图，子类只需设置 form_definition。"""

    form_definition: ResourceFormDefinition

    def __init__(self):
        if not getattr(self, "form_definition", None):
            raise RuntimeError(f"{self.__class__.__name__} 未配置 form_definition")
        self.service: BaseResourceService = self.form_definition.service_class()

    # ------------------------------------------------------------------ #
    # HTTP Methods
    # ------------------------------------------------------------------ #
    def get(self, resource_id: int | None = None, **kwargs) -> str:
        resource = self._load_resource(self._resolve_resource_id(resource_id, kwargs))
        context = self._build_context(resource, form_data=None)
        return render_template(self.form_definition.template, **context)

    def post(self, resource_id: int | None = None, **kwargs) -> str | Response:
        resource = self._load_resource(self._resolve_resource_id(resource_id, kwargs))
        payload = self._extract_payload(request)

        result = self.service.upsert(payload, resource)
        if result.success and result.data is not None:
            flash(
                self.get_success_message(result.data),
                FlashCategory.SUCCESS,
            )
            return redirect(self._resolve_success_redirect(result.data))

        context = self._build_context(resource, form_data=payload, errors=result.message or "保存失败")
        flash(result.message or "保存失败", FlashCategory.ERROR)
        return render_template(self.form_definition.template, **context)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _load_resource(self, resource_id: int | None):
        if resource_id is None:
            return None
        return self.service.load(resource_id)

    def _resolve_resource_id(self, resource_id: int | None, kwargs: dict[str, Any]) -> int | None:
        if resource_id is not None:
            return resource_id
        for key in ("instance_id", "credential_id", "tag_id", "classification_id", "rule_id"):
            if kwargs.get(key) is not None:
                return kwargs[key]
        return None

    def _extract_payload(self, req) -> Mapping[str, Any]:
        if req.is_json:
            return req.get_json(silent=True) or {}
        return req.form

    def _build_context(
        self,
        resource: Any | None,
        form_data: Mapping[str, Any] | None,
        errors: str | None = None,
    ) -> dict[str, Any]:
        base_context = {
            "resource": resource,
            "form_mode": "edit" if resource else "create",
            "form_definition": self.form_definition,
            "form_fields": self.form_definition.fields,
            "form_errors": errors,
            "form_data": form_data,
        }
        extra = self.service.build_context(resource=resource)

        if self.form_definition.context_builder:
            extra = {
                **extra,
                **dict(self.form_definition.context_builder(resource=resource)),
            }
        base_context.update(extra)
        return base_context

    def _resolve_success_redirect(self, instance: Any) -> str:
        endpoint = self.form_definition.redirect_endpoint
        if not endpoint:
            return request.referrer or url_for("main.index")
        return url_for(endpoint, **self._success_redirect_kwargs(instance))

    def _success_redirect_kwargs(self, instance: Any) -> dict[str, Any]:
        return {}

    def get_success_message(self, instance: Any) -> str:
        return self.form_definition.success_message
