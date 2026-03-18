"""Instances namespace: audit info read/sync."""

from __future__ import annotations

from typing import ClassVar

from flask_login import current_user
from flask_restx import fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.namespaces.instances import ns
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.core.exceptions import NotFoundError
from app.services.config_sync.instance_audit_read_service import InstanceAuditInfoReadService
from app.services.config_sync.instance_audit_sync_actions_service import InstanceAuditSyncActionsService
from app.utils.decorators import require_csrf

ErrorEnvelope = get_error_envelope_model(ns)

InstanceAuditInfoData = ns.model(
    "InstanceAuditInfoData",
    {
        "instance_id": fields.Integer(required=True),
        "instance_name": fields.String(required=True),
        "db_type": fields.String(required=True),
        "config_key": fields.String(required=True, example="audit_info"),
        "supported": fields.Boolean(required=True),
        "available": fields.Boolean(required=True),
        "last_sync_time": fields.String(required=False),
        "snapshot": fields.Raw(required=False),
        "facts": fields.Raw(required=False),
        "message": fields.String(required=False),
    },
)

InstanceAuditInfoSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceAuditInfoSuccessEnvelope",
    InstanceAuditInfoData,
)

InstanceAuditSyncData = ns.model(
    "InstanceAuditSyncData",
    {
        "session_id": fields.String(required=True),
        "summary": fields.Raw(required=False),
        "config_key": fields.String(required=False),
    },
)

InstanceAuditSyncSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceAuditSyncSuccessEnvelope",
    InstanceAuditSyncData,
)


@ns.route("/<int:instance_id>/audit-info")
class InstanceAuditInfoResource(BaseResource):
    """实例审计信息读取资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", InstanceAuditInfoSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, instance_id: int):
        def _execute():
            payload = InstanceAuditInfoReadService().get_audit_info(instance_id)
            return self.success(data=payload, message="获取审计信息成功")

        return self.safe_call(
            _execute,
            module="instances_audit",
            action="get_instance_audit_info",
            public_error="获取审计信息失败",
            expected_exceptions=(NotFoundError,),
            context={"instance_id": instance_id},
        )


@ns.route("/<int:instance_id>/actions/sync-audit-info")
class InstanceAuditSyncActionResource(BaseResource):
    """实例审计信息同步资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("update")]

    @ns.response(200, "OK", InstanceAuditSyncSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self, instance_id: int):
        def _execute():
            result = InstanceAuditSyncActionsService().sync_instance_audit_info(
                instance_id=instance_id,
                actor_id=getattr(current_user, "id", None),
            )
            if result.success:
                return self.success(data=result.result, message=result.message, status=result.http_status)
            return self.error_message(
                result.message,
                status=result.http_status,
                message_key=result.message_key,
                extra=result.extra,
            )

        return self.safe_call(
            _execute,
            module="instances_audit",
            action="sync_instance_audit_info",
            public_error="同步审计信息失败",
            expected_exceptions=(NotFoundError,),
            context={"instance_id": instance_id},
        )
