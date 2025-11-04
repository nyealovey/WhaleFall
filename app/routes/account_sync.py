
"""
鲸落 - 账户同步记录路由
"""

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
from app.services.account_sync import account_sync_service
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import require_csrf, update_required, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info, log_warning

# 创建蓝图
account_sync_bp = Blueprint("account_sync", __name__)


def _get_instance(instance_id: int) -> Instance:
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance is None:
        raise NotFoundError("实例不存在")
    return instance


def _normalize_sync_result(result: dict | None, *, context: str) -> tuple[bool, dict]:
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


@account_sync_bp.route("/api/sync-all", methods=["POST"])
@login_required
@update_required
@require_csrf
def sync_all_accounts() -> str | Response | tuple[Response, int]:
    """触发后台批量同步所有实例的账户信息"""
    try:
        log_info("触发批量账户同步", module="account_sync", user_id=current_user.id)

        active_instance_count = Instance.query.filter_by(is_active=True).count()
        if active_instance_count == 0:
            log_warning(
                "没有找到活跃的数据库实例",
                module="account_sync",
                user_id=current_user.id,
            )
            raise AppValidationError("没有找到活跃的数据库实例")

        created_by = getattr(current_user, "id", None)

        def _run_sync_task(captured_created_by: int | None) -> None:
            from app.tasks.account_sync_tasks import sync_accounts

            try:
                sync_accounts(manual_run=True, created_by=captured_created_by)
            except Exception as exc:  # pragma: no cover - 后台线程日志
                log_error(
                    "后台批量账户同步失败",
                    module="account_sync",
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
            module="account_sync",
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
            module="account_sync",
            user_id=current_user.id if current_user else None,
            error=str(exc),
        )
        raise SystemError("批量同步任务触发失败，请稍后重试") from exc


@account_sync_bp.route("/api/instances/<int:instance_id>/sync", methods=["POST"])
@login_required
@update_required
@require_csrf
def sync_instance_accounts(instance_id: int) -> str | Response | tuple[Response, int]:
    """同步指定实例的账户信息"""
    instance = Instance.query.get_or_404(instance_id)
    is_json = request.is_json

    try:
        log_info(
            "开始同步实例账户",
            module="account_sync",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
        )

        raw_result = account_sync_service.sync_accounts(instance, sync_type=SyncOperationType.MANUAL_SINGLE.value)
        is_success, normalized = _normalize_sync_result(
            raw_result,
            context=f"实例 {instance.name} 账户同步",
        )

        if is_success:
            instance.sync_count = (instance.sync_count or 0) + 1
            db.session.commit()

            log_info(
                "实例账户同步成功",
                module="account_sync",
                user_id=current_user.id,
                instance_id=instance.id,
                instance_name=instance.name,
                synced_count=normalized.get("synced_count", 0),
            )

            if is_json:
                return jsonify_unified_success(
                    data={"result": normalized},
                    message="账户同步成功",
                )

            flash("账户同步成功！", FlashCategory.SUCCESS)
            return redirect(url_for("instance.detail", instance_id=instance_id))

        log_error(
            "实例账户同步失败",
            module="account_sync",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
            error=normalized.get("message", "未知错误"),
        )

        if is_json:
            raise SystemError(normalized.get("message", "账户同步失败"))

        flash(f"账户同步失败: {normalized.get('message', '未知错误')}", "error")
        return redirect(url_for("instance.detail", instance_id=instance_id))

    except Exception as exc:
        log_error(f"同步实例账户失败: {exc}", module="account_sync", instance_id=instance.id)
        log_error(
            "实例账户同步异常",
            module="account_sync",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
            error=str(exc),
        )

        if is_json:
            raise SystemError("账户同步失败，请重试") from exc

        flash("账户同步失败，请重试", FlashCategory.ERROR)
        return redirect(url_for("instance.detail", instance_id=instance_id))
