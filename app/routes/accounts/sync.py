
"""Accounts 域：账户同步 API 路由。"""

import threading

from flask import Blueprint, Response, flash, redirect, request, url_for
from flask_login import current_user, login_required

from app import db
from app.constants.sync_constants import SyncOperationType, SyncCategory
from app.constants import SyncStatus, TaskStatus, FlashCategory
from app.models.instance import Instance
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.errors import NotFoundError, SystemError, ValidationError as AppValidationError
from app.services.accounts_sync import accounts_sync_service
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import require_csrf, update_required, view_required
from app.utils.response_utils import jsonify_unified_success, jsonify_unified_error_message
from app.utils.structlog_config import log_error, log_info, log_warning

# 创建蓝图
accounts_sync_bp = Blueprint("accounts_sync", __name__)


def _get_instance(instance_id: int) -> Instance:
    """获取实例或抛出错误。

    Args:
        instance_id: 实例 ID。

    Returns:
        实例对象。

    Raises:
        NotFoundError: 当实例不存在时抛出。
    """
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance is None:
        raise NotFoundError("实例不存在")
    return instance


def _normalize_sync_result(result: dict | None, *, context: str) -> tuple[bool, dict]:
    """规范化同步结果。

    将同步服务返回的结果转换为统一格式。

    Args:
        result: 同步结果字典，可能为 None。
        context: 上下文描述，用于生成默认消息。

    Returns:
        (是否成功, 规范化后的结果字典)。
    """
    if not result:
        return False, {"status": "failed", "message": f"{context}返回为空"}

    normalized = dict(result)
    is_success = bool(normalized.pop("success", True))
    message = normalized.get("message") or normalized.get("error")
    if not message:
        message = f"{context}{'成功' if is_success else '失败'}"

    normalized["status"] = "completed" if is_success else "failed"
    normalized["message"] = message
    normalized["success"] = is_success
    return is_success, normalized


@accounts_sync_bp.route("/api/sync-all", methods=["POST"])
@login_required
@update_required
@require_csrf
def sync_all_accounts() -> str | Response | tuple[Response, int]:
    """触发后台批量同步所有实例的账户信息。

    在后台线程中启动批量同步任务，不阻塞请求。

    Returns:
        JSON 响应，包含任务 ID。

    Raises:
        AppValidationError: 当没有活跃实例时抛出。
        SystemError: 当任务触发失败时抛出。
    """
    try:
        log_info("触发批量账户同步", module="accounts_sync", user_id=current_user.id)

        active_instance_count = Instance.query.filter_by(is_active=True).count()
        if active_instance_count == 0:
            log_warning(
                "没有找到活跃的数据库实例",
                module="accounts_sync",
                user_id=current_user.id,
            )
            raise AppValidationError("没有找到活跃的数据库实例")

        created_by = getattr(current_user, "id", None)

        def _run_sync_task(captured_created_by: int | None) -> None:
            from app.tasks.accounts_sync_tasks import sync_accounts

            try:
                sync_accounts(manual_run=True, created_by=captured_created_by)
            except Exception as exc:  # pragma: no cover - 后台线程日志
                log_error(
                    "后台批量账户同步失败",
                    module="accounts_sync",
                    error=str(exc),
                )

        thread = threading.Thread(
            target=_run_sync_task,
            args=(created_by,),
            name="sync_accounts_manual_batch",
            daemon=True,
        )
        thread.start()

        log_info(
            "批量账户同步任务已在后台启动",
            module="accounts_sync",
            user_id=current_user.id,
            active_instance_count=active_instance_count,
            thread_name=thread.name,
        )

        return jsonify_unified_success(
            message="批量账户同步任务已在后台启动，请稍后在会话中心查看进度。",
            data={"manual_job_id": thread.name},
        )

    except AppValidationError:
        raise
    except Exception as exc:  # noqa: BLE001
        log_error(
            "触发批量账户同步失败",
            module="accounts_sync",
            user_id=current_user.id if current_user else None,
            error=str(exc),
        )
        raise SystemError("批量同步任务触发失败，请稍后重试") from exc


@accounts_sync_bp.route("/api/instances/<int:instance_id>/sync", methods=["POST"])
@login_required
@update_required
@require_csrf
def sync_instance_accounts(instance_id: int) -> Response:
    """同步指定实例的账户信息，统一返回 JSON。

    Args:
        instance_id: 实例 ID。

    Returns:
        JSON 响应，包含同步结果和统计信息。

    Raises:
        NotFoundError: 当实例不存在时抛出。
        SystemError: 当同步失败时抛出。
    """
    instance = Instance.query.get_or_404(instance_id)
    try:
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
        is_success, normalized = _normalize_sync_result(
            raw_result,
            context=f"实例 {instance.name} 账户同步",
        )

        if is_success:
            instance.sync_count = (instance.sync_count or 0) + 1
            db.session.commit()

            log_info(
                "实例账户同步成功",
                module="accounts_sync",
                user_id=current_user.id,
                instance_id=instance.id,
                instance_name=instance.name,
                synced_count=normalized.get("synced_count", 0),
            )

            return jsonify_unified_success(
                data={"result": normalized},
                message=normalized["message"],
            )

        failure_message = normalized.get("message", "账户同步失败")
        log_error(
            "实例账户同步失败",
            module="accounts_sync",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
            error=failure_message,
        )

        return jsonify_unified_error_message(
            failure_message,
            extra={"result": normalized, "instance_id": instance.id},
        )

    except Exception as exc:
        log_error(f"同步实例账户失败: {exc}", module="accounts_sync", instance_id=instance.id)
        log_error(
            "实例账户同步异常",
            module="accounts_sync",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
            error=str(exc),
        )
        raise SystemError("账户同步失败，请重试") from exc
