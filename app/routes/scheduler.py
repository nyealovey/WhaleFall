
"""
定时任务管理路由
"""

from typing import Any
from flask import Blueprint, Response, render_template, request
from flask_login import login_required  # type: ignore

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.scheduler import get_scheduler
from app.utils.api_response import APIResponse
from app.utils.decorators import scheduler_manage_required, scheduler_view_required
from app.utils.structlog_config import get_system_logger

# 常量: 内置任务ID集合（统一前后端识别）
BUILTIN_TASK_IDS: set[str] = {
    "cleanup_logs", 
    "sync_accounts", 
    "monitor_partition_health", 
    "collect_database_sizes", 
    "calculate_database_size_aggregations"
}

# 初始化日志记录器
system_logger = get_system_logger()

# 创建蓝图
scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.route("/")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def index() -> str:
    """定时任务管理页面"""
    return render_template("scheduler/management.html")


@scheduler_bp.route("/api/jobs")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def get_jobs() -> Response:
    """获取所有定时任务"""
    try:
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore
        jobs = scheduler.get_jobs()
        system_logger.info("获取任务列表", module="scheduler", job_count=len(jobs))
        jobs_data: list[dict[str, Any]] = []

        for job in jobs:
            try:
                # 检查任务状态
                is_paused = job.next_run_time is None
                is_builtin = job.id in BUILTIN_TASK_IDS

                trigger_type = "unknown"
                trigger_args: dict[str, Any] = {}
                
                # 调试信息
                system_logger.info(f"处理任务: {job.id}, 触发器类型: {type(job.trigger)}")
                
                # 简化触发器信息显示
                trigger_type = str(type(job.trigger).__name__).lower().replace("trigger", "")
                
                # 统一触发器信息显示格式
                if hasattr(job.trigger, 'second') and 'CronTrigger' in str(type(job.trigger)):
                    # 对于CronTrigger，只显示非通配符字段
                    trigger_info = {}
                    trigger_args = {}
                    
                    # 只显示非'*'的字段，这样所有任务都会显示简洁的配置
                    if hasattr(job.trigger, 'second') and job.trigger.second != '*':
                        trigger_info['second'] = job.trigger.second
                        trigger_args['second'] = job.trigger.second
                    if hasattr(job.trigger, 'minute') and job.trigger.minute != '*':
                        trigger_info['minute'] = job.trigger.minute
                        trigger_args['minute'] = job.trigger.minute
                    if hasattr(job.trigger, 'hour') and job.trigger.hour != '*':
                        trigger_info['hour'] = job.trigger.hour
                        trigger_args['hour'] = job.trigger.hour
                    if hasattr(job.trigger, 'day') and job.trigger.day != '*':
                        trigger_info['day'] = job.trigger.day
                        trigger_args['day'] = job.trigger.day
                    if hasattr(job.trigger, 'month') and job.trigger.month != '*':
                        trigger_info['month'] = job.trigger.month
                        trigger_args['month'] = job.trigger.month
                    if hasattr(job.trigger, 'day_of_week') and job.trigger.day_of_week != '*':
                        trigger_info['day_of_week'] = job.trigger.day_of_week
                        trigger_args['day_of_week'] = job.trigger.day_of_week
                    if hasattr(job.trigger, 'year') and job.trigger.year is not None and job.trigger.year != '*':
                        trigger_info['year'] = job.trigger.year
                        trigger_args['year'] = job.trigger.year
                    
                    # 添加description字段用于显示
                    trigger_args['description'] = f"cron{trigger_info}"
                else:
                    # 对于其他类型的触发器，使用原始字符串
                    trigger_args = {"description": str(job.trigger)}
                    
            except Exception as job_error:
                system_logger.error(f"处理任务 {job.id} 时出错: {job_error}")
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
                from app.utils.time_utils import now_china
                from datetime import timedelta
                
                # 查找最近24小时内该任务的执行日志
                recent_logs = UnifiedLog.query.filter(
                    UnifiedLog.module == "scheduler",
                    UnifiedLog.message.like(f"%{job.name}%"),
                    UnifiedLog.timestamp >= now_china() - timedelta(days=1)
                ).order_by(UnifiedLog.timestamp.desc()).first()
                
                if recent_logs:
                    last_run_time = recent_logs.timestamp.isoformat()
            except Exception as e:
                system_logger.warning(f"获取任务 {job.id} 上次运行时间失败: {e}")

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

        return APIResponse.success(data=jobs_data, message="任务列表获取成功")  # type: ignore

    except Exception as e:
        system_logger.error("获取任务列表失败", module="scheduler", exception=e)
        return APIResponse.error("获取任务列表失败: {str(e)}")  # type: ignore


@scheduler_bp.route("/api/jobs/<job_id>")
@login_required  # type: ignore
@scheduler_view_required  # type: ignore
def get_job(job_id: str) -> Response:
    """获取指定任务详情"""
    try:
        job = get_scheduler().get_job(job_id)  # type: ignore
        if not job:
            return APIResponse.error("任务不存在", code=404)  # type: ignore

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

        return APIResponse.success(data=job_info, message="任务详情获取成功")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("获取任务详情失败: %s", error_str)
        return APIResponse.error("获取任务详情失败: {error_str}")  # type: ignore






@scheduler_bp.route("/api/jobs/<job_id>/disable", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def disable_job(job_id: str) -> Response:
    """禁用定时任务"""
    try:
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        job = scheduler.get_job(job_id)
        if not job:
            return APIResponse.error("任务不存在", code=404)  # type: ignore

        # 暂停任务
        scheduler.pause_job(job_id)
        system_logger.info("任务已禁用: {job_id}", module="scheduler")
        return APIResponse.success(data={"job_id": job_id}, message="任务已禁用")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("禁用任务失败: %s", error_str)
        return APIResponse.error(f"禁用任务失败: {error_str}")  # type: ignore


@scheduler_bp.route("/api/jobs/<job_id>/enable", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def enable_job(job_id: str) -> Response:
    """启用定时任务"""
    try:
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        job = scheduler.get_job(job_id)
        if not job:
            return APIResponse.error("任务不存在", code=404)  # type: ignore

        # 恢复任务
        scheduler.resume_job(job_id)
        system_logger.info("任务已启用: {job_id}", module="scheduler")
        return APIResponse.success(data={"job_id": job_id}, message="任务已启用")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("启用任务失败: %s", error_str)
        return APIResponse.error(f"启用任务失败: {error_str}")  # type: ignore


@scheduler_bp.route("/api/jobs/<job_id>/pause", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def pause_job(job_id: str) -> Response:
    """暂停任务"""
    try:
        get_scheduler().pause_job(job_id)  # type: ignore
        system_logger.info("任务暂停成功: {job_id}")
        return APIResponse.success("任务暂停成功")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("暂停任务失败: %s", error_str)
        return APIResponse.error(f"暂停任务失败: {error_str}")  # type: ignore


@scheduler_bp.route("/api/jobs/<job_id>/resume", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def resume_job(job_id: str) -> Response:
    """恢复任务"""
    try:
        get_scheduler().resume_job(job_id)  # type: ignore
        system_logger.info("任务恢复成功: {job_id}")
        return APIResponse.success("任务恢复成功")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("恢复任务失败: %s", error_str)
        return APIResponse.error(f"恢复任务失败: {error_str}")  # type: ignore


@scheduler_bp.route("/api/jobs/<job_id>/run", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def run_job(job_id: str) -> Response:
    """立即执行任务"""
    try:
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        job = scheduler.get_job(job_id)
        if not job:
            return APIResponse.error("任务不存在", code=404)  # type: ignore

        system_logger.info("开始立即执行任务: {job_id} - {job.name}")

        # 立即执行任务
        try:
            # 对于内置任务，直接调用任务函数（它们内部有应用上下文管理）
            if job_id in BUILTIN_TASK_IDS:
                # 对于sync_accounts和calculate_database_size_aggregations任务，手动执行时传递manual_run=True
                if job_id in ["sync_accounts", "calculate_database_size_aggregations"]:
                    result = job.func(manual_run=True)
                else:
                    result = job.func(*job.args, **job.kwargs)
                system_logger.info("任务立即执行成功: {job_id} - 结果: {result}")
                return APIResponse.success(data={"result": str(result)}, message="任务执行成功")  # type: ignore
            # 对于自定义任务，需要手动管理应用上下文
            from app import create_app

            app = create_app()  # type: ignore
            with app.app_context():
                result = job.func(*job.args, **job.kwargs)
                system_logger.info("任务立即执行成功: {job_id} - 结果: {result}")
                return APIResponse.success(data={"result": str(result)}, message="任务执行成功")  # type: ignore
        except Exception as func_error:
            error_str = str(func_error) if func_error else "未知错误"
            system_logger.error("任务函数执行失败: %s - %s", job_id, error_str)
            return APIResponse.error(f"任务执行失败: {error_str}")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("执行任务失败: %s", error_str)
        return APIResponse.error(f"执行任务失败: {error_str}")  # type: ignore






@scheduler_bp.route("/api/jobs/reload", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
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
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        # 获取现有任务列表
        existing_jobs = scheduler.get_jobs()
        existing_job_ids = [job.id for job in existing_jobs]
        
        # 删除所有现有任务
        deleted_count = 0
        for job_id in existing_job_ids:
            try:
                scheduler.remove_job(job_id)
                deleted_count += 1
                system_logger.info("重新加载-删除任务: %s", job_id)
            except Exception as del_err:
                system_logger.error("重新加载-删除任务失败: %s - %s", job_id, str(del_err))

        # 重新加载任务配置
        from app.scheduler import _reload_all_jobs
        _reload_all_jobs()
        
        # 获取重新加载后的任务列表
        reloaded_jobs = scheduler.get_jobs()
        reloaded_job_ids = [job.id for job in reloaded_jobs]
        
        system_logger.info(
            "任务重新加载完成",
            module="scheduler",
            deleted_count=deleted_count,
            reloaded_count=len(reloaded_jobs)
        )

        return APIResponse.success(
            data={
                "deleted": existing_job_ids,
                "reloaded": reloaded_job_ids,
                "deleted_count": deleted_count,
                "reloaded_count": len(reloaded_jobs)
            },
            message=f"已删除 {deleted_count} 个任务，重新加载 {len(reloaded_jobs)} 个任务"
        )

    except Exception as e:
        system_logger.error("重新加载任务失败: %s", str(e), exc_info=True)
        return APIResponse.error(f"重新加载任务失败: {str(e)}", code=500)  # type: ignore


@scheduler_bp.route("/api/jobs/<job_id>", methods=["PUT"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def update_job_trigger(job_id: str) -> Response:
    """更新内置任务的触发器配置（仅限内置任务）"""
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("请求数据不能为空", code=400)  # type: ignore

        # 检查任务是否存在
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        job = scheduler.get_job(job_id)
        if not job:
            return APIResponse.error("任务不存在", code=404)  # type: ignore

        # 只允许修改内置任务的触发器
        if job_id not in BUILTIN_TASK_IDS:
            return APIResponse.error("只能修改内置任务的触发器配置", code=403)  # type: ignore

        # 检查是否包含触发器配置
        if "trigger_type" not in data:
            return APIResponse.error("缺少触发器类型配置", code=400)  # type: ignore

        # 构建新的触发器
        trigger = _build_trigger(data)
        if not trigger:
            return APIResponse.error("无效的触发器配置", code=400)  # type: ignore

        # 更新触发器
        scheduler.modify_job(job_id, trigger=trigger)
        
        # 获取更新后的任务信息
        updated_job = scheduler.get_job(job_id)
        if updated_job and hasattr(updated_job, 'next_run_time'):
            system_logger.info("任务触发器更新后的下次执行时间: %s - %s", job_id, updated_job.next_run_time)
        
        system_logger.info("内置任务触发器更新成功: %s", job_id)
        return APIResponse.success("触发器更新成功")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("更新任务触发器失败: %s", error_str)
        return APIResponse.error(f"更新任务触发器失败: {error_str}")  # type: ignore


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
            system_logger.info("构建 CronTrigger 参数: %s", cron_kwargs)
        except Exception:  # noqa: BLE001
            pass

        try:
            # 确保CronTrigger使用与调度器相同的时区
            cron_kwargs["timezone"] = "Asia/Shanghai"
            return CronTrigger(**cron_kwargs)
        except Exception as e:  # noqa: BLE001
            system_logger.error("CronTrigger 构建失败: %s", str(e))
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
            system_logger.error("IntervalTrigger 构建失败: %s", str(e))
            return None

    if trigger_type == "date":
        run_date = data.get("run_date")
        if not run_date:
            return None
        from datetime import datetime

        dt = None
        try:
            dt = datetime.fromisoformat(str(run_date))
        except Exception:  # noqa: BLE001
            try:
                dt = datetime.strptime(str(run_date), "%Y-%m-%dT%H:%M")
            except Exception:  # noqa: BLE001
                dt = None
        if dt is None:
            return None
        try:
            return DateTrigger(run_date=dt)
        except Exception as e:  # noqa: BLE001
            system_logger.error("DateTrigger 构建失败: %s", str(e))
            return None

    return None




# 辅助函数





