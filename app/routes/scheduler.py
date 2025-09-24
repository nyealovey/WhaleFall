
"""
定时任务管理路由
"""

import importlib.util
from collections.abc import Callable
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from flask import Blueprint, Response, render_template, request
from flask_login import login_required  # type: ignore

from app.scheduler import get_scheduler
from app.utils.api_response import APIResponse
from app.utils.decorators import scheduler_manage_required, scheduler_view_required
from app.utils.structlog_config import get_system_logger
from app.utils.timezone import now

# 常量: 内置任务ID集合（统一前后端识别）
BUILTIN_TASK_IDS: set[str] = {"cleanup_logs", "sync_accounts"}

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
                
                if isinstance(job.trigger, CronTrigger):
                    trigger_type = "cron"
                    # CronTrigger通过fields属性访问，添加异常处理
                    try:
                        # CronTrigger的fields是一个列表，按顺序包含：year, month, day, week, day_of_week, hour, minute, second
                        fields = job.trigger.fields
                        trigger_args = {
                            "minute": str(fields[6]) if len(fields) > 6 and fields[6] is not None else "*",
                            "hour": str(fields[5]) if len(fields) > 5 and fields[5] is not None else "*",
                            "day": str(fields[2]) if len(fields) > 2 and fields[2] is not None else "*",
                            "month": str(fields[1]) if len(fields) > 1 and fields[1] is not None else "*",
                            "day_of_week": str(fields[4]) if len(fields) > 4 and fields[4] is not None else "*",
                        }
                        # 扩展：补充 second 与 year 字段，并提供标准 7 段 cron_expression 便于前端统一解析
                        try:
                            second_str = str(fields[7]) if len(fields) > 7 and fields[7] is not None else "*"
                        except Exception:
                            second_str = "*"
                        try:
                            year_str = str(fields[0]) if len(fields) > 0 and fields[0] is not None else "*"
                        except Exception:
                            year_str = "*"

                        trigger_args["second"] = second_str
                        trigger_args["year"] = year_str

                        # 统一构造 7 段表达式：second minute hour day month day_of_week year
                        cron_expression = f"{second_str} {trigger_args.get('minute', '*')} {trigger_args.get('hour', '*')} {trigger_args.get('day', '*')} {trigger_args.get('month', '*')} {trigger_args.get('day_of_week', '*')} {year_str}"
                        trigger_args["cron_expression"] = cron_expression
                        system_logger.info(f"CronTrigger字段: {trigger_args}")
                    except Exception as trigger_error:
                        system_logger.error(f"访问CronTrigger字段失败: {trigger_error}")
                        # 使用默认值
                        trigger_args = {
                            "minute": "*",
                            "hour": "*", 
                            "day": "*",
                            "month": "*",
                            "day_of_week": "*",
                        }
                elif isinstance(job.trigger, IntervalTrigger):
                    trigger_type = "interval"
                    delta = job.trigger.interval
                    trigger_args = {
                        "weeks": delta.days // 7,
                        "days": delta.days % 7,
                        "hours": delta.seconds // 3600,
                        "minutes": (delta.seconds % 3600) // 60,
                        "seconds": delta.seconds % 60,
                    }
                elif isinstance(job.trigger, DateTrigger):
                    trigger_type = "date"
                    trigger_args = {"run_date": job.trigger.run_date.isoformat()}
                else:
                    system_logger.warning(f"未知触发器类型: {type(job.trigger)}")
                    
            except Exception as job_error:
                system_logger.error(f"处理任务 {job.id} 时出错: {job_error}")
                # 使用默认值继续处理
                trigger_type = "unknown"
                trigger_args = {}

            # 模拟任务状态
            state = "STATE_PAUSED"
            if scheduler.running and not is_paused:
                state = "STATE_RUNNING"

            job_info = {
                "id": job.id,
                "name": job.name,
                "description": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "last_run_time": None,
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


@scheduler_bp.route("/api/jobs", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def create_job() -> Response:
    """创建新的定时任务"""
    try:
        data = request.get_json()
        system_logger.info("创建任务请求数据: %s", data)

        # 验证必需字段
        required_fields = ["id", "name", "code", "trigger_type"]
        for field in required_fields:
            if field not in data:
                system_logger.error("缺少必需字段: %s", field)
                return APIResponse.error(f"缺少必需字段: {field}", code=400)  # type: ignore

        # 构建触发器
        trigger = _build_trigger(data)
        if not trigger:
            return APIResponse.error("无效的触发器配置", code=400)  # type: ignore
        # 记录触发器构建结果
        system_logger.info("创建任务-触发器构建完成: %s", str(trigger))

        # 验证代码格式
        code = data["code"].strip()
        if not code:
            return APIResponse.error("任务代码不能为空", code=400)  # type: ignore

        # 检查代码是否包含execute_task函数
        if "def execute_task():" not in code:
            return APIResponse.error("代码必须包含 'def execute_task():' 函数", code=400)  # type: ignore

        # 创建动态任务函数
        task_func = _create_dynamic_task_function(data["id"], code)
        if not task_func:
            return APIResponse.error("代码格式错误，请检查语法", code=400)  # type: ignore

        # 添加任务
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        # 直接使用函数对象（不覆盖现有任务）
        job = scheduler.add_job(
            func=task_func,
            trigger=trigger,
            id=data["id"],
            name=data["name"],
            args=[],
            kwargs={},
        )

        system_logger.info("任务创建成功: %s", job.id)
        return APIResponse.success(data={"job_id": job.id}, message="任务创建成功")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("创建任务失败: %s", error_str)
        return APIResponse.error("创建任务失败: {error_str}")  # type: ignore


@scheduler_bp.route("/api/jobs/<job_id>", methods=["PUT"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def update_job(job_id: str) -> Response:
    """更新定时任务"""
    try:
        data = request.get_json()

        # 检查任务是否存在
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        job = scheduler.get_job(job_id)
        if not job:
            return APIResponse.error("任务不存在", code=404)  # type: ignore

        # 检查是否为内置任务
        is_builtin = job_id in BUILTIN_TASK_IDS

        # 构建新的触发器
        if "trigger_type" in data:
            trigger = _build_trigger(data)
            if not trigger:
                return APIResponse.error("无效的触发器配置", code=400)  # type: ignore

            if is_builtin:
                # 内置任务：只能更新触发器
                scheduler.modify_job(job_id, trigger=trigger)
                # 手动触发调度器重新计算下次执行时间
                updated_job = scheduler.get_job(job_id)
                if updated_job and hasattr(updated_job, 'next_run_time'):
                    system_logger.info("任务触发器更新后的下次执行时间: %s - %s", job_id, updated_job.next_run_time)
                system_logger.info("内置任务触发器更新成功: %s", job_id)
                return APIResponse.success("触发器更新成功")  # type: ignore
            # 自定义任务：可以更新所有属性
            scheduler.modify_job(
                job_id,
                trigger=trigger,
                name=data.get("name", job.name),
                args=data.get("args", job.args),
                kwargs=data.get("kwargs", job.kwargs),
            )
            # 记录更新后的下次执行时间
            try:
                updated_job = scheduler.get_job(job_id)
                system_logger.info("任务更新后下次执行时间: %s - %s", job_id, getattr(updated_job, "next_run_time", None))
            except Exception as _log_err:
                system_logger.warning("记录任务更新的下次执行时间失败: %s", str(_log_err))
        else:
            if is_builtin:
                # 内置任务：不允许更新其他属性
                return APIResponse.error("内置任务只能修改触发器", code=403)  # type: ignore
            # 只更新其他属性
            scheduler.modify_job(
                job_id,
                name=data.get("name", job.name),
                args=data.get("args", job.args),
                kwargs=data.get("kwargs", job.kwargs),
            )

        system_logger.info("任务更新成功: %s", job_id)
        return APIResponse.success("任务更新成功")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("更新任务失败: %s", error_str)
        return APIResponse.error("更新任务失败: {error_str}")  # type: ignore


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
            if job_id in ["sync_accounts", "cleanup_logs"]:
                # 对于sync_accounts任务，手动执行时传递manual_run=True
                result = job.func(manual_run=True) if job_id == "sync_accounts" else job.func(*job.args, **job.kwargs)
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


@scheduler_bp.route("/api/jobs/by-func", methods=["POST"])  # type: ignore[misc]
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def create_job_by_func() -> Response:
    """通过内置任务函数创建定时任务

    请求体示例:
        {
            "name": "账户同步",
            "func": "sync_accounts",            # 或 "cleanup_old_logs" 等受支持的函数
            "trigger_type": "cron",            # cron | interval | date
            # cron: 可提交 cron_expression 或 cron_* 单字段（与 _build_trigger 兼容）
            # interval: 提交 minutes/seconds（或 weeks/days/hours 等）
            # date: 提交 run_date（ISO8601 或 datetime-local 格式字符串）
            "id": "可选-自定义任务ID"
        }

    Returns:
        Response: 标准化的 JSON 响应，成功时返回 {"job_id": "..."}
    """
    try:
        data = request.get_json() or {}
        system_logger.info("按函数创建任务请求数据: %s", data)

        # 基础字段校验
        required_fields = ["name", "func", "trigger_type"]
        for field in required_fields:
            if field not in data:
                return APIResponse.error(f"缺少必需字段: {field}", code=400)  # type: ignore

        # 构建触发器（兼容 cron/interval/date）
        trigger = _build_trigger(data)
        if not trigger:
            return APIResponse.error("无效的触发器配置", code=400)  # type: ignore

        # 解析任务函数
        func_name = str(data.get("func"))
        task_func = _get_task_function(func_name)
        if task_func is None:
            return APIResponse.error(f"未知的执行函数: {func_name}", code=400)  # type: ignore

        # 调度器状态检查
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        # 生成任务ID（未传入则使用 函数名_时间戳）
        job_id = data.get("id")
        if not job_id:
            import time as _time
            job_id = f"{func_name}_{int(_time.time())}"

        # 创建任务
        job = scheduler.add_job(
            func=task_func,
            trigger=trigger,
            id=job_id,
            name=str(data.get("name")),
            args=[],
            kwargs={},
        )

        system_logger.info("按函数创建任务成功: %s", job.id)
        return APIResponse.success(data={"job_id": job.id}, message="任务创建成功")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("按函数创建任务失败: %s", error_str)
        return APIResponse.error(f"创建任务失败: {error_str}")  # type: ignore


@scheduler_bp.route("/api/jobs/<job_id>", methods=["DELETE"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def delete_job(job_id: str) -> Response:
    """删除指定定时任务

    Args:
        job_id (str): 任务ID。

    Returns:
        Response: 标准化的JSON响应。
    """
    try:
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        job = scheduler.get_job(job_id)
        if not job:
            return APIResponse.error("任务不存在", code=404)  # type: ignore

        # 保护内置任务，避免误删
        if job_id in BUILTIN_TASK_IDS:
            return APIResponse.error("内置任务不允许删除", code=403)  # type: ignore

        scheduler.remove_job(job_id)
        system_logger.info("任务已删除: %s", job_id)
        return APIResponse.success(message="任务已删除")  # type: ignore
    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("删除任务失败: %s - %s", job_id, error_str)
        return APIResponse.error(f"删除任务失败: {error_str}")  # type: ignore


@scheduler_bp.route("/api/jobs/purge", methods=["POST"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def purge_jobs() -> Response:
    """批量清理任务，仅保留指定任务ID列表。

    请求体示例：
        {"keep_ids": ["cleanup_logs", "sync_accounts"], "include_builtin": false}

    说明：
        - keep_ids: 需要保留的任务ID列表；
        - include_builtin: 是否允许清理内置任务；默认 False（内置任务将始终保留）。

    Returns:
        Response: 标准化的JSON响应，包含删除的任务ID清单。
    """
    try:
        data = request.get_json(silent=True) or {}
        keep_ids = set(data.get("keep_ids", []) or [])
        include_builtin = bool(data.get("include_builtin", False))

        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        jobs = scheduler.get_jobs()
        deleted: list[str] = []
        skipped: list[str] = []

        for job in jobs:
            jid = job.id
            # 内置任务默认跳过
            if not include_builtin and jid in BUILTIN_TASK_IDS:
                skipped.append(jid)
                continue
            # 保留名单跳过
            if jid in keep_ids:
                skipped.append(jid)
                continue
            # 执行删除
            try:
                scheduler.remove_job(jid)
                deleted.append(jid)
                system_logger.info("批量清理-删除任务: %s", jid)
            except Exception as del_err:
                system_logger.error("批量清理-删除任务失败: %s - %s", jid, str(del_err))

        return APIResponse.success(
            data={"deleted": deleted, "kept": list(keep_ids), "skipped": skipped},
            message=f"已删除 {len(deleted)} 个任务",
        )  # type: ignore
    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("批量清理任务失败: %s", error_str)
        return APIResponse.error(f"批量清理任务失败: {error_str}")  # type: ignore


# 辅助函数

def _get_task_function(func_name: str) -> Callable[..., Any] | None:
    """根据名称获取任务函数。

    Args:
        func_name (str): 前端传入的函数名或其别名。

    Returns:
        Callable[..., Any] | None: 可调用任务函数，未知名称时返回 None。
    """
    # 延迟导入以避免循环依赖
    from app.tasks import cleanup_old_logs, sync_accounts  # type: ignore

    # 任务函数映射与别名
    task_functions: dict[str, Callable[..., Any]] = {
        # 标准名称
        "cleanup_old_logs": cleanup_old_logs,
        "sync_accounts": sync_accounts,
        # 别名兼容
        "cleanup_logs": cleanup_old_logs,  # 内置任务ID别名
        "sync_all_instances": sync_accounts,  # 前端下拉项兼容
    }

    return task_functions.get(func_name)


def _create_dynamic_task_function(job_id: str, code: str) -> Callable[..., Any] | None:
    """基于用户提供的代码创建动态任务函数。

    要求 code 中必须包含一个无参的 `def execute_task():` 函数。

    Args:
        job_id (str): 任务 ID，用于生成唯一模块文件名。
        code (str): 用户提交的 Python 代码片段。

    Returns:
        Callable[..., Any] | None: 返回可调用的任务包装器函数；失败时返回 None。
    """
    try:
        import os
        import sys

        # 动态任务代码保存目录
        dynamic_tasks_dir = os.path.join("userdata", "dynamic_tasks")
        os.makedirs(dynamic_tasks_dir, exist_ok=True)

        # 生成任务文件路径
        task_file = os.path.join(dynamic_tasks_dir, f"{job_id}.py")

        # 组合完整任务代码：包裹应用上下文，调用 execute_task
        full_code = f'''"""
动态任务: {job_id}
生成时间: {now().isoformat()}
"""
from app import create_app

{code}

def task_wrapper():
    """动态任务包装器：负责创建应用上下文并调用 execute_task。"""
    try:
        app = create_app()
        with app.app_context():
            return execute_task()
    except Exception as e:  # noqa: BLE001
        return f"任务执行失败: {e}"
'''

        # 写入文件
        with open(task_file, "w", encoding="utf-8") as f:
            f.write(full_code)

        # 将目录加入 Python 路径
        if dynamic_tasks_dir not in sys.path:
            sys.path.insert(0, dynamic_tasks_dir)

        # 使用 importlib 动态导入模块
        module_name = job_id
        spec = importlib.util.spec_from_file_location(module_name, task_file)
        if spec is None or spec.loader is None:
            system_logger.error("无法创建动态模块规范: %s", module_name)
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 提取包装器函数
        task_func = getattr(module, "task_wrapper", None)
        if callable(task_func):
            return task_func
        system_logger.error("动态模块缺少 task_wrapper: %s", module_name)
        return None
    except Exception as e:  # noqa: BLE001
        system_logger.error("创建动态任务函数失败: %s", str(e))
        return None


def _build_trigger(
    data: dict[str, Any],
) -> CronTrigger | IntervalTrigger | DateTrigger | None:
    """根据前端数据构建 APScheduler 触发器。

    支持三种类型：cron、interval、date。

    - cron: 支持 cron_expression（5/6/7 段）与单字段别名：
        cron_second/cron_minute/cron_hour/cron_day/cron_month/cron_weekday 及 year。
      若表达式与单字段同时提供，单字段优先。
    - interval: 接受 weeks/days/hours/minutes/seconds 的正整数。
    - date: 接受 run_date（ISO8601 或 datetime-local 格式）。

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
