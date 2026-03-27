"""Instances namespace: backup info read."""

from __future__ import annotations

from typing import ClassVar

from flask_restx import fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.namespaces.instances import ns
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.core.exceptions import NotFoundError
from app.services.veeam.instance_backup_read_service import InstanceBackupInfoReadService

ErrorEnvelope = get_error_envelope_model(ns)

InstanceBackupRestorePointData = ns.model(
    "InstanceBackupRestorePointData",
    {
        "id": fields.String(required=False),
        "name": fields.String(required=False),
        "type": fields.String(required=False),
        "backup_id": fields.String(required=False),
        "object_id": fields.String(required=False),
        "restore_point_ids": fields.List(fields.String, required=False),
        "data_size_bytes": fields.Integer(required=False),
        "backup_size_bytes": fields.Integer(required=False),
        "compress_ratio": fields.Integer(required=False),
        "creation_time": fields.String(required=False),
    },
)

InstanceBackupMetricsCoverageData = ns.model(
    "InstanceBackupMetricsCoverageData",
    {
        "expected_restore_point_count": fields.Integer(required=True),
        "enriched_restore_point_count": fields.Integer(required=True),
        "missing_restore_point_count": fields.Integer(required=True),
        "partial": fields.Boolean(required=True),
    },
)

InstanceBackupInfoData = ns.model(
    "InstanceBackupInfoData",
    {
        "instance_id": fields.Integer(required=True),
        "instance_name": fields.String(required=True),
        "backup_status": fields.String(required=True),
        "backup_last_time": fields.String(required=False),
        "matched_machine_name": fields.String(required=False),
        "match_candidates": fields.List(fields.String, required=True),
        "backup_id": fields.String(required=False),
        "backup_file_id": fields.String(required=False),
        "job_name": fields.String(required=False),
        "restore_point_name": fields.String(required=False),
        "source_record_id": fields.String(required=False),
        "restore_point_size_bytes": fields.Integer(required=False),
        "backup_chain_size_bytes": fields.Integer(required=False),
        "restore_point_count": fields.Integer(required=False),
        "backup_metrics_coverage": fields.Nested(InstanceBackupMetricsCoverageData, required=False),
        "restore_point_times": fields.List(fields.String, required=False),
        "restore_points": fields.List(fields.Nested(InstanceBackupRestorePointData), required=False),
        "last_sync_time": fields.String(required=False),
        "message": fields.String(required=False),
    },
)

InstanceBackupInfoSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceBackupInfoSuccessEnvelope",
    InstanceBackupInfoData,
)


@ns.route("/<int:instance_id>/backup-info")
class InstanceBackupInfoResource(BaseResource):
    """实例备份信息读取资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", InstanceBackupInfoSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, instance_id: int):
        def _execute():
            payload = InstanceBackupInfoReadService().get_backup_info(instance_id)
            return self.success(data=payload, message="获取备份信息成功")

        return self.safe_call(
            _execute,
            module="instances_backup",
            action="get_instance_backup_info",
            public_error="获取备份信息失败",
            expected_exceptions=(NotFoundError,),
            context={"instance_id": instance_id},
        )
