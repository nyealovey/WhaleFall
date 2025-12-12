"""Accounts 域:账户同步 API 路由."""

import threading

from flask import Blueprint, Response
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.constants.sync_constants import SyncOperationType
from app.errors import NotFoundError, SystemError, ValidationError as AppValidationError
from app.models.instance import Instance
from app.services.accounts_sync import accounts_sync_service
from app.utils.decorators import require_csrf, update_required
from app.utils.response_utils import jsonify_unified_error_message, jsonify_unified_success
from app.utils.route_safety import log_with_context, safe_route_call
from app.utils.structlog_config import log_info, log_warning

# 创建蓝图
accounts_sync_bp = Blueprint(
    "accounts_sync",
    __name__,
    url_prefix="/sync",
)

BACKGROUND_SYNC_EXCEPTIONS: tuple[type[BaseException], ...] = (
    AppValidationError,
    SystemError,
    SQLAlchemyError,
    RuntimeError,
)


def _ensure_active_instances() -> int:
    """校验是否存在活跃实例并返回数量."""
    active_count = Instance.query.filter_by(is_active=True).count()
    if active_count == 0:
        msg = "没有找到活跃的数据库实例"
        log_warning(msg, module="accounts_sync", user_id=current_user.id)
        raise AppValidationError(msg)
    return active_count


def _launch_background_sync(created_by: int | None) -> threading.Thread:
    """启动后台线程执行全量同步任务."""

    def _run_sync_task(captured_created_by: int | None) -> None:
        from app.tasks.accounts_sync_tasks import sync_accounts

        try:
            sync_accounts(manual_run=True, created_by=captured_created_by)
        except BACKGROUND_SYNC_EXCEPTIONS as exc:  # pragma: no cover - 后台线程日志
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
        args=(created_by,),
        name="sync_accounts_manual_batch",
        daemon=True,
    )
    thread.start()
    return thread


def _get_instance(instance_id: int) -> Instance:
    """获取实例或抛出错误.

    Args:
        instance_id: 实例 ID.

    Returns:
        实例对象.

    Raises:
        NotFoundError: 当实例不存在时抛出.

    """
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance is None:
        msg = "实例不存在"
        raise NotFoundError(msg)
    return instance


def _normalize_sync_result(result: dict | None, *, context: str) -> tuple[bool, dict]:
    """规范化同步结果.

    将同步服务返回的结果转换为统一格式.

    Args:
        result: 同步结果字典,可能为 None.
        context: 上下文描述,用于生成默认消息.

    Returns:
        (是否成功, 规范化后的结果字典).

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


def _log_sync_failure(instance: Instance, *, message: str) -> None:
    """统一记录实例同步失败日志."""
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


@accounts_sync_bp.route("/api/sync-all", methods=["POST"])
@login_required
@update_required
@require_csrf
def sync_all_accounts() -> str | Response | tuple[Response, int]:
    """触发后台批量同步所有实例的账户信息.

    在后台线程中启动批量同步任务,不阻塞请求.

    Returns:
        JSON 响应,包含任务 ID.

    Raises:
        AppValidationError: 当没有活跃实例时抛出.
        SystemError: 当任务触发失败时抛出.

    """

    def _execute() -> str | Response | tuple[Response, int]:
        log_info("触发批量账户同步", module="accounts_sync", user_id=current_user.id)
        active_instance_count = _ensure_active_instances()
        created_by = getattr(current_user, "id", None)
        thread = _launch_background_sync(created_by)

        log_info(
            "批量账户同步任务已在后台启动",
            module="accounts_sync",
            user_id=current_user.id,
            active_instance_count=active_instance_count,
            thread_name=thread.name,
        )

        return jsonify_unified_success(
            message="批量账户同步任务已在后台启动,请稍后在会话中心查看进度.",
            data={"manual_job_id": thread.name},
        )

    return safe_route_call(
        _execute,
        module="accounts_sync",
        action="sync_all_accounts",
        public_error="批量同步任务触发失败,请稍后重试",
        context={"scope": "all_instances"},
        expected_exceptions=(AppValidationError, SystemError),
    )


@accounts_sync_bp.route("/api/instances/<int:instance_id>/sync", methods=["POST"])
@login_required
@update_required
@require_csrf
def sync_instance_accounts(instance_id: int) -> Response:
    """同步指定实例的账户信息,统一返回 JSON.

    Args:
        instance_id: 实例 ID.

    Returns:
        JSON 响应,包含同步结果和统计信息.

    Raises:
        NotFoundError: 当实例不存在时抛出.
        SystemError: 当同步失败时抛出.

    """

    def _execute() -> Response:
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
        _log_sync_failure(instance, message=failure_message)

        return jsonify_unified_error_message(
            failure_message,
            extra={"result": normalized, "instance_id": instance.id},
        )

    return safe_route_call(
        _execute,
        module="accounts_sync",
        action="sync_instance_accounts",
        public_error="账户同步失败,请重试",
        context={"instance_id": instance_id},
        expected_exceptions=(NotFoundError, SystemError),
    )
