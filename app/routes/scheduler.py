"""定时任务管理路由."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, cast

from apscheduler.jobstores.base import JobLookupError
from flask import Blueprint, Flask, Response, current_app, has_app_context, render_template
from flask_restx import marshal
from flask.typing import RouteCallable
from flask_login import (  # type: ignore[import-untyped]  # Flask-Login 未提供类型存根, 后续在 third_party_stubs 中补充
    current_user,
    login_required,
)
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.local import LocalProxy

from app import create_app
from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.errors import AppError, ConflictError, NotFoundError, SystemError
from app.scheduler import _reload_all_jobs, get_scheduler
from app.routes.scheduler_restx_models import SCHEDULER_JOB_DETAIL_FIELDS, SCHEDULER_JOB_LIST_ITEM_FIELDS
from app.services.scheduler.scheduler_jobs_read_service import SchedulerJobsReadService
from app.utils.decorators import require_csrf, scheduler_manage_required, scheduler_view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import log_with_context, safe_route_call
from app.utils.structlog_config import log_info, log_warning
from app.views.scheduler_forms import SchedulerJobFormView

RouteReturn = Response | tuple[Response, int]

if TYPE_CHECKING:
    from apscheduler.schedulers.background import BackgroundScheduler

# 创建蓝图
scheduler_bp = Blueprint("scheduler", __name__)

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

_scheduler_jobs_read_service = SchedulerJobsReadService()


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


_scheduler_forms = SchedulerJobFormView.as_view("scheduler_forms")
_scheduler_forms = login_required(scheduler_manage_required(require_csrf(_scheduler_forms)))  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充通用包装以保留视图签名
scheduler_bp.add_url_rule(
    "/api/jobs/<job_id>",
    view_func=cast(RouteCallable, _scheduler_forms),
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
def get_jobs() -> Response | tuple[Response, int]:
    """获取所有定时任务."""

    def _execute() -> RouteReturn:
        jobs = _scheduler_jobs_read_service.list_jobs()
        payload = marshal(jobs, SCHEDULER_JOB_LIST_ITEM_FIELDS)
        log_info("获取任务列表成功", module="scheduler", job_count=len(payload))
        return jsonify_unified_success(data=payload, message="任务列表获取成功")

    return cast(
        Response | tuple[Response, int],
        safe_route_call(
            _execute,
            module="scheduler",
            action="get_jobs",
            public_error="获取任务列表失败",
            context={"endpoint": "jobs"},
            expected_exceptions=(ConflictError,),
        ),
    )


@scheduler_bp.route("/api/jobs/<job_id>")
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_view_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
def get_job(job_id: str) -> Response | tuple[Response, int]:
    """获取指定任务详情.

    Args:
        job_id: APScheduler 任务 ID.

    Returns:
        Response: 任务详情 JSON.

    """

    def _execute() -> RouteReturn:
        job = _scheduler_jobs_read_service.get_job(job_id)
        job_info = marshal(job, SCHEDULER_JOB_DETAIL_FIELDS)
        log_info("获取任务详情成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(data=job_info, message="任务详情获取成功")

    return cast(
        Response | tuple[Response, int],
        safe_route_call(
            _execute,
            module="scheduler",
            action="get_job",
            public_error="获取任务详情失败",
            context={"job_id": job_id},
            expected_exceptions=(NotFoundError, ConflictError),
        ),
    )


@scheduler_bp.route("/api/jobs/<job_id>/pause", methods=["POST"])
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_manage_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
@require_csrf
def pause_job(job_id: str) -> Response | tuple[Response, int]:
    """暂停任务.

    Args:
        job_id: 任务 ID.

    Returns:
        Response: 操作结果 JSON.

    """

    def _execute() -> RouteReturn:
        scheduler = _ensure_scheduler_running()
        scheduler.pause_job(job_id)
        log_info("任务暂停成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(message="任务暂停成功")

    return cast(
        Response | tuple[Response, int],
        safe_route_call(
            _execute,
            module="scheduler",
            action="pause_job",
            public_error="暂停任务失败",
            context={"job_id": job_id},
            expected_exceptions=(ConflictError,),
        ),
    )


@scheduler_bp.route("/api/jobs/<job_id>/resume", methods=["POST"])
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_manage_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
@require_csrf
def resume_job(job_id: str) -> Response | tuple[Response, int]:
    """恢复任务.

    Args:
        job_id: 任务 ID.

    Returns:
        Response: 操作结果 JSON.

    """

    def _execute() -> RouteReturn:
        scheduler = _ensure_scheduler_running()
        scheduler.resume_job(job_id)
        log_info("任务恢复成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(message="任务恢复成功")

    return cast(
        Response | tuple[Response, int],
        safe_route_call(
            _execute,
            module="scheduler",
            action="resume_job",
            public_error="恢复任务失败",
            context={"job_id": job_id},
            expected_exceptions=(ConflictError,),
        ),
    )


@scheduler_bp.route("/api/jobs/<job_id>/run", methods=["POST"])
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_manage_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
@require_csrf
def run_job(job_id: str) -> Response | tuple[Response, int]:
    """立即执行任务.

    Args:
        job_id: 任务 ID.

    Returns:
        Response: 操作结果 JSON.

    Raises:
        ConflictError: 调度器未启动或任务不存在时抛出.

    """

    def _execute() -> RouteReturn:
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
            current_app_proxy = cast(LocalProxy[Flask], current_app)
            base_app = (
                current_app_proxy._get_current_object()
                if has_app_context()
                else create_app(init_scheduler_on_start=False)
            )
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

    return cast(
        Response | tuple[Response, int],
        safe_route_call(
            _execute,
            module="scheduler",
            action="run_job",
            public_error="执行任务失败",
            context={"job_id": job_id},
            expected_exceptions=(NotFoundError, ConflictError),
        ),
    )


@scheduler_bp.route("/api/jobs/reload", methods=["POST"])
@login_required  # type: ignore[misc]  # Flask-Login 装饰器缺少类型提示, 计划补充本地 stub
@scheduler_manage_required  # type: ignore[misc]  # 自定义装饰器未保留 Callable 签名, 计划使用 ParamSpec 重写
@require_csrf
def reload_jobs() -> Response | tuple[Response, int]:
    """重新加载所有任务配置.

    此操作会删除现有任务、重新读取配置并确保任务元数据最新.

    Returns:
        Response: 包含删除与重载结果的 JSON 响应.

    """

    def _execute() -> RouteReturn:
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

    return cast(
        Response | tuple[Response, int],
        safe_route_call(
            _execute,
            module="scheduler",
            action="reload_jobs",
            public_error="重新加载任务失败",
            context={"endpoint": "reload_jobs"},
            expected_exceptions=(ConflictError,),
        ),
    )
