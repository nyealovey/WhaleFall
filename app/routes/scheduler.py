
"""
定时任务管理路由
"""

from typing import Any
from datetime import datetime
from flask import Blueprint, Response, render_template, request, current_app, jsonify
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
                            system_logger.warning(f"fields列表长度不足: {len(fields)}")
                            trigger_args['second'] = '0'
                            trigger_args['minute'] = '0'
                            trigger_args['hour'] = '0'
                            trigger_args['day'] = '*'
                            trigger_args['month'] = '*'
                            trigger_args['day_of_week'] = '*'
                            trigger_args['year'] = ''
                    else:
                        # 如果既不是字典也不是列表，使用默认值
                        system_logger.warning(f"fields不是字典或列表类型: {type(fields)}")
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

@scheduler_bp.route("/api/health")
@login_required
@scheduler_view_required
def get_scheduler_health():
    """获取调度器健康状态"""
    try:
        scheduler = get_scheduler()
        
        # 基本状态检查
        is_running = scheduler.running if scheduler else False
        jobs = scheduler.get_jobs() if scheduler else []
        
        # 统计任务状态
        running_jobs = [job for job in jobs if job.next_run_time is not None]
        paused_jobs = [job for job in jobs if job.next_run_time is None]
        
        # 检查调度器线程状态 - 检查调度器是否真正运行
        thread_alive = scheduler and scheduler.running
        
        # 检查作业存储状态 - 如果能获取到任务说明存储正常
        jobstore_accessible = len(jobs) > 0
        
        # 检查执行器状态 - 检查执行器是否可用
        executor_working = False
        try:
            if scheduler and hasattr(scheduler, 'executors'):
                default_executor = scheduler.executors.get('default')
                if default_executor:
                    # 检查执行器是否可用
                    executor_working = True
        except Exception as e:
            current_app.logger.warning(f"执行器检查失败: {e}")
        
        # 检查任务执行能力 - 检查是否有任务在等待执行
        has_pending_jobs = len(running_jobs) > 0
        current_app.logger.info(f"健康检查: 调度器运行={is_running}, 线程={thread_alive}, 存储={jobstore_accessible}, 执行器={executor_working}, 待执行任务={len(running_jobs)}")
        
        # 计算健康状态
        health_score = 0
        if is_running:
            health_score += 30
        if thread_alive:
            health_score += 25
        if jobstore_accessible:
            health_score += 25
        if executor_working:
            health_score += 20
        
        # 如果有待执行任务但执行器不工作，降低分数
        if has_pending_jobs and not executor_working:
            health_score = max(0, health_score - 30)
        
        # 确定健康状态
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
        
        health_data = {
            "status": status,
            "status_text": status_text,
            "status_color": status_color,
            "health_score": health_score,
            "scheduler_running": is_running,
            "thread_alive": thread_alive,
            "jobstore_accessible": jobstore_accessible,
            "executor_working": executor_working,
            "total_jobs": len(jobs),
            "running_jobs": len(running_jobs),
            "paused_jobs": len(paused_jobs),
            "last_check": datetime.now().isoformat()
        }
        
        return jsonify({
            "success": True,
            "data": health_data
        })
        
    except Exception as e:
        current_app.logger.error(f"获取调度器健康状态失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "data": {
                "status": "error",
                "status_text": "检查失败",
                "status_color": "danger",
                "health_score": 0,
                "last_check": datetime.now().isoformat()
            }
        })



