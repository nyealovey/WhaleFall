"""
通用资源表单视图
------------------
集成 GET/POST 逻辑，依赖 ResourceFormDefinition 与 BaseResourceService。
"""

from __future__ import annotations

from typing import Any
from collections.abc import Mapping

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
from app.services.form_service.resource_service import BaseResourceService


class ResourceFormView(MethodView):
    """通用 GET/POST 视图，子类只需设置 form_definition。

    提供统一的资源表单处理逻辑，包括 GET 显示表单和 POST 提交表单。
    子类只需配置 form_definition 即可使用。

    Attributes:
        form_definition: 资源表单定义配置。
        service: 资源服务实例。

    """

    form_definition: ResourceFormDefinition

    def __init__(self):
        """初始化视图。

        Raises:
            RuntimeError: 当子类未配置 form_definition 时抛出。

        """
        if not getattr(self, "form_definition", None):
            raise RuntimeError(f"{self.__class__.__name__} 未配置 form_definition")
        self.service: BaseResourceService = self.form_definition.service_class()

    # ------------------------------------------------------------------ #
    # HTTP Methods
    # ------------------------------------------------------------------ #
    def get(self, resource_id: int | None = None, **kwargs) -> str:
        """GET 请求处理，显示表单。

        Args:
            resource_id: 资源 ID，如果为 None 则为创建模式。
            **kwargs: 额外的关键字参数。

        Returns:
            渲染的 HTML 字符串。

        """
        resource = self._load_resource(self._resolve_resource_id(resource_id, kwargs))
        context = self._build_context(resource, form_data=None)
        return render_template(self.form_definition.template, **context)

    def post(self, resource_id: int | None = None, **kwargs) -> str | Response:
        """POST 请求处理，提交表单。

        Args:
            resource_id: 资源 ID，如果为 None 则为创建模式。
            **kwargs: 额外的关键字参数。

        Returns:
            成功时返回重定向响应，失败时返回渲染的 HTML 字符串。

        """
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
        """加载资源对象。

        Args:
            resource_id: 资源 ID，如果为 None 则返回 None。

        Returns:
            资源对象或 None。

        """
        if resource_id is None:
            return None
        return self.service.load(resource_id)

    def _resolve_resource_id(self, resource_id: int | None, kwargs: dict[str, Any]) -> int | None:
        """解析资源 ID。

        从参数中提取资源 ID，支持多种命名方式。

        Args:
            resource_id: 直接传入的资源 ID。
            kwargs: 关键字参数字典。

        Returns:
            解析出的资源 ID 或 None。

        """
        if resource_id is not None:
            return resource_id
        for key in ("instance_id", "credential_id", "tag_id", "classification_id", "rule_id", "user_id"):
            if kwargs.get(key) is not None:
                return kwargs[key]
        return None

    def _extract_payload(self, req) -> Mapping[str, Any]:
        """提取请求负载数据。

        Args:
            req: Flask 请求对象。

        Returns:
            请求数据字典。

        """
        if req.is_json:
            return req.get_json(silent=True) or {}
        return req.form

    def _build_context(
        self,
        resource: Any | None,
        form_data: Mapping[str, Any] | None,
        errors: str | None = None,
    ) -> dict[str, Any]:
        """构建模板上下文。

        Args:
            resource: 资源对象。
            form_data: 表单数据。
            errors: 错误消息。

        Returns:
            模板上下文字典。

        """
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
        """解析成功后的重定向地址。

        Args:
            instance: 资源实例对象。

        Returns:
            重定向的 URL 字符串。

        """
        endpoint = self.form_definition.redirect_endpoint
        if not endpoint:
            return request.referrer or url_for("main.index")
        return url_for(endpoint, **self._success_redirect_kwargs(instance))

    def _success_redirect_kwargs(self, instance: Any) -> dict[str, Any]:
        """获取重定向的额外参数。

        Args:
            instance: 资源实例对象。

        Returns:
            参数字典。

        """
        return {}

    def get_success_message(self, instance: Any) -> str:
        """获取成功消息。

        Args:
            instance: 资源实例对象。

        Returns:
            成功消息字符串。

        """
        return self.form_definition.success_message
