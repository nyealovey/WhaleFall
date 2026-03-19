"""JumpServer 数据源 namespace."""

from __future__ import annotations

from typing import ClassVar

from flask_login import current_user
from flask_restx import Namespace, fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource, get_raw_payload
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.schemas.jumpserver import JumpServerSourceBindingPayload
from app.schemas.validation import validate_or_raise
from app.services.jumpserver.source_service import JumpServerSourceService
from app.services.jumpserver.sync_actions_service import JumpServerSyncActionsService
from app.utils.decorators import require_csrf

ns = Namespace("jumpserver", description="JumpServer 数据源")

ErrorEnvelope = get_error_envelope_model(ns)

JumpServerSourceData = ns.model(
    "JumpServerSourceData",
    {
        "binding": fields.Raw(required=False),
        "api_credentials": fields.List(fields.Raw, required=True),
        "provider_ready": fields.Boolean(required=True),
    },
)

JumpServerSourceSuccessEnvelope = make_success_envelope_model(
    ns,
    "JumpServerSourceSuccessEnvelope",
    JumpServerSourceData,
)

JumpServerSourceBindingPayloadModel = ns.model(
    "JumpServerSourceBindingPayloadModel",
    {
        "credential_id": fields.Integer(required=True, description="API 凭据 ID", example=1),
        "base_url": fields.String(required=True, description="JumpServer URL", example="https://demo.jumpserver.org"),
    },
)

JumpServerSyncResultData = ns.model(
    "JumpServerSyncResultData",
    {
        "run_id": fields.String(required=True, description="任务运行 ID", example="run_123"),
    },
)

JumpServerSyncResultSuccessEnvelope = make_success_envelope_model(
    ns,
    "JumpServerSyncResultSuccessEnvelope",
    JumpServerSyncResultData,
)


@ns.route("/source")
class JumpServerSourceResource(BaseResource):
    """JumpServer 数据源绑定资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", JumpServerSourceSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取 JumpServer 数据源状态."""

        def _execute():
            data = JumpServerSourceService().build_view_payload()
            return self.success(data=data, message="获取 JumpServer 数据源成功")

        return self.safe_call(
            _execute,
            module="jumpserver",
            action="get_source_binding",
            public_error="获取 JumpServer 数据源失败",
        )

    @ns.response(200, "OK", JumpServerSourceSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(JumpServerSourceBindingPayloadModel, validate=False)
    @require_csrf
    def put(self):
        """绑定 JumpServer API 凭据."""

        def _execute():
            payload = validate_or_raise(JumpServerSourceBindingPayload, get_raw_payload() or {})
            service = JumpServerSourceService()
            service.bind_source(credential_id=payload.credential_id, base_url=payload.base_url)
            data = service.build_view_payload()
            return self.success(data=data, message="JumpServer 数据源绑定成功")

        return self.safe_call(
            _execute,
            module="jumpserver",
            action="bind_source",
            public_error="绑定 JumpServer 数据源失败",
        )

    @ns.response(200, "OK", JumpServerSourceSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def delete(self):
        """解绑 JumpServer 数据源."""

        def _execute():
            service = JumpServerSourceService()
            service.unbind_source()
            data = service.build_view_payload()
            return self.success(data=data, message="JumpServer 数据源已解绑")

        return self.safe_call(
            _execute,
            module="jumpserver",
            action="unbind_source",
            public_error="解绑 JumpServer 数据源失败",
        )


@ns.route("/actions/sync")
class JumpServerSyncActionResource(BaseResource):
    """JumpServer 资产同步动作资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", JumpServerSyncResultSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """触发 JumpServer 资产同步."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            service = JumpServerSyncActionsService()
            prepared = service.prepare_background_sync(created_by=operator_id)
            service.launch_background_sync(created_by=operator_id, prepared=prepared)
            return self.success(
                data={"run_id": prepared.run_id},
                message="JumpServer 资源同步任务已在后台启动",
            )

        return self.safe_call(
            _execute,
            module="jumpserver",
            action="sync_assets",
            public_error="触发 JumpServer 资源同步失败",
        )
