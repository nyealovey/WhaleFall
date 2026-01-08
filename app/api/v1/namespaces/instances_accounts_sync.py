"""Instances namespace: accounts sync actions.

将原 `/api/v1/accounts/actions/sync(-all)` 迁移到 instances 资源归属下:

- POST /api/v1/instances/actions/sync-accounts
- POST /api/v1/instances/{instance_id}/actions/sync-accounts
"""

from __future__ import annotations

from typing import ClassVar

from flask_login import current_user
from flask_restx import fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.namespaces.instances import ns
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.services.accounts_sync import accounts_sync_service
from app.services.accounts_sync.accounts_sync_actions_service import AccountsSyncActionsService
from app.tasks.accounts_sync_tasks import sync_accounts as sync_accounts_task
from app.utils.decorators import require_csrf
from app.utils.structlog_config import log_info

ErrorEnvelope = get_error_envelope_model(ns)

InstancesAccountsSyncResultData = ns.model(
    "InstancesAccountsSyncResultData",
    {
        "result": fields.Raw(required=True, description="同步结果", example={}),
    },
)

InstancesAccountsSyncResultSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstancesAccountsSyncResultSuccessEnvelope",
    InstancesAccountsSyncResultData,
)

InstancesAccountsSyncAllData = ns.model(
    "InstancesAccountsSyncAllData",
    {
        "session_id": fields.String(
            required=True,
            description="同步会话 ID",
            example="a1b2c3d4-e5f6-7890-1234-567890abcdef",
        ),
    },
)

InstancesAccountsSyncAllSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstancesAccountsSyncAllSuccessEnvelope",
    InstancesAccountsSyncAllData,
)


@ns.route("/actions/sync-accounts")
class InstancesSyncAccountsActionResource(BaseResource):
    """账户全量同步动作资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("update")]

    @ns.response(200, "OK", InstancesAccountsSyncAllSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """触发全量账户同步."""
        created_by = getattr(current_user, "id", None)

        def _execute():
            log_info("触发批量账户同步", module="accounts_sync", user_id=current_user.id)
            launch_result = AccountsSyncActionsService(
                sync_service=accounts_sync_service,
                sync_task=sync_accounts_task,
            ).trigger_background_full_sync(created_by=created_by)
            log_info(
                "批量账户同步任务已在后台启动",
                module="accounts_sync",
                user_id=current_user.id,
                active_instance_count=launch_result.active_instance_count,
                thread_name=launch_result.thread_name,
                session_id=launch_result.session_id,
            )
            return self.success(
                data={"session_id": launch_result.session_id},
                message="批量账户同步任务已在后台启动,请稍后在会话中心查看进度.",
            )

        return self.safe_call(
            _execute,
            module="accounts_sync",
            action="sync_all_accounts",
            public_error="批量同步任务触发失败,请稍后重试",
            context={"scope": "all_instances"},
        )


@ns.route("/<int:instance_id>/actions/sync-accounts")
class InstancesSyncInstanceAccountsActionResource(BaseResource):
    """账户单实例同步动作资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("update")]

    @ns.response(200, "OK", InstancesAccountsSyncResultSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self, instance_id: int):
        """触发单实例账户同步."""

        def _execute():
            result = AccountsSyncActionsService(
                sync_service=accounts_sync_service,
                sync_task=sync_accounts_task,
            ).sync_instance_accounts(
                instance_id=instance_id,
                actor_id=getattr(current_user, "id", None),
            )
            if result.success:
                return self.success(data={"result": result.result}, message=result.message)
            return self.error_message(
                result.message,
                extra={"result": result.result, "instance_id": instance_id},
            )

        return self.safe_call(
            _execute,
            module="accounts_sync",
            action="sync_instance_accounts",
            public_error="账户同步失败,请重试",
            context={"instance_id": instance_id},
        )
