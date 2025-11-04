
"""
鲸落 - 账户同步记录路由
"""

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
    """同步所有实例的账户（使用新的会话管理架构）"""
    from app.services.sync_session_service import sync_session_service

    try:
        log_info("开始同步所有账户", module="account_sync", user_id=current_user.id)

        # 获取所有活跃实例
        instances = Instance.query.filter_by(is_active=True).all()

        if not instances:
            log_warning(
                "没有找到活跃的数据库实例",
                module="account_sync",
                user_id=current_user.id,
            )
            raise AppValidationError("没有找到活跃的数据库实例")

        # 创建同步会话
        session = sync_session_service.create_session(
            sync_type=SyncOperationType.MANUAL_BATCH.value,
            sync_category=SyncCategory.ACCOUNT.value,
            created_by=current_user.id,
        )

        log_info(
            "创建手动批量同步会话",
            module="account_sync",
            session_id=session.session_id,
            user_id=current_user.id,
            instance_count=len(instances),
        )

        # 添加实例记录
        instance_ids = [inst.id for inst in instances]
        records = sync_session_service.add_instance_records(session.session_id, instance_ids)
        session.total_instances = len(instances)

        success_count = 0
        failed_count = 0
        results = []

        for instance in instances:
            # 找到对应的记录
            record = next((r for r in records if r.instance_id == instance.id), None)
            if not record:
                continue

            try:
                # 开始实例同步
                sync_session_service.start_instance_sync(record.id)

                log_info(
                    f"开始同步实例: {instance.name}",
                    module="account_sync",
                    session_id=session.session_id,
                    instance_id=instance.id,
                )

                # 使用统一的账户同步服务
                raw_result = account_sync_service.sync_accounts(
                    instance, sync_type=SyncOperationType.MANUAL_BATCH.value, session_id=session.session_id
                )

                is_success, normalized = _normalize_sync_result(
                    raw_result,
                    context=f"实例 {instance.name} 账户同步",
                )

                if is_success:
                    success_count += 1

                    # 完成实例同步
                    details = normalized.get("details", {})
                    inventory = details.get("inventory", {})
                    permissions = details.get("permissions", {})
                    sync_session_service.complete_instance_sync(
                        record.id,
                        items_synced=permissions.get("updated", 0) + permissions.get("created", 0),
                        items_created=inventory.get("created", 0),
                        items_updated=permissions.get("updated", 0),
                        items_deleted=inventory.get("deactivated", 0),
                        sync_details=details,
                    )

                    # 移除实例同步成功的日志记录，减少日志噪音

                    # 同步会话记录已通过sync_session_service管理，无需额外创建记录
                else:
                    failed_count += 1

                    # 标记实例同步失败
                    sync_session_service.fail_instance_sync(
                        record.id,
                        error_message=normalized.get("message", "同步失败"),
                        sync_details=normalized.get("details", {}),
                    )

                    log_error(
                        f"实例同步失败: {instance.name}",
                        module="account_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        error=normalized.get("message", "同步失败"),
                    )

                    # 同步会话记录已通过sync_session_service管理，无需额外创建记录

                results.append(
                    {
                        "instance_name": instance.name,
                        "success": is_success,
                        "status": normalized.get("status"),
                        "message": normalized.get("message"),
                        "synced_count": normalized.get("synced_count", 0),
                        "details": normalized.get("details"),
                    }
                )

            except Exception as e:
                failed_count += 1

                # 标记实例同步失败
                if record:
                    sync_session_service.fail_instance_sync(
                        record.id,
                        error_message=str(e),
                        sync_details={"exception": str(e)},
                    )

                log_error(
                    f"实例同步异常: {instance.name}",
                    module="account_sync",
                    session_id=session.session_id,
                    instance_id=instance.id,
                    error=str(e),
                )

                # 同步会话记录已通过sync_session_service管理，无需额外创建记录

                results.append(
                    {
                        "instance_name": instance.name,
                        "success": False,
                        "status": "failed",
                        "message": f"同步失败: {str(e)}",
                        "synced_count": 0,
                    }
                )

        # 完成同步会话
        session.update_statistics(succeeded_instances=success_count, failed_instances=failed_count)
        db.session.commit()

        # 记录同步完成日志
        log_info(
            f"批量同步完成: 成功 {success_count} 个实例，失败 {failed_count} 个实例",
            module="account_sync",
            session_id=session.session_id,
            user_id=current_user.id,
            total_instances=len(instances),
            success_count=success_count,
            failed_count=failed_count,
            session_status=session.status,
        )

        # 记录操作日志
        log_info(
            "批量同步账户完成",
            module="account_sync",
            operation_type="BATCH_SYNC_ACCOUNTS_COMPLETE",
            session_id=session.session_id,
            user_id=current_user.id,
            total_instances=len(instances),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
        )

        return jsonify_unified_success(
            data={
                "total_instances": len(instances),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results,
            },
            message=f"批量同步完成，成功 {success_count} 个实例，失败 {failed_count} 个实例",
        )

    except AppValidationError:
        raise
    except Exception as e:
        log_error(
            "同步所有账户失败",
            module="account_sync",
            operation="sync_all_accounts",
            user_id=current_user.id if current_user else None,
            exception=str(e),
        )
        db.session.rollback()

        raise SystemError(f"批量同步失败: {str(e)}") from e

# sync_details route removed - functionality replaced by sync_sessions API


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
