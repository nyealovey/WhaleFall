
"""
定时任务管理路由
"""

from typing import Any

from flask import Blueprint, Response, current_app, render_template, request
from flask_login import login_required  # type: ignore

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.errors import NotFoundError, SystemError, ValidationError
from app.scheduler import get_scheduler
from app.services.scheduler_health_service import scheduler_health_service
from app.utils.decorators import require_csrf, scheduler_manage_required, scheduler_view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import time_utils

# 常量: 内置任务ID集合（统一前后端识别）
BUILTIN_TASK_IDS: set[str] = {
    "cleanup_logs", 
    "sync_accounts", 
    "monitor_partition_health", 
    "collect_database_sizes", 
    "calculate_database_size_aggregations"
}

# 创建蓝图
scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.route("/")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def index() -> str:
    """定时任务管理页面"""
    return render_template("admin/scheduler.html")


@scheduler_bp.route("/api/jobs")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def get_jobs() -> Response:
    """获取所有定时任务"""
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

        try:
            if job_id in BUILTIN_TASK_IDS:
                if job_id in ["sync_accounts", "calculate_database_size_aggregations"]:
                    result = job.func(manual_run=True)
                else:
                    result = job.func(*job.args, **job.kwargs)
            else:
                from app import create_app

                app = create_app()  # type: ignore
                with app.app_context():
                    result = job.func(*job.args, **job.kwargs)

            log_info(
                "任务立即执行成功",
                module="scheduler",
                job_id=job_id,
                job_name=job.name,
                result=str(result),
            )
            return jsonify_unified_success(data={"result": str(result)}, message="任务执行成功")

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
    """重新加载所有任务配置
    
    此操作会：
    1. 删除所有现有任务
    2. 重新从配置文件加载任务
    3. 确保任务名称和配置都是最新的
    
    Returns:
        Response: 标准化的JSON响应，包含重新加载的任务信息
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


@scheduler_bp.route("/api/jobs/<job_id>", methods=["PUT"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
@require_csrf
def update_job_trigger(job_id: str) -> Response:
    """更新内置任务的触发器配置（仅限内置任务）"""
    try:
        data = request.get_json() or {}
        if not data:
            raise ValidationError("请求数据不能为空")

        # 检查任务是否存在
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            log_warning("调度器未启动", module="scheduler")
            raise SystemError("调度器未启动")

        job = scheduler.get_job(job_id)
        if not job:
            raise NotFoundError("任务不存在")

        # 只允许修改内置任务的触发器
        if job_id not in BUILTIN_TASK_IDS:
            raise SystemError("只能修改内置任务的触发器配置", status_code=403)

        # 检查是否包含触发器配置
        if "trigger_type" not in data:
            raise ValidationError("缺少触发器类型配置")

        # 构建新的触发器
        trigger = _build_trigger(data)
        if not trigger:
            raise ValidationError("无效的触发器配置")

        # 更新触发器
        scheduler.modify_job(job_id, trigger=trigger)
        
        # 获取更新后的任务信息
        updated_job = scheduler.get_job(job_id)
        if updated_job and hasattr(updated_job, 'next_run_time'):
            log_info(
                "任务触发器更新后的下次执行时间",
                module="scheduler",
                job_id=job_id,
                next_run_time=str(updated_job.next_run_time),
            )
        
        log_info("内置任务触发器更新成功", module="scheduler", job_id=job_id)
        return jsonify_unified_success(message="触发器更新成功")

    except NotFoundError:
        raise
    except ValidationError:
        raise
    except Exception as exc:
        log_error("更新任务触发器失败", module="scheduler", job_id=job_id, error=str(exc))
        raise SystemError("更新任务触发器失败") from exc


def _build_trigger(data: dict[str, Any]) -> CronTrigger | IntervalTrigger | DateTrigger | None:
    """根据前端数据构建 APScheduler 触发器。

    支持三种类型：cron、interval、date。

    Args:
        data (dict[str, Any]): 前端提交的数据。

    Returns:
        CronTrigger | IntervalTrigger | DateTrigger | None: 构建成功返回触发器，否则 None。
    """
    trigger_type = data.get("trigger_type")

    if trigger_type == "cron":
        cron_kwargs: dict[str, Any] = {}
        expr = str(data.get("cron_expression", "")).strip()
        parts: list[str] = expr.split() if expr else []

        # 读取单字段（前端可能传 bare 字段或 cron_ 前缀字段）
        def pick(*keys: str) -> Any:
            for k in keys:
                if data.get(k) is not None and str(data.get(k)).strip() != "":
                    return data.get(k)
            return None

        second = pick("cron_second", "second")
        minute = pick("cron_minute", "minute")
        hour = pick("cron_hour", "hour")
        day = pick("cron_day", "day")
        month = pick("cron_month", "month")
        day_of_week = pick("cron_weekday", "cron_day_of_week", "day_of_week", "weekday")
        year = pick("year")

        # 从表达式回填缺失字段
        try:
            if len(parts) == 7:
                s, m, h, d, mo, dow, y = parts
                second = second or s
                minute = minute or m
                hour = hour or h
                day = day or d
                month = month or mo
                day_of_week = day_of_week or dow
                year = year or y
            elif len(parts) == 6:
                s, m, h, d, mo, dow = parts
                second = second or s
                minute = minute or m
                hour = hour or h
                day = day or d
                month = month or mo
                day_of_week = day_of_week or dow
            elif len(parts) == 5:
                m, h, d, mo, dow = parts
                minute = minute or m
                hour = hour or h
                day = day or d
                month = month or mo
                day_of_week = day_of_week or dow
        except Exception:  # noqa: BLE001
            pass

        if year is not None:
            cron_kwargs["year"] = year
        if month is not None:
            cron_kwargs["month"] = month
        if day is not None:
            cron_kwargs["day"] = day
        if day_of_week is not None:
            cron_kwargs["day_of_week"] = day_of_week
        if hour is not None:
            cron_kwargs["hour"] = hour
        if minute is not None:
            cron_kwargs["minute"] = minute
        if second is not None:
            cron_kwargs["second"] = second


        try:
            # 确保CronTrigger使用与调度器相同的时区
            cron_kwargs["timezone"] = "Asia/Shanghai"
            return CronTrigger(**cron_kwargs)
        except Exception as e:  # noqa: BLE001
            log_error("CronTrigger 构建失败", module="scheduler", error=str(e))
            return None

    if trigger_type == "interval":
        kwargs: dict[str, int] = {}
        for key in ["weeks", "days", "hours", "minutes", "seconds"]:
            val = data.get(key)
            if val is None or str(val).strip() == "":
                continue
            try:
                iv = int(val)
                if iv > 0:
                    kwargs[key] = iv
            except Exception:  # noqa: BLE001
                continue
        if not kwargs:
            return None
        try:
            return IntervalTrigger(**kwargs)
        except Exception as e:  # noqa: BLE001
            log_error("IntervalTrigger 构建失败", module="scheduler", error=str(e))
            return None

    if trigger_type == "date":
        run_date = data.get("run_date")
        if not run_date:
            return None
        dt = None
        try:
            # 使用 time_utils 解析时间
            dt = time_utils.to_utc(str(run_date))
        except Exception:  # noqa: BLE001
            dt = None
        if dt is None:
            return None
        try:
            return DateTrigger(run_date=dt)
        except Exception as e:  # noqa: BLE001
            log_error("DateTrigger 构建失败", module="scheduler", error=str(e))
            return None

    return None




# 辅助函数

@scheduler_bp.route("/api/health")
@login_required
@scheduler_view_required
def get_scheduler_health() -> Response:
    """获取调度器健康状态"""
    try:
        scheduler = get_scheduler()
        report = scheduler_health_service.inspect(scheduler)

        jobstore_accessible = "jobstore_unreachable" not in report.warnings
        executor_working = report.executor_working

        health_score = 0
        if report.scheduler_running:
            health_score += 35
        if jobstore_accessible:
            health_score += 25
        if executor_working:
            health_score += 25
        if report.total_jobs > 0:
            health_score += 15

        if report.total_jobs > 0 and not executor_working:
            health_score = max(0, health_score - 30)
        if report.total_jobs == 0 and report.scheduler_running and jobstore_accessible:
            health_score = max(health_score, 40)

        if health_score >= 80:
            status = "healthy"
            status_text = "健康"
            status_color = "success"
        elif health_score >= 60:
            status = "warning"
            status_text = "警告"
            status_color = "warning"
        else:
            status = "error"
            status_text = "异常"
            status_color = "danger"

        current_time = time_utils.now_china()

        health_data = {
            "status": status,
            "status_text": status_text,
            "status_color": status_color,
            "health_score": health_score,
            "scheduler_running": report.scheduler_running,
            "thread_alive": report.scheduler_running,
            "jobstore_accessible": jobstore_accessible,
            "executor_working": executor_working,
            "total_jobs": report.total_jobs,
            "running_jobs": report.running_jobs,
            "paused_jobs": report.paused_jobs,
            "executor_details": [
                {
                    "name": item.name,
                    "class_name": item.class_name,
                    "healthy": item.healthy,
                    "details": item.details,
                }
                for item in report.executors
            ],
            "warnings": report.warnings,
            "last_check": time_utils.format_china_time(current_time, "%Y/%m/%d %H:%M:%S"),
        }

        log_info(
            "调度器健康检查完成",
            module="scheduler",
            health_score=health_score,
            status=status,
            total_jobs=report.total_jobs,
            running_jobs=report.running_jobs,
            executor_working=executor_working,
        )

        return jsonify_unified_success(data=health_data, message="调度器健康检查完成")

    except Exception as exc:
        log_error("获取调度器健康状态失败", module="scheduler", error=str(exc))
        raise SystemError("获取调度器健康状态失败") from exc
