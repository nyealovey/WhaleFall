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
from app.services.veeam.matching import (
    build_instance_match_candidates,
    build_instance_ip_candidates,
    normalize_machine_name,
    normalize_ip_address,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.infra.route_safety import log_with_context
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
    @require_csrf
    def post(self, instance_id: int):
        """为指定实例触发 Veeam 备份同步."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            instance = InstancesRepository().get_instance(instance_id)
            if instance is None or instance.deleted_at is not None:
                raise NotFoundError("实例不存在")

            provider = HttpVeeamProvider()
            if not provider.is_configured():
                raise ValidationError("Veeam Provider 尚未接入真实 API")

            source_service = VeeamSourceService()
            binding = source_service.get_binding_or_error()
            credential = getattr(binding, "credential", None)
            if credential is None:
                raise ValidationError("Veeam 数据源未绑定有效凭据")

            instance_name = instance.name
            instance_host = getattr(instance, "host", None)
            domains = binding.match_domains if binding and isinstance(binding.match_domains, list) else []

            log_with_context(
                "info",
                "单实例 Veeam 备份同步开始",
                module="veeam",
                action="sync_instance_backup",
                extra={
                    "instance_id": instance_id,
                    "instance_name": instance_name,
                    "instance_host": instance_host,
                    "match_domains": domains,
                },
                include_actor=False,
            )

            session = provider.create_session(
                server_host=str(binding.server_host or ""),
                server_port=int(binding.server_port),
                username=str(credential.username or ""),
                password=str(credential.get_plain_password() or ""),
                api_version=str(binding.api_version),
                verify_ssl=bool(binding.verify_ssl),
            )

            name_candidates = build_instance_match_candidates(instance_name, domains)
            ip_candidates = build_instance_ip_candidates(instance_host)

            log_with_context(
                "debug",
                "单实例 Veeam 候选匹配",
                module="veeam",
                action="sync_instance_backup",
                extra={
                    "instance_id": instance_id,
                    "instance_name": instance_name,
                    "instance_host": instance_host,
                    "name_candidates": name_candidates,
                    "ip_candidates": ip_candidates,
                },
                include_actor=False,
            )

            backup_items = provider.fetch_backup_objects(session=session)

            log_with_context(
                "debug",
                "单实例 Veeam 备份列表",
                module="veeam",
                action="sync_instance_backup",
                extra={
                    "instance_id": instance_id,
                    "backup_items_count": len(backup_items),
                    "backup_items_sample": [
                        provider._pick_string(item, ("name", "machineName", "objectName")) for item in backup_items[:10]
                    ],
                },
                include_actor=False,
            )

            matched_backup = None
            for item in backup_items:
                backup_name = provider._pick_string(item, ("name", "machineName", "objectName"))
                if not backup_name:
                    continue

                normalized_backup_name = normalize_machine_name(backup_name)
                backup_ip = provider._resolve_backup_machine_ip(item)
                normalized_backup_ip = normalize_ip_address(backup_ip) if backup_ip else None
                backup_name_as_ip = normalize_ip_address(backup_name)
                if backup_name_as_ip and not normalized_backup_ip:
                    normalized_backup_ip = backup_name_as_ip

                name_match = normalized_backup_name in name_candidates if normalized_backup_name else False
                ip_match = normalized_backup_ip in ip_candidates if normalized_backup_ip else False

                if name_match or ip_match:
                    matched_backup = item
                    log_with_context(
                        "debug",
                        "单实例 Veeam 备份匹配成功",
                        module="veeam",
                        action="sync_instance_backup",
                        extra={
                            "instance_id": instance_id,
                            "backup_name": backup_name,
                            "normalized_backup_name": normalized_backup_ip,
                            "backup_ip": backup_ip,
                            "normalized_backup_ip": normalized_backup_ip,
                            "name_match": name_match,
                            "ip_match": ip_match,
                        },
                        include_actor=False,
                    )
                    break

            if not matched_backup:
                log_with_context(
                    "warning",
                    "单实例 Veeam 备份未匹配到",
                    module="veeam",
                    action="sync_instance_backup",
                    extra={
                        "instance_id": instance_id,
                        "instance_name": instance_name,
                        "instance_host": instance_host,
                        "name_candidates": name_candidates,
                        "ip_candidates": ip_candidates,
                        "backup_items_count": len(backup_items),
                    },
                    include_actor=False,
                )
                return self.success(
                    data={
                        "instance_id": instance_id,
                        "instance_name": instance_name,
                        "backup_info": None,
                        "matched": False,
                    },
                    message=f"实例 {instance_name} 未匹配到 Veeam 备份",
                )

            matched_backup_id = provider._pick_string(matched_backup, ("id", "backupObjectId"))
            matched_machine_name = provider._pick_string(matched_backup, ("name", "machineName", "objectName"))

            log_with_context(
                "info",
                "单实例 Veeam 备份已匹配",
                module="veeam",
                action="sync_instance_backup",
                extra={
                    "instance_id": instance_id,
                    "instance_name": instance_name,
                    "matched_backup_id": matched_backup_id,
                    "matched_machine_name": matched_machine_name,
                },
                include_actor=False,
            )

            restore_points_url = provider._build_backup_restore_points_url(
                base_url=session.base_url,
                backup_object_id=matched_backup_id,
            )
            log_with_context(
                "debug",
                "单实例 Veeam 恢复点 URL",
                module="veeam",
                action="sync_instance_backup",
                extra={
                    "instance_id": instance_id,
                    "restore_points_url": restore_points_url,
                },
                include_actor=False,
            )

            restore_point_items = provider._collect_paginated_items(
                url=restore_points_url,
                access_token=session.access_token,
                api_version=session.api_version,
                verify_ssl=session.verify_ssl,
            )

            log_with_context(
                "debug",
                "单实例 Veeam 恢复点数据",
                module="veeam",
                action="sync_instance_backup",
                extra={
                    "instance_id": instance_id,
                    "restore_point_items_count": len(restore_point_items),
                    "restore_point_items_sample": restore_point_items[:3],
                },
                include_actor=False,
            )

            records: list = []
            for item in restore_point_items:
                record = provider._normalize_backup_record(
                    item,
                    backup_item=matched_backup,
                    backup_machine_name=matched_machine_name,
                )
                if record:
                    records.append(record)

            log_with_context(
                "debug",
                "单实例 Veeam 标准化记录",
                module="veeam",
                action="sync_instance_backup",
                extra={
                    "instance_id": instance_id,
                    "records_count": len(records),
                    "records_sample": [
                        {"machine_name": r.machine_name, "backup_at": str(r.backup_at)} for r in records[:3]
                    ],
                },
                include_actor=False,
            )

            if records:
                from app.utils.time_utils import time_utils

                synced_at = time_utils.now()
                snapshots_written = VeeamRepository.replace_machine_backup_snapshots(
                    records=records,
                    sync_run_id=f"single_sync_{instance_id}",
                    synced_at=synced_at,
                )

                log_with_context(
                    "info",
                    "单实例 Veeam 备份同步完成",
                    module="veeam",
                    action="sync_instance_backup",
                    extra={
                        "instance_id": instance_id,
                        "instance_name": instance_name,
                        "matched_backup_id": matched_backup_id,
                        "restore_points_count": len(records),
                        "snapshots_written": snapshots_written,
                    },
                    include_actor=False,
                )

                matched = VeeamRepository.find_best_backup_for_instance_name(instance_name, instance_host)
            else:
                matched = None

            return self.success(
                data={
                    "instance_id": instance_id,
                    "instance_name": instance_name,
                    "backup_info": matched,
                    "matched": True,
                },
                message=f"实例 {instance_name} 备份同步成功",
            )

        return self.safe_call(
            _execute,
            module="veeam",
            action="sync_instance_backup",
            public_error="同步实例备份失败",
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
                from app.infra.route_safety import log_with_context

                log_with_context(
                    "info",
                    "获取单实例 Veeam 备份信息",
                    module="veeam",
                    action="get_instance_backup",
                    extra={
                        "instance_id": instance_id,
                        "instance_name": instance.name,
                        "reason": "snapshot_table_not_exists",
                    },
                    include_actor=False,
                )
                return self.success(
                    data={"instance_id": instance_id, "instance_name": instance.name, "backup_info": None},
                    message="Veeam 备份快照表不存在",
                )

            instance_host = getattr(instance, "host", None)
            matched = VeeamRepository.find_best_backup_for_instance_name(instance.name, instance_host)

            from app.infra.route_safety import log_with_context

            log_with_context(
                "info",
                "获取单实例 Veeam 备份信息",
                module="veeam",
                action="get_instance_backup",
                extra={
                    "instance_id": instance_id,
                    "instance_name": instance.name,
                    "instance_host": instance_host,
                    "has_backup_info": matched is not None,
                },
                include_actor=False,
            )

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
