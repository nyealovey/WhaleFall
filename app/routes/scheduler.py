
"""定时任务管理路由."""

import threading
from datetime import timedelta
from typing import Any

from flask import Blueprint, Response, render_template
from flask_login import current_user, login_required  # type: ignore

from app import create_app
from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.errors import NotFoundError, SystemError
from app.models.unified_log import UnifiedLog
from app.scheduler import _reload_all_jobs, get_scheduler
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import require_csrf, scheduler_manage_required, scheduler_view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import time_utils
from app.views.scheduler_forms import SchedulerJobFormView

# 创建蓝图
scheduler_bp = Blueprint("scheduler", __name__)

JOB_CATEGORY_MAP: dict[str, str] = {
    "sync_accounts": SyncCategory.ACCOUNT.value,
    "collect_database_sizes": SyncCategory.CAPACITY.value,
    "calculate_database_size_aggregations": SyncCategory.AGGREGATION.value,
}


def _ensure_scheduler_running() -> Any:
    """返回运行中的调度器,若未启动则抛出系统错误.

    Returns:
        运行中的调度器实例.

    Raises:
        SystemError: 当调度器未启动时抛出.

    """
    scheduler = get_scheduler()  # type: ignore
    if not scheduler.running:
        log_warning("调度器未启动", module="scheduler")
        msg = "调度器未启动"
        raise SystemError(msg)
    return scheduler


def _resolve_session_last_run(category: str | None) -> str | None:
    if not category:
        return None
    sessions = sync_session_service.get_sessions_by_category(category, limit=10)
    for session in sessions:
        if session.sync_type == SyncOperationType.SCHEDULED_TASK.value:
            return (
                session.completed_at
                or session.updated_at
                or session.started_at
                or session.created_at
            ).isoformat()
    return None


def _build_job_payload(job: Any, scheduler: Any) -> dict[str, Any]:
    trigger_type, trigger_args = _collect_trigger_args(job)
    state = "STATE_RUNNING" if scheduler.running and job.next_run_time else "STATE_PAUSED"
    last_run_time = _lookup_job_last_run(job)
    if not last_run_time:
        category = JOB_CATEGORY_MAP.get(job.id)
        session_time = _resolve_session_last_run(category)
        if session_time:
            last_run_time = session_time

    return {
        "id": job.id,
        "name": job.name,
        "description": job.name,
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        "last_run_time": last_run_time,
        "trigger_type": trigger_type,
        "trigger_args": trigger_args,
        "state": state,
        "is_builtin": job.id in BUILTIN_TASK_IDS,
        "func": job.func.__name__ if hasattr(job.func, "__name__") else str(job.func),
        "args": job.args,
        "kwargs": job.kwargs,
    }


def _collect_trigger_args(job: Any) -> tuple[str, dict[str, Any]]:
    trigger_type = str(type(job.trigger).__name__).lower().replace("trigger", "")
    trigger_args: dict[str, Any] = {}

    if trigger_type != "cron" or "CronTrigger" not in str(type(job.trigger)):
        return trigger_type, {"description": str(job.trigger)}

    fields = getattr(job.trigger, "fields", {})
    if isinstance(fields, dict):
        trigger_args["second"] = fields.get("second", "0")
        trigger_args["minute"] = fields.get("minute", "0")
        trigger_args["hour"] = fields.get("hour", "0")
        trigger_args["day"] = fields.get("day", "*")
        trigger_args["month"] = fields.get("month", "*")
        trigger_args["day_of_week"] = fields.get("day_of_week", "*")
        trigger_args["year"] = fields.get("year") or ""
        return trigger_type, trigger_args

    if isinstance(fields, list) and len(fields) >= 8:
        trigger_args["second"] = str(fields[7] or "0")
        trigger_args["minute"] = str(fields[6] or "0")
        trigger_args["hour"] = str(fields[5] or "0")
        trigger_args["day"] = str(fields[2] or "*")
        trigger_args["month"] = str(fields[1] or "*")
        trigger_args["day_of_week"] = str(fields[4] or "*")
        trigger_args["year"] = str(fields[0] or "")
        return trigger_type, trigger_args

    log_warning(
        "触发器字段类型异常",
        module="scheduler",
        job_id=job.id,
        field_type=str(type(fields)),
    )
    return trigger_type, {
        "second": "0",
        "minute": "0",
        "hour": "0",
        "day": "*",
        "month": "*",
        "day_of_week": "*",
        "year": "",
    }


def _lookup_job_last_run(job: Any) -> str | None:
    try:
        recent_log = (
            UnifiedLog.query.filter(
                UnifiedLog.module == "scheduler",
                UnifiedLog.message.like(f"%{job.name}%"),
                UnifiedLog.timestamp >= time_utils.now() - timedelta(days=1),
            )
            .order_by(UnifiedLog.timestamp.desc())
            .first()
        )
        if recent_log:
            return recent_log.timestamp.isoformat()
    except Exception as lookup_error:  # pragma: no cover - 记录告警
        log_warning(
            "获取任务上次运行时间失败",
            module="scheduler",
            job_id=job.id,
            error=str(lookup_error),
        )
    return None

_scheduler_forms = SchedulerJobFormView.as_view("scheduler_forms")
_scheduler_forms = login_required(scheduler_manage_required(require_csrf(_scheduler_forms)))  # type: ignore
scheduler_bp.add_url_rule(
    "/api/jobs/<job_id>",
    view_func=_scheduler_forms,
    methods=["PUT"],
)


@scheduler_bp.route("/")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def index() -> str:
    """定时任务管理页面.

    渲染定时任务管理界面,提供任务查看、暂停、恢复、执行等功能.

    Returns:
        渲染的定时任务管理页面 HTML.

    """
    return render_template("admin/scheduler/index.html")


@scheduler_bp.route("/api/jobs")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def get_jobs() -> Response:
    """获取所有定时任务."""
    scheduler = _ensure_scheduler_running()
    try:
        jobs_data = [_build_job_payload(job, scheduler) for job in scheduler.get_jobs()]
        jobs_data.sort(key=lambda item: item["id"])
        log_info("获取任务列表成功", module="scheduler", job_count=len(jobs_data))
        return jsonify_unified_success(data=jobs_data, message="任务列表获取成功")
    except Exception as exc:
        log_error("获取任务列表失败", module="scheduler", error=str(exc))
        msg = "获取任务列表失败"
        raise SystemError(msg) from exc





@scheduler_bp.route("/api/jobs/<job_id>")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def get_job(job_id: str) -> Response:
    """获取指定任务详情.

    Args:
        job_id: APScheduler 任务 ID.

    Returns:
        Response: 任务详情 JSON.

    """
    job = get_scheduler().get_job(job_id)  # type: ignore
    if not job:
        msg = "任务不存在"
        raise NotFoundError(msg)

    try:
        job_info = {
            "id": job.id,
            "name": job.name,
            "next_run_time": (job.next_run_time.isoformat() if job.next_run_time else None),
            "trigger": str(job.trigger),
            "func": (job.func.__name__ if hasattr(job.func, "__name__") else str(job.func)),
            "args": job.args,
            "kwargs": job.kwargs,
            "misfire_grace_time": job.misfire_grace_time,
            "max_instances": job.max_instances,
            "coalesce": job.coalesce,
        }

        log_info("获取任务详情成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(data=job_info, message="任务详情获取成功")

    except NotFoundError:
        raise
    except Exception as exc:
        log_error("获取任务详情失败", module="scheduler", job_id=job_id, error=str(exc))
        msg = "获取任务详情失败"
        raise SystemError(msg) from exc






@scheduler_bp.route("/api/jobs/<job_id>/pause", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
@require_csrf
def pause_job(job_id: str) -> Response:
    """暂停任务.

    Args:
        job_id: 任务 ID.

    Returns:
        Response: 操作结果 JSON.

    """
    try:
        get_scheduler().pause_job(job_id)  # type: ignore
        log_info("任务暂停成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(message="任务暂停成功")

    except Exception as exc:
        log_error("暂停任务失败", module="scheduler", job_id=job_id, error=str(exc))
        msg = "暂停任务失败"
        raise SystemError(msg) from exc


@scheduler_bp.route("/api/jobs/<job_id>/resume", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
@require_csrf
def resume_job(job_id: str) -> Response:
    """恢复任务.

    Args:
        job_id: 任务 ID.

    Returns:
        Response: 操作结果 JSON.

    """
    try:
        get_scheduler().resume_job(job_id)  # type: ignore
        log_info("任务恢复成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(message="任务恢复成功")

    except Exception as exc:
        log_error("恢复任务失败", module="scheduler", job_id=job_id, error=str(exc))
        msg = "恢复任务失败"
        raise SystemError(msg) from exc


@scheduler_bp.route("/api/jobs/<job_id>/run", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
@require_csrf
def run_job(job_id: str) -> Response:
    """立即执行任务.

    Args:
        job_id: 任务 ID.

    Returns:
        Response: 操作结果 JSON.

    Raises:
        SystemError: 调度器未启动或任务不存在时抛出.

    """
    scheduler = _ensure_scheduler_running()
    job = scheduler.get_job(job_id)
    if not job:
        msg = "任务不存在"
        raise NotFoundError(msg)

    log_info("开始立即执行任务", module="scheduler", job_id=job_id, job_name=job.name)

    created_by = None
    user_is_authenticated = False
    try:
        user_is_authenticated = current_user.is_authenticated  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - 防御性捕获
        user_is_authenticated = False
    if user_is_authenticated:
        created_by = getattr(current_user, "id", None)

    def _run_job_in_background(captured_created_by: int | None = created_by) -> None:
        try:
            if job_id in BUILTIN_TASK_IDS:
                manual_kwargs = dict(job.kwargs) if job.kwargs else {}
                if job_id in ["sync_accounts", "calculate_database_size_aggregations"]:
                    manual_kwargs["manual_run"] = True
                    manual_kwargs["created_by"] = captured_created_by
                job.func(*job.args, **manual_kwargs)
            else:
                app = create_app(init_scheduler_on_start=False)  # type: ignore
                with app.app_context():
                    job.func(*job.args, **(job.kwargs or {}))

            log_info(
                "任务立即执行成功",
                module="scheduler",
                job_id=job_id,
                job_name=job.name,
            )
        except Exception as func_error:  # pragma: no cover - 防御性日志
            log_error(
                "任务函数执行失败",
                module="scheduler",
                job_id=job_id,
                job_name=job.name,
                error=str(func_error),
            )

    try:
        thread = threading.Thread(target=_run_job_in_background, name=f"{job_id}_manual", daemon=True)
        thread.start()

        return jsonify_unified_success(
            data={"manual_job_id": thread.name},
            message="任务已提交后台执行",
        )

    except Exception as exc:
        log_error("执行任务失败", module="scheduler", job_id=job_id, error=str(exc))
        msg = "执行任务失败"
        raise SystemError(msg) from exc






@scheduler_bp.route("/api/jobs/reload", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
@require_csrf
def reload_jobs() -> Response:
    """重新加载所有任务配置.

    此操作会删除现有任务、重新读取配置并确保任务元数据最新.

    Returns:
        Response: 包含删除与重载结果的 JSON 响应.

    """
    scheduler = _ensure_scheduler_running()
    try:
        # 获取现有任务列表
        existing_jobs = scheduler.get_jobs()
        existing_job_ids = [job.id for job in existing_jobs]

        # 删除所有现有任务
        deleted_count = 0
        for job_id in existing_job_ids:
            try:
                scheduler.remove_job(job_id)
                deleted_count += 1
                log_info("重新加载-删除任务", module="scheduler", job_id=job_id)
            except Exception as del_err:
                log_error(
                    "重新加载-删除任务失败",
                    module="scheduler",
                    job_id=job_id,
                    error=str(del_err),
                )

        # 重新加载任务配置
        _reload_all_jobs()

        # 获取重新加载后的任务列表
        reloaded_jobs = scheduler.get_jobs()
        reloaded_job_ids = [job.id for job in reloaded_jobs]

        log_info(
            "任务重新加载完成",
            module="scheduler",
            deleted_count=deleted_count,
            reloaded_count=len(reloaded_jobs),
        )

        return jsonify_unified_success(
            data={
                "deleted": existing_job_ids,
                "reloaded": reloaded_job_ids,
                "deleted_count": deleted_count,
                "reloaded_count": len(reloaded_jobs),
            },
            message=f"已删除 {deleted_count} 个任务,重新加载 {len(reloaded_jobs)} 个任务",
        )

    except Exception as exc:
        log_error("重新加载任务失败", module="scheduler", error=str(exc))
        msg = "重新加载任务失败"
        raise SystemError(msg) from exc
