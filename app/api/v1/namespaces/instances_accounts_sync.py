"""Instances namespace: accounts sync actions.

将原 `/api/v1/accounts/actions/sync(-all)` 迁移到 instances 资源归属下:

- POST /api/v1/instances/actions/sync-accounts
- POST /api/v1/instances/{instance_id}/actions/sync-accounts
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from typing import Any, ClassVar, cast
from uuid import uuid4

from flask_login import current_user
from flask_restx import fields
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.namespaces.instances import ns
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.constants.sync_constants import SyncOperationType
from app.errors import NotFoundError, SystemError, ValidationError
from app.models.instance import Instance
from app.services.accounts_sync import accounts_sync_service
from app.tasks.accounts_sync_tasks import sync_accounts as sync_accounts_task
from app.utils.decorators import require_csrf
from app.utils.route_safety import log_with_context
from app.utils.structlog_config import log_info, log_warning

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

BACKGROUND_SYNC_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ValidationError,
    SystemError,
    SQLAlchemyError,
    RuntimeError,
)


def _ensure_active_instances() -> int:
    active_count = Instance.query.filter_by(is_active=True).count()
    if active_count == 0:
        msg = "没有找到活跃的数据库实例"
        log_warning(msg, module="accounts_sync", user_id=current_user.id)
        raise ValidationError(msg)
    return int(active_count)


def _launch_background_sync(created_by: int | None, session_id: str) -> threading.Thread:
    def _run_sync_task(captured_created_by: int | None, captured_session_id: str) -> None:
        try:
            sync_accounts_task(manual_run=True, created_by=captured_created_by, session_id=captured_session_id)
        except BACKGROUND_SYNC_EXCEPTIONS as exc:  # pragma: no cover
            log_with_context(
                "error",
                "后台批量账户同步失败",
                module="accounts_sync",
                action="sync_all_accounts_background",
                context={"created_by": captured_created_by},
                extra={
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )

    thread = threading.Thread(
        target=_run_sync_task,
        args=(created_by, session_id),
        name="sync_accounts_manual_batch",
        daemon=True,
    )
    thread.start()
    return thread


def _get_instance(instance_id: int) -> Instance:
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance is None:
        raise NotFoundError("实例不存在")
    return instance


def _normalize_sync_result(result: Mapping[str, Any] | None, *, context: str) -> tuple[bool, dict[str, Any]]:
    if not result:
        return False, {"status": "failed", "message": f"{context}返回为空"}

    normalized = dict(result)
    is_success = bool(normalized.pop("success", True))
    message = normalized.get("message")
    if not message:
        message = f"{context}{'成功' if is_success else '失败'}"

    normalized["status"] = "completed" if is_success else "failed"
    normalized["message"] = message
    normalized["success"] = is_success
    return is_success, normalized


def _log_sync_failure(instance: Instance, *, message: str) -> None:
    log_with_context(
        "error",
        "实例账户同步失败",
        module="accounts_sync",
        action="sync_instance_accounts",
        context={
            "user_id": getattr(current_user, "id", None),
            "instance_id": instance.id,
            "instance_name": instance.name,
            "db_type": instance.db_type,
            "host": instance.host,
        },
        extra={"error_message": message},
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
            active_instance_count = _ensure_active_instances()
            session_id = str(uuid4())
            thread = _launch_background_sync(created_by, session_id)
            log_info(
                "批量账户同步任务已在后台启动",
                module="accounts_sync",
                user_id=current_user.id,
                active_instance_count=active_instance_count,
                thread_name=thread.name,
                session_id=session_id,
            )
            return self.success(
                data={"session_id": session_id},
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
            instance = _get_instance(instance_id)
            log_info(
                "开始同步实例账户",
                module="accounts_sync",
                user_id=current_user.id,
                instance_id=instance.id,
                instance_name=instance.name,
                db_type=instance.db_type,
                host=instance.host,
            )

            raw_result = accounts_sync_service.sync_accounts(instance, sync_type=SyncOperationType.MANUAL_SINGLE.value)
            is_success, normalized = _normalize_sync_result(raw_result, context=f"实例 {instance.name} 账户同步")

            if is_success:
                instance.sync_count = (instance.sync_count or 0) + 1
                log_info(
                    "实例账户同步成功",
                    module="accounts_sync",
                    user_id=current_user.id,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    synced_count=normalized.get("synced_count", 0),
                )
                return self.success(data={"result": normalized}, message=cast(str, normalized["message"]))

            failure_message = cast(str, normalized.get("message") or "账户同步失败")
            _log_sync_failure(instance, message=failure_message)
            return self.error_message(
                failure_message,
                extra={"result": normalized, "instance_id": instance.id},
            )

        return self.safe_call(
            _execute,
            module="accounts_sync",
            action="sync_instance_accounts",
            public_error="账户同步失败,请重试",
            context={"instance_id": instance_id},
        )
