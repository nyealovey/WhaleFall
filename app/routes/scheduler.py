"""定时任务管理路由."""

from __future__ import annotations

import threading
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from apscheduler.jobstores.base import JobLookupError
from flask import Blueprint, Response, current_app, has_app_context, render_template
from flask_login import (  # type: ignore[import-untyped]  # Flask-Login 未提供类型存根, 后续在 third_party_stubs 中补充
    current_user,
    login_required,
)
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.errors import AppError, ConflictError, NotFoundError, SystemError
from app.models.unified_log import UnifiedLog
from app.scheduler import _reload_all_jobs, get_scheduler
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import require_csrf, scheduler_manage_required, scheduler_view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import log_with_context, safe_route_call
from app.utils.structlog_config import log_info, log_warning
from app.utils.time_utils import time_utils
from app.views.scheduler_forms import SchedulerJobFormView

if TYPE_CHECKING:
    from apscheduler.job import Job
    from apscheduler.schedulers.background import BackgroundScheduler

CRON_FIELD_COUNT = 8
CRON_YEAR_INDEX = 0
CRON_MONTH_INDEX = 1
CRON_DAY_INDEX = 2
CRON_DAY_OF_WEEK_INDEX = 4
CRON_HOUR_INDEX = 5
CRON_MINUTE_INDEX = 6
CRON_SECOND_INDEX = 7

# 创建蓝图
scheduler_bp = Blueprint("scheduler", __name__)
JobPayload = dict[str, object]
TriggerArgs = dict[str, str]

JOB_CATEGORY_MAP: dict[str, str] = {
    "sync_accounts": SyncCategory.ACCOUNT.value,
    "collect_database_sizes": SyncCategory.CAPACITY.value,
    "calculate_database_size_aggregations": SyncCategory.AGGREGATION.value,
}

LOG_LOOKUP_EXCEPTIONS: tuple[type[BaseException], ...] = (SQLAlchemyError,)
USER_STATE_EXCEPTIONS: tuple[type[BaseException], ...] = (AttributeError, RuntimeError)
BACKGROUND_EXECUTION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    AppError,
    ConflictError,
    NotFoundError,
    SystemError,
    RuntimeError,
    ValueError,
    LookupError,
    SQLAlchemyError,
)
JOB_REMOVAL_EXCEPTIONS: tuple[type[BaseException], ...] = (JobLookupError, ValueError)


def _ensure_scheduler_running() -> BackgroundScheduler:
    """返回运行中的调度器,若未启动则抛出系统错误.

    Returns:
        运行中的调度器实例.

    Raises:
        ConflictError: 当调度器未启动时抛出.

    """
    scheduler = cast("BackgroundScheduler | None", get_scheduler())
    if scheduler is None or not scheduler.running:
        log_warning("调度器未启动", module="scheduler")
        msg = "调度器未启动"
        raise ConflictError(msg)
    return scheduler


def _resolve_session_last_run(category: str | None) -> str | None:
    if not category:
        return None
    sessions = sync_session_service.get_sessions_by_category(category, limit=10)
    for session in sessions:
        if session.sync_type == SyncOperationType.SCHEDULED_TASK.value:
            return (session.completed_at or session.updated_at or session.started_at or session.created_at).isoformat()
    return None


def _build_job_payload(job: Job, scheduler: BackgroundScheduler) -> JobPayload:
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


def _collect_trigger_args(job: Job) -> tuple[str, TriggerArgs]:
    trigger_type = str(type(job.trigger).__name__).lower().replace("trigger", "")
    trigger_args: TriggerArgs = {}

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

    if isinstance(fields, list) and len(fields) >= CRON_FIELD_COUNT:
        trigger_args["second"] = str(fields[CRON_SECOND_INDEX] or "0")
        trigger_args["minute"] = str(fields[CRON_MINUTE_INDEX] or "0")
        trigger_args["hour"] = str(fields[CRON_HOUR_INDEX] or "0")
        trigger_args["day"] = str(fields[CRON_DAY_INDEX] or "*")
        trigger_args["month"] = str(fields[CRON_MONTH_INDEX] or "*")
        trigger_args["day_of_week"] = str(fields[CRON_DAY_OF_WEEK_INDEX] or "*")
        trigger_args["year"] = str(fields[CRON_YEAR_INDEX] or "")
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


def _lookup_job_last_run(job: Job) -> str | None:
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
    except LOG_LOOKUP_EXCEPTIONS as lookup_error:  # pragma: no cover - 记录告警
        log_warning(
            "获取任务上次运行时间失败",
            module="scheduler",
            job_id=job.id,
            error=str(lookup_error),
        )
    return None


_scheduler_forms = SchedulerJobFormView.as_view("scheduler_forms")
_scheduler_forms = login_required(scheduler_manage_required(require_csrf(_scheduler_forms)))  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充通用包装以保留视图签名
scheduler_bp.add_url_rule(
    "/api/jobs/<job_id>",
    view_func=_scheduler_forms,
    methods=["PUT"],
)


@scheduler_bp.route("/")
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_view_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
def index() -> str:
    """定时任务管理页面.

    渲染定时任务管理界面,提供任务查看、暂停、恢复、执行等功能.

    Returns:
        渲染的定时任务管理页面 HTML.

    """
    return render_template("admin/scheduler/index.html")


@scheduler_bp.route("/api/jobs")
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_view_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
def get_jobs() -> Response:
    """获取所有定时任务."""

    def _execute() -> Response:
        scheduler = _ensure_scheduler_running()
        jobs = cast("list[Job]", scheduler.get_jobs())
        jobs_data = [_build_job_payload(job, scheduler) for job in jobs]
        jobs_data.sort(key=lambda item: item["id"])
        log_info("获取任务列表成功", module="scheduler", job_count=len(jobs_data))
        return jsonify_unified_success(data=jobs_data, message="任务列表获取成功")

    return safe_route_call(
        _execute,
        module="scheduler",
        action="get_jobs",
        public_error="获取任务列表失败",
        context={"endpoint": "jobs"},
        expected_exceptions=(ConflictError,),
    )


@scheduler_bp.route("/api/jobs/<job_id>")
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_view_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
def get_job(job_id: str) -> Response:
    """获取指定任务详情.

    Args:
        job_id: APScheduler 任务 ID.

    Returns:
        Response: 任务详情 JSON.

    """

    def _execute() -> Response:
        scheduler = _ensure_scheduler_running()
        job = scheduler.get_job(job_id)
        if not job:
            msg = "任务不存在"
            raise NotFoundError(msg)

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

    return safe_route_call(
        _execute,
        module="scheduler",
        action="get_job",
        public_error="获取任务详情失败",
        context={"job_id": job_id},
        expected_exceptions=(NotFoundError, ConflictError),
    )


@scheduler_bp.route("/api/jobs/<job_id>/pause", methods=["POST"])
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_manage_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
@require_csrf
def pause_job(job_id: str) -> Response:
    """暂停任务.

    Args:
        job_id: 任务 ID.

    Returns:
        Response: 操作结果 JSON.

    """

    def _execute() -> Response:
        scheduler = _ensure_scheduler_running()
        scheduler.pause_job(job_id)
        log_info("任务暂停成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(message="任务暂停成功")

    return safe_route_call(
        _execute,
        module="scheduler",
        action="pause_job",
        public_error="暂停任务失败",
        context={"job_id": job_id},
        expected_exceptions=(ConflictError,),
    )


@scheduler_bp.route("/api/jobs/<job_id>/resume", methods=["POST"])
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_manage_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
@require_csrf
def resume_job(job_id: str) -> Response:
    """恢复任务.

    Args:
        job_id: 任务 ID.

    Returns:
        Response: 操作结果 JSON.

    """

    def _execute() -> Response:
        scheduler = _ensure_scheduler_running()
        scheduler.resume_job(job_id)
        log_info("任务恢复成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(message="任务恢复成功")

    return safe_route_call(
        _execute,
        module="scheduler",
        action="resume_job",
        public_error="恢复任务失败",
        context={"job_id": job_id},
        expected_exceptions=(ConflictError,),
    )


@scheduler_bp.route("/api/jobs/<job_id>/run", methods=["POST"])
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_manage_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
@require_csrf
def run_job(job_id: str) -> Response:
    """立即执行任务.

    Args:
        job_id: 任务 ID.

    Returns:
        Response: 操作结果 JSON.

    Raises:
        ConflictError: 调度器未启动或任务不存在时抛出.

    """

    def _execute() -> Response:
        scheduler = _ensure_scheduler_running()
        job = scheduler.get_job(job_id)
        if not job:
            msg = "任务不存在"
            raise NotFoundError(msg)

        log_info("开始立即执行任务", module="scheduler", job_id=job_id, job_name=job.name)

        created_by = None
        user_is_authenticated = False
        try:
            user_is_authenticated = current_user.is_authenticated  # type: ignore[attr-defined]  # current_user 由 Flask-Login 动态注入, 计划通过 typed proxy 提供属性提示
        except USER_STATE_EXCEPTIONS:  # pragma: no cover - 防御性捕获
            user_is_authenticated = False
        if user_is_authenticated:
            created_by = getattr(current_user, "id", None)

        def _run_job_in_background(captured_created_by: int | None = created_by) -> None:
            base_app = current_app._get_current_object() if has_app_context() else create_app(init_scheduler_on_start=False)
            try:
                with base_app.app_context():
                    if job_id in BUILTIN_TASK_IDS:
                        manual_kwargs = dict(job.kwargs) if job.kwargs else {}
                        if job_id in ["sync_accounts", "calculate_database_size_aggregations"]:
                            manual_kwargs["manual_run"] = True
                            manual_kwargs["created_by"] = captured_created_by
                        job.func(*job.args, **manual_kwargs)
                    else:
                        job.func(*job.args, **(job.kwargs or {}))

                log_info(
                    "任务立即执行成功",
                    module="scheduler",
                    job_id=job_id,
                    job_name=job.name,
                )
            except BACKGROUND_EXECUTION_EXCEPTIONS as func_error:  # pragma: no cover - 防御性日志
                log_with_context(
                    "error",
                    "任务函数执行失败",
                    module="scheduler",
                    action="run_job_background",
                    context={"job_id": job_id, "job_name": job.name},
                    extra={
                        "error_type": func_error.__class__.__name__,
                        "error_message": str(func_error),
                    },
                )

        thread = threading.Thread(target=_run_job_in_background, name=f"{job_id}_manual", daemon=True)
        thread.start()
        return jsonify_unified_success(
            data={"manual_job_id": thread.name},
            message="任务已提交后台执行",
        )

    return safe_route_call(
        _execute,
        module="scheduler",
        action="run_job",
        public_error="执行任务失败",
        context={"job_id": job_id},
        expected_exceptions=(NotFoundError, ConflictError),
    )


@scheduler_bp.route("/api/jobs/reload", methods=["POST"])
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_manage_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
@require_csrf
def reload_jobs() -> Response:
    """重新加载所有任务配置.

    此操作会删除现有任务、重新读取配置并确保任务元数据最新.

    Returns:
        Response: 包含删除与重载结果的 JSON 响应.

    """

    def _execute() -> Response:
        scheduler = _ensure_scheduler_running()
        existing_jobs = scheduler.get_jobs()
        existing_job_ids = [job.id for job in existing_jobs]

        deleted_count = 0
        for job_id in existing_job_ids:
            try:
                scheduler.remove_job(job_id)
            except JOB_REMOVAL_EXCEPTIONS as del_err:
                log_with_context(
                    "error",
                    "重新加载-删除任务失败",
                    module="scheduler",
                    action="reload_jobs",
                    context={"job_id": job_id},
                    extra={
                        "error_type": del_err.__class__.__name__,
                        "error_message": str(del_err),
                    },
                )
            else:
                deleted_count += 1
                log_info("重新加载-删除任务", module="scheduler", job_id=job_id)

        _reload_all_jobs()

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

    return safe_route_call(
        _execute,
        module="scheduler",
        action="reload_jobs",
        public_error="重新加载任务失败",
        context={"endpoint": "reload_jobs"},
        expected_exceptions=(ConflictError,),
    )
