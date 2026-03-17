"""邮件告警配置 namespace."""

from __future__ import annotations

from typing import ClassVar

from flask import request
from flask_restx import Namespace, fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.schemas.email_alerts import EmailAlertSettingsPayload
from app.schemas.validation import validate_or_raise
from app.services.alerts.email_alert_settings_service import EmailAlertSettingsService
from app.utils.decorators import require_csrf

ns = Namespace("alerts", description="邮件告警配置")

ErrorEnvelope = get_error_envelope_model(ns)
AlertSettingsData = ns.model(
    "AlertSettingsData",
    {
        "smtp_ready": fields.Boolean(required=True),
        "from_address": fields.String(required=False),
        "from_name": fields.String(required=False),
        "settings": fields.Raw(required=True),
    },
)
AlertSettingsSuccessEnvelope = make_success_envelope_model(ns, "AlertSettingsSuccessEnvelope", AlertSettingsData)

AlertSettingsPayloadModel = ns.model(
    "AlertSettingsPayloadModel",
    {
        "global_enabled": fields.Boolean(required=True),
        "recipients": fields.List(fields.String, required=True),
        "database_capacity_enabled": fields.Boolean(required=True),
        "database_capacity_percent_threshold": fields.Integer(required=True),
        "database_capacity_absolute_gb_threshold": fields.Integer(required=True),
        "account_sync_failure_enabled": fields.Boolean(required=True),
        "database_sync_failure_enabled": fields.Boolean(required=True),
        "privileged_account_enabled": fields.Boolean(required=True),
    },
)


@ns.route("/email-settings")
class AlertEmailSettingsResource(BaseResource):
    """邮件告警配置资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", AlertSettingsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取邮件告警配置."""

        def _execute():
            data = EmailAlertSettingsService().build_view_payload()
            return self.success(data=data, message="获取邮件告警配置成功")

        return self.safe_call(
            _execute,
            module="alerts",
            action="get_email_settings",
            public_error="获取邮件告警配置失败",
        )

    @ns.response(200, "OK", AlertSettingsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(AlertSettingsPayloadModel, validate=False)
    @require_csrf
    def put(self):
        """更新邮件告警配置."""

        def _execute():
            payload = request.get_json(silent=True)
            parsed = validate_or_raise(EmailAlertSettingsPayload, payload or {})
            service = EmailAlertSettingsService()
            service.update_settings(parsed.model_dump())
            data = service.build_view_payload()
            return self.success(data=data, message="更新邮件告警配置成功")

        return self.safe_call(
            _execute,
            module="alerts",
            action="update_email_settings",
            public_error="更新邮件告警配置失败",
        )
