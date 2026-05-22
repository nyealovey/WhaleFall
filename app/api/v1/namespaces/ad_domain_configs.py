"""AD 域配置 namespace."""

from __future__ import annotations

from typing import ClassVar

from flask_login import current_user
from flask_restx import Namespace, fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource, get_raw_payload
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.schemas.ad_domain_config import AdDomainConfigPayload, AdDomainEnabledPayload
from app.schemas.validation import validate_or_raise
from app.services.ad_sync.ad_domain_config_service import AdDomainConfigService
from app.tasks.ad_sync_tasks import sync_ad_accounts
from app.utils.decorators import require_csrf

ns = Namespace("ad-domain-configs", description="AD 域账户同步配置")

ErrorEnvelope = get_error_envelope_model(ns)

AdDomainConfigData = ns.model(
    "AdDomainConfigData",
    {
        "configs": fields.List(fields.Raw, required=True),
    },
)

AdDomainConfigSuccessEnvelope = make_success_envelope_model(
    ns,
    "AdDomainConfigSuccessEnvelope",
    AdDomainConfigData,
)

AdDomainConfigPayloadModel = ns.model(
    "AdDomainConfigPayloadModel",
    {
        "name": fields.String(required=True),
        "netbios_name": fields.String(required=True),
        "domain_controllers": fields.List(fields.String, required=True),
        "ldap_port": fields.Integer(required=False),
        "use_ssl": fields.Boolean(required=False),
        "verify_ssl": fields.Boolean(required=False),
        "base_dn": fields.String(required=True),
        "credential_id": fields.Integer(required=True),
        "is_enabled": fields.Boolean(required=False),
        "description": fields.String(required=False),
    },
)

AdDomainEnabledPayloadModel = ns.model(
    "AdDomainEnabledPayloadModel",
    {
        "is_enabled": fields.Boolean(required=True),
    },
)

AdDomainSyncData = ns.model(
    "AdDomainSyncData",
    {
        "triggered": fields.Boolean(required=True),
    },
)

AdDomainSyncSuccessEnvelope = make_success_envelope_model(ns, "AdDomainSyncSuccessEnvelope", AdDomainSyncData)


def _configs_payload(service: AdDomainConfigService) -> dict[str, object]:
    return {"configs": service.list_configs()}


@ns.route("")
class AdDomainConfigsResource(BaseResource):
    """AD 域配置列表与创建."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", AdDomainConfigSuccessEnvelope)
    def get(self):
        """列出 AD 域配置."""

        def _execute():
            service = AdDomainConfigService()
            return self.success(data=_configs_payload(service), message="获取 AD 域配置成功")

        return self.safe_call(
            _execute,
            module="ad_domain_configs",
            action="list_configs",
            public_error="获取 AD 域配置失败",
        )

    @ns.response(200, "OK", AdDomainConfigSuccessEnvelope)
    @ns.expect(AdDomainConfigPayloadModel, validate=False)
    @require_csrf
    def post(self):
        """新增 AD 域配置."""

        def _execute():
            payload = validate_or_raise(AdDomainConfigPayload, get_raw_payload() or {})
            service = AdDomainConfigService()
            service.create(payload)
            return self.success(data=_configs_payload(service), message="AD 域配置创建成功")

        return self.safe_call(
            _execute,
            module="ad_domain_configs",
            action="create_config",
            public_error="创建 AD 域配置失败",
        )


@ns.route("/<int:config_id>")
class AdDomainConfigResource(BaseResource):
    """单个 AD 域配置."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", AdDomainConfigSuccessEnvelope)
    @ns.expect(AdDomainConfigPayloadModel, validate=False)
    @require_csrf
    def put(self, config_id: int):
        """更新 AD 域配置."""

        def _execute():
            payload = validate_or_raise(AdDomainConfigPayload, get_raw_payload() or {})
            service = AdDomainConfigService()
            service.update(config_id, payload)
            return self.success(data=_configs_payload(service), message="AD 域配置更新成功")

        return self.safe_call(
            _execute,
            module="ad_domain_configs",
            action="update_config",
            public_error="更新 AD 域配置失败",
        )

    @ns.response(200, "OK", AdDomainConfigSuccessEnvelope)
    @require_csrf
    def delete(self, config_id: int):
        """删除 AD 域配置."""

        def _execute():
            service = AdDomainConfigService()
            service.delete(config_id)
            return self.success(data=_configs_payload(service), message="AD 域配置删除成功")

        return self.safe_call(
            _execute,
            module="ad_domain_configs",
            action="delete_config",
            public_error="删除 AD 域配置失败",
        )


@ns.route("/<int:config_id>/actions/set-enabled")
class AdDomainConfigEnabledResource(BaseResource):
    """启停 AD 域配置."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", AdDomainConfigSuccessEnvelope)
    @ns.expect(AdDomainEnabledPayloadModel, validate=False)
    @require_csrf
    def post(self, config_id: int):
        """启用或停用 AD 域配置."""

        def _execute():
            payload = validate_or_raise(AdDomainEnabledPayload, get_raw_payload() or {})
            service = AdDomainConfigService()
            service.set_enabled(config_id, is_enabled=payload.is_enabled)
            return self.success(data=_configs_payload(service), message="AD 域配置状态已更新")

        return self.safe_call(
            _execute,
            module="ad_domain_configs",
            action="set_enabled",
            public_error="更新 AD 域配置状态失败",
        )


@ns.route("/<int:config_id>/actions/test-connection")
class AdDomainConfigTestConnectionResource(BaseResource):
    """测试 AD 连接."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", make_success_envelope_model(ns, "AdDomainConfigTestSuccessEnvelope"))
    @require_csrf
    def post(self, config_id: int):
        """测试 AD 域连接."""

        def _execute():
            data = AdDomainConfigService().test_connection(config_id)
            return self.success(data=data, message="AD 域连接测试成功")

        return self.safe_call(
            _execute,
            module="ad_domain_configs",
            action="test_connection",
            public_error="AD 域连接测试失败",
        )


@ns.route("/actions/sync")
class AdDomainSyncResource(BaseResource):
    """手动触发 AD 同步."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", AdDomainSyncSuccessEnvelope)
    @require_csrf
    def post(self):
        """手动触发 AD 域账户同步."""

        def _execute():
            created_by = int(getattr(current_user, "id", 0) or 0) or None
            sync_ad_accounts(manual_run=True, created_by=created_by)
            return self.success(data={"triggered": True}, message="AD 域账户同步已触发")

        return self.safe_call(
            _execute,
            module="ad_domain_configs",
            action="sync_ad_accounts",
            public_error="触发 AD 域账户同步失败",
        )
