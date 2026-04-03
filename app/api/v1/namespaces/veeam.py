"""Veeam 数据源 namespace."""

from __future__ import annotations

from typing import ClassVar

from flask_login import current_user
from flask_restx import Namespace, fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource, get_raw_payload
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.schemas.validation import validate_or_raise
from app.schemas.veeam import VeeamSourceBindingPayload
from app.services.veeam.source_service import VeeamSourceService
from app.services.veeam.sync_actions_service import VeeamSyncActionsService
from app.services.veeam.instance_backup_read_service import InstanceBackupInfoReadService
from app.repositories.instances_repository import InstancesRepository
from app.repositories.veeam_repository import VeeamRepository
from app.services.veeam.provider import HttpVeeamProvider
from app.core.exceptions import NotFoundError, ValidationError
from app.utils.decorators import require_csrf

ns = Namespace("veeam", description="Veeam 数据源")

ErrorEnvelope = get_error_envelope_model(ns)

VeeamSourceData = ns.model(
    "VeeamSourceData",
    {
        "binding": fields.Raw(required=False),
        "veeam_credentials": fields.List(fields.Raw, required=True),
        "provider_ready": fields.Boolean(required=True),
        "default_port": fields.Integer(required=True),
        "default_api_version": fields.String(required=True),
        "default_verify_ssl": fields.Boolean(required=True),
        "default_match_domains": fields.List(fields.String, required=True),
    },
)

VeeamSourceSuccessEnvelope = make_success_envelope_model(
    ns,
    "VeeamSourceSuccessEnvelope",
    VeeamSourceData,
)

VeeamSourceBindingPayloadModel = ns.model(
    "VeeamSourceBindingPayloadModel",
    {
        "credential_id": fields.Integer(required=True, description="Veeam 凭据 ID", example=1),
        "server_host": fields.String(required=True, description="Veeam 服务器 IP/主机名", example="10.0.0.10"),
        "server_port": fields.Integer(required=True, description="Veeam 服务器端口", example=9419),
        "api_version": fields.String(required=True, description="Veeam API 版本", example="v1.2-rev0"),
        "verify_ssl": fields.Boolean(required=False, description="是否校验 Veeam HTTPS 证书", example=False),
        "match_domains": fields.List(
            fields.String,
            required=False,
            description="候选域名列表",
            example=["domain.com", "corp.local"],
        ),
    },
)

VeeamSyncResultData = ns.model(
    "VeeamSyncResultData",
    {
        "run_id": fields.String(required=True, description="任务运行 ID", example="run_123"),
    },
)

VeeamSyncResultSuccessEnvelope = make_success_envelope_model(
    ns,
    "VeeamSyncResultSuccessEnvelope",
    VeeamSyncResultData,
)


@ns.route("/source")
class VeeamSourceResource(BaseResource):
    """Veeam 数据源绑定资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", VeeamSourceSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取 Veeam 数据源状态."""

        def _execute():
            data = VeeamSourceService().build_view_payload()
            return self.success(data=data, message="获取 Veeam 数据源成功")

        return self.safe_call(
            _execute,
            module="veeam",
            action="get_source_binding",
            public_error="获取 Veeam 数据源失败",
        )

    @ns.response(200, "OK", VeeamSourceSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(VeeamSourceBindingPayloadModel, validate=False)
    @require_csrf
    def put(self):
        """绑定 Veeam 凭据."""

        def _execute():
            payload = validate_or_raise(VeeamSourceBindingPayload, get_raw_payload() or {})
            service = VeeamSourceService()
            service.bind_source(
                credential_id=payload.credential_id,
                server_host=payload.server_host,
                server_port=payload.server_port,
                api_version=payload.api_version,
                verify_ssl=payload.verify_ssl,
                match_domains=payload.match_domains,
            )
            data = service.build_view_payload()
            return self.success(data=data, message="Veeam 数据源绑定成功")

        return self.safe_call(
            _execute,
            module="veeam",
            action="bind_source",
            public_error="绑定 Veeam 数据源失败",
        )

    @ns.response(200, "OK", VeeamSourceSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def delete(self):
        """解绑 Veeam 数据源."""

        def _execute():
            service = VeeamSourceService()
            service.unbind_source()
            data = service.build_view_payload()
            return self.success(data=data, message="Veeam 数据源已解绑")

        return self.safe_call(
            _execute,
            module="veeam",
            action="unbind_source",
            public_error="解绑 Veeam 数据源失败",
        )


@ns.route("/actions/sync")
class VeeamSyncActionResource(BaseResource):
    """Veeam 备份同步动作资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", VeeamSyncResultSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """触发 Veeam 备份同步."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            service = VeeamSyncActionsService()
            prepared = service.prepare_background_sync(created_by=operator_id)
            service.launch_background_sync(created_by=operator_id, prepared=prepared)
            return self.success(
                data={"run_id": prepared.run_id},
                message="Veeam 备份同步任务已在后台启动",
            )

        return self.safe_call(
            _execute,
            module="veeam",
            action="sync_backups",
            public_error="触发 Veeam 备份同步失败",
        )


@ns.route("/actions/sync-instance/<int:instance_id>")
class VeeamSyncInstanceActionResource(BaseResource):
    """单实例 Veeam 备份同步动作资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", VeeamSyncResultSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def post(self, instance_id: int):
        """为指定实例触发 Veeam 备份同步."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            instance = InstancesRepository().get_instance(instance_id)
            if instance is None or instance.deleted_at is not None:
                raise NotFoundError("实例不存在")

            if not self._provider.is_configured():
                raise ValidationError("Veeam Provider 尚未接入真实 API")

            binding = VeeamSourceService().get_binding_or_error()
            credential = getattr(binding, "credential", None)
            if credential is None:
                raise ValidationError("Veeam 数据源未绑定有效凭据")

            session = self._provider.create_session(
                server_host=str(binding.server_host or ""),
                server_port=int(binding.server_port),
                username=str(credential.username or ""),
                password=str(credential.get_plain_password() or ""),
                api_version=str(binding.api_version),
                verify_ssl=bool(binding.verify_ssl),
            )

            instance_host = getattr(instance, "host", None)
            matched = self._veeam_repository.find_best_backup_for_instance_name(instance.name, instance_host)

            return self.success(
                data={"instance_id": instance_id, "instance_name": instance.name, "backup_info": matched},
                message=f"实例 {instance.name} 备份同步查询成功",
            )

        return self.safe_call(
            _execute,
            module="veeam",
            action="sync_instance_backup",
            public_error="查询实例备份信息失败",
        )

    @ns.response(200, "OK", VeeamSyncResultSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, instance_id: int):
        """获取指定实例的 Veeam 备份信息."""

        def _execute():
            instance = InstancesRepository().get_instance(instance_id)
            if instance is None or instance.deleted_at is not None:
                raise NotFoundError("实例不存在")

            if not VeeamRepository._has_machine_backup_snapshot_table():
                return self.success(
                    data={"instance_id": instance_id, "instance_name": instance.name, "backup_info": None},
                    message="Veeam 备份快照表不存在",
                )

            instance_host = getattr(instance, "host", None)
            matched = VeeamRepository.find_best_backup_for_instance_name(instance.name, instance_host)

            return self.success(
                data={"instance_id": instance_id, "instance_name": instance.name, "backup_info": matched},
                message=f"获取实例 {instance.name} 备份信息成功",
            )

        return self.safe_call(
            _execute,
            module="veeam",
            action="get_instance_backup",
            public_error="获取实例备份信息失败",
        )
