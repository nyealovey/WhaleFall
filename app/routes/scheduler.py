
"""
定时任务管理路由
"""

from typing import Any
import threading

from flask import Blueprint, Response, current_app, render_template, request
from flask_login import current_user, login_required  # type: ignore

from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.errors import NotFoundError, SystemError, ValidationError
from app.views.scheduler_job_form_view import SchedulerJobFormView
from app.scheduler import get_scheduler
from app.utils.decorators import require_csrf, scheduler_manage_required, scheduler_view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info, log_warning

# 创建蓝图
scheduler_bp = Blueprint("scheduler", __name__)

_scheduler_job_form_view = SchedulerJobFormView.as_view("scheduler_job_form_view")
_scheduler_job_form_view = login_required(scheduler_manage_required(require_csrf(_scheduler_job_form_view)))  # type: ignore
scheduler_bp.add_url_rule(
    "/api/jobs/<job_id>",
    view_func=_scheduler_job_form_view,
    methods=["PUT"],
)


@scheduler_bp.route("/")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def index() -> str:
    """定时任务管理页面。

    渲染定时任务管理界面，提供任务查看、暂停、恢复、执行等功能。

    Returns:
        渲染的定时任务管理页面 HTML。
    """
    return render_template("admin/scheduler/index.html")


@scheduler_bp.route("/api/jobs")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def get_jobs() -> Response:
    """获取所有定时任务。

    查询调度器中的所有任务，包括任务状态、触发器信息等。

    Returns:
        包含任务列表的 JSON 响应。

    Raises:
        SystemError: 当调度器未启动时抛出。
    """
    try:
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            log_warning("调度器未启动", module="scheduler")
            raise SystemError("调度器未启动")
        jobs = scheduler.get_jobs()
        jobs_data: list[dict[str, Any]] = []

        for job in jobs:
            try:
                # 检查任务状态
                is_paused = job.next_run_time is None
                is_builtin = job.id in BUILTIN_TASK_IDS

                trigger_type = "unknown"
                trigger_args: dict[str, Any] = {}
                
                # 简化触发器信息显示
                trigger_type = str(type(job.trigger).__name__).lower().replace("trigger", "")
                
                if trigger_type == "cron" and 'CronTrigger' in str(type(job.trigger)):
                    # 对于CronTrigger，包含所有字段用于编辑
                    trigger_info = {}
                    trigger_args = {}
                    
                    # 包含所有字段，用于编辑时正确显示
                    # CronTrigger使用fields属性存储字段值
                    fields = getattr(job.trigger, 'fields', {})
                    
                    # 检查fields是否为字典
                    if isinstance(fields, dict):
                        # 按时间顺序生成trigger_args：秒、分、时、日、月、周、年
                        trigger_args['second'] = fields.get('second', '0')
                        trigger_args['minute'] = fields.get('minute', '0')
                        trigger_args['hour'] = fields.get('hour', '0')
                        trigger_args['day'] = fields.get('day', '*')
                        trigger_args['month'] = fields.get('month', '*')
                        trigger_args['day_of_week'] = fields.get('day_of_week', '*')
                        trigger_args['year'] = fields.get('year', '') if fields.get('year') is not None else ''
                    elif isinstance(fields, list):
                        # 如果是列表，直接使用字段值
                        # 按时间顺序生成trigger_args：秒、分、时、日、月、周、年
                        if len(fields) >= 8:
                            trigger_args['second'] = str(fields[7]) if fields[7] is not None else '0'
                            trigger_args['minute'] = str(fields[6]) if fields[6] is not None else '0'
                            trigger_args['hour'] = str(fields[5]) if fields[5] is not None else '0'
                            trigger_args['day'] = str(fields[2]) if fields[2] is not None else '*'
                            trigger_args['month'] = str(fields[1]) if fields[1] is not None else '*'
                            trigger_args['day_of_week'] = str(fields[4]) if fields[4] is not None else '*'
                            trigger_args['year'] = str(fields[0]) if fields[0] is not None else ''
                        else:
                            log_warning(f"fields列表长度不足: {len(fields)}")
                            trigger_args['second'] = '0'
                            trigger_args['minute'] = '0'
                            trigger_args['hour'] = '0'
                            trigger_args['day'] = '*'
                            trigger_args['month'] = '*'
                            trigger_args['day_of_week'] = '*'
                            trigger_args['year'] = ''
                    else:
                        # 如果既不是字典也不是列表，使用默认值
                        log_warning(
                            "触发器字段类型异常",
                            module="scheduler",
                            job_id=job.id,
                            field_type=str(type(fields)),
                        )
                        trigger_args['second'] = '0'
                        trigger_args['minute'] = '0'
                        trigger_args['hour'] = '0'
                        trigger_args['day'] = '*'
                        trigger_args['month'] = '*'
                        trigger_args['day_of_week'] = '*'
                        trigger_args['year'] = ''
                    
                    # 只显示非通配符的字段用于简洁显示
                    if isinstance(fields, dict):
                        if fields.get('second') and fields.get('second') != '*':
                            trigger_info['second'] = fields.get('second')
                        if fields.get('minute') and fields.get('minute') != '*':
                            trigger_info['minute'] = fields.get('minute')
                        if fields.get('hour') and fields.get('hour') != '*':
                            trigger_info['hour'] = fields.get('hour')
                        if fields.get('day') and fields.get('day') != '*':
                            trigger_info['day'] = fields.get('day')
                        if fields.get('month') and fields.get('month') != '*':
                            trigger_info['month'] = fields.get('month')
                        if fields.get('day_of_week') and fields.get('day_of_week') != '*':
                            trigger_info['day_of_week'] = fields.get('day_of_week')
                        if fields.get('year') and fields.get('year') is not None and fields.get('year') != '*':
                            trigger_info['year'] = fields.get('year')
                    elif isinstance(fields, list):
                        # 如果是列表，直接使用字段值，按时间顺序排序：秒、分、时、日、月、周、年
                        if len(fields) >= 8:
                            # 按时间顺序添加非默认值
                            if str(fields[7]) != '0':  # second
                                trigger_info['second'] = str(fields[7])
                            if str(fields[6]) != '0':  # minute
                                trigger_info['minute'] = str(fields[6])
                            if str(fields[5]) != '0':  # hour
                                trigger_info['hour'] = str(fields[5])
                            if str(fields[2]) != '*':  # day
                                trigger_info['day'] = str(fields[2])
                            if str(fields[1]) != '*':  # month
                                trigger_info['month'] = str(fields[1])
                            if str(fields[4]) != '*':  # day_of_week
                                trigger_info['day_of_week'] = str(fields[4])
                            if str(fields[0]) != '*' and str(fields[0]) != '':  # year
                                trigger_info['year'] = str(fields[0])
                else:
                    # 对于其他类型的触发器，使用原始字符串
                    trigger_args = {"description": str(job.trigger)}
            except Exception as job_error:
                log_error(
                    "处理任务触发器信息失败",
                    module="scheduler",
                    job_id=job.id,
                    error=str(job_error),
                )
                # 使用默认值继续处理
                trigger_type = "unknown"
                trigger_args = {}

            # 模拟任务状态
            state = "STATE_PAUSED"
            if scheduler.running and not is_paused:
                state = "STATE_RUNNING"

            # 获取任务的上次运行时间（从日志中查找）
            last_run_time = None
            try:
                from app.models.unified_log import UnifiedLog
                from app.utils.time_utils import time_utils
                from datetime import timedelta
                
                # 查找最近24小时内该任务的执行日志
                from datetime import timedelta
                recent_logs = UnifiedLog.query.filter(
                    UnifiedLog.module == "scheduler",
                    UnifiedLog.message.like(f"%{job.name}%"),
                    UnifiedLog.timestamp >= time_utils.now() - timedelta(days=1)
                ).order_by(UnifiedLog.timestamp.desc()).first()

                if recent_logs:
                    last_run_time = recent_logs.timestamp.isoformat()
            except Exception as lookup_error:
                log_warning(
                    "获取任务上次运行时间失败",
                    module="scheduler",
                    job_id=job.id,
                    error=str(lookup_error),
                )

            job_info = {
                "id": job.id,
                "name": job.name,
                "description": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "last_run_time": last_run_time,
                "trigger_type": trigger_type,
                "trigger_args": trigger_args,
                "state": state,
                "is_builtin": is_builtin,
                "func": job.func.__name__ if hasattr(job.func, "__name__") else str(job.func),
                "args": job.args,
                "kwargs": job.kwargs,
            }
            jobs_data.append(job_info)

        # 按ID排序任务列表
        jobs_data.sort(key=lambda x: x["id"])

        log_info("获取任务列表成功", module="scheduler", job_count=len(jobs_data))
        return jsonify_unified_success(data=jobs_data, message="任务列表获取成功")

    except Exception as exc:
        log_error("获取任务列表失败", module="scheduler", error=str(exc))
        raise SystemError("获取任务列表失败") from exc


@scheduler_bp.route("/api/jobs/<job_id>")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def get_job(job_id: str) -> Response:
    """获取指定任务详情"""
    try:
        job = get_scheduler().get_job(job_id)  # type: ignore
        if not job:
            raise NotFoundError("任务不存在")

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
        raise SystemError("获取任务详情失败") from exc






@scheduler_bp.route("/api/jobs/<job_id>/pause", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
@require_csrf
def pause_job(job_id: str) -> Response:
    """暂停任务"""
    try:
        get_scheduler().pause_job(job_id)  # type: ignore
        log_info("任务暂停成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(message="任务暂停成功")

    except Exception as exc:
        log_error("暂停任务失败", module="scheduler", job_id=job_id, error=str(exc))
        raise SystemError("暂停任务失败") from exc


@scheduler_bp.route("/api/jobs/<job_id>/resume", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
@require_csrf
def resume_job(job_id: str) -> Response:
    """恢复任务"""
    try:
        get_scheduler().resume_job(job_id)  # type: ignore
        log_info("任务恢复成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(message="任务恢复成功")

    except Exception as exc:
        log_error("恢复任务失败", module="scheduler", job_id=job_id, error=str(exc))
        raise SystemError("恢复任务失败") from exc


@scheduler_bp.route("/api/jobs/<job_id>/run", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
@require_csrf
def run_job(job_id: str) -> Response:
    """立即执行任务"""
    try:
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            log_warning("调度器未启动", module="scheduler")
            raise SystemError("调度器未启动")

        job = scheduler.get_job(job_id)
        if not job:
            raise NotFoundError("任务不存在")

        log_info("开始立即执行任务", module="scheduler", job_id=job_id, job_name=job.name)

        # 在请求上下文内获取当前用户信息，避免线程中访问 current_user 失败
        created_by = None
        user_is_authenticated = False
        try:
            user_is_authenticated = current_user.is_authenticated  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - 防御性捕获
            user_is_authenticated = False
        if user_is_authenticated:
            created_by = getattr(current_user, "id", None)

        try:
            def _run_job_in_background(captured_created_by: int | None = created_by) -> None:
                try:
                    if job_id in BUILTIN_TASK_IDS:
                        manual_kwargs = dict(job.kwargs) if job.kwargs else {}
                        if job_id in ["sync_accounts", "calculate_database_size_aggregations"]:
                            manual_kwargs["manual_run"] = True
                            manual_kwargs["created_by"] = captured_created_by
                        job.func(*job.args, **manual_kwargs)
                    else:
                        from app import create_app

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

            thread = threading.Thread(target=_run_job_in_background, name=f"{job_id}_manual", daemon=True)
            thread.start()

            return jsonify_unified_success(
                data={"manual_job_id": thread.name},
                message="任务已提交后台执行",
            )

        except Exception as func_error:
            log_error(
                "任务函数执行失败",
                module="scheduler",
                job_id=job_id,
                job_name=job.name,
                error=str(func_error),
            )
            raise SystemError("任务执行失败") from func_error

    except NotFoundError:
        raise
    except Exception as exc:
        log_error("执行任务失败", module="scheduler", job_id=job_id, error=str(exc))
        raise SystemError("执行任务失败") from exc






@scheduler_bp.route("/api/jobs/reload", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
@require_csrf
def reload_jobs() -> Response:
    """重新加载所有任务配置。

    此操作会删除现有任务、重新读取配置并确保任务元数据最新。

    Returns:
        Response: 包含删除与重载结果的 JSON 响应。
    """
    try:
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            log_warning("调度器未启动", module="scheduler")
            raise SystemError("调度器未启动")

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
        from app.scheduler import _reload_all_jobs
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
                "reloaded_count": len(reloaded_jobs)
            },
            message=f"已删除 {deleted_count} 个任务，重新加载 {len(reloaded_jobs)} 个任务"
        )

    except Exception as exc:
        log_error("重新加载任务失败", module="scheduler", error=str(exc))
        raise SystemError("重新加载任务失败") from exc
