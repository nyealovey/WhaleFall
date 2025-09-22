
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
            # 检查任务状态
            is_paused = job.next_run_time is None
            is_builtin = job.id in ["sync_accounts", "cleanup_logs"]

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
                "is_paused": is_paused,
                "is_builtin": is_builtin,
                "status": "paused" if is_paused else "active",
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
        builtin_tasks = ["sync_accounts", "cleanup_logs"]
        is_builtin = job_id in builtin_tasks

        # 构建新的触发器
        if "trigger_type" in data:
            trigger = _build_trigger(data)
            if not trigger:
                return APIResponse.error("无效的触发器配置", code=400)  # type: ignore

            if is_builtin:
                # 内置任务：只能更新触发器
                scheduler.modify_job(job_id, trigger=trigger)
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


@scheduler_bp.route("/api/jobs/<job_id>", methods=["DELETE"])
@login_required  # type: ignore
@scheduler_manage_required  # type: ignore
def delete_job(job_id: str) -> Response:
    """删除定时任务"""
    try:
        # 检查是否为内置任务
        builtin_tasks = ["sync_accounts", "cleanup_logs"]
        if job_id in builtin_tasks:
            return APIResponse.error("内置任务无法删除", code=403)  # type: ignore

        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)  # type: ignore

        scheduler.remove_job(job_id)
        system_logger.info("任务删除成功: {job_id}")
        return APIResponse.success("任务删除成功")  # type: ignore

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("删除任务失败: %s", error_str)
        return APIResponse.error(f"删除任务失败: {error_str}")  # type: ignore


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


def _get_task_function(func_name: str) -> Callable[..., Any] | None:
    """获取任务函数"""
    from app.tasks import cleanup_old_logs, sync_accounts

    # 任务函数映射
    task_functions = {
        "cleanup_old_logs": cleanup_old_logs,
        "sync_accounts": sync_accounts,
    }

    return task_functions.get(func_name)


def _create_dynamic_task_function(job_id: str, code: str) -> Callable[..., Any] | None:
    """创建动态任务函数"""
    try:
        import os
        import sys

        # 创建动态任务目录
        dynamic_tasks_dir = "userdata/dynamic_tasks"
        os.makedirs(dynamic_tasks_dir, exist_ok=True)

        # 生成任务文件路径
        task_file = os.path.join(dynamic_tasks_dir, f"{job_id}.py")

        # 创建完整的任务代码
        full_code = f'''"""
动态任务: {job_id}
创建时间: {now().isoformat()}
"""

from app import create_app, db

{code}

def task_wrapper():
    """任务包装器"""
    try:
        system_logger.info("开始执行动态任务: {job_id}")
        result = execute_task()
        system_logger.info("动态任务 {job_id} 执行完成: {{result}}")
        return result
    except Exception as e:
        system_logger.error("动态任务 {job_id} 执行失败: {{e}}")
        return f"任务执行失败: {{e}}"
'''

        # 保存任务文件
        with open(task_file, "w", encoding="utf-8") as f:
            f.write(full_code)

        # 将动态任务目录添加到Python路径
        if dynamic_tasks_dir not in sys.path:
            sys.path.insert(0, dynamic_tasks_dir)

        # 动态导入模块
        module_name = job_id
        spec = importlib.util.spec_from_file_location(module_name, task_file)
        if spec is None or spec.loader is None:
            system_logger.error("无法创建模块规范: {module_name}")
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 返回模块中的task_wrapper函数
        return getattr(module, "task_wrapper", None)

    except Exception as e:
        error_str = str(e) if e else "未知错误"
        system_logger.error("创建动态任务函数失败: %s", error_str)
        return None


def _build_trigger(
    data: dict[str, Any],
) -> CronTrigger | IntervalTrigger | DateTrigger | None:
    """构建触发器"""
    trigger_type = data.get("trigger_type")

    if trigger_type == "cron":
        return CronTrigger(
            year=data.get("year"),
            month=data.get("month"),
            day=data.get("day"),
            week=data.get("week"),
            day_of_week=data.get("day_of_week"),
            hour=data.get("cron_hour") or data.get("hour"),
            minute=data.get("cron_minute") or data.get("minute"),
            second=data.get("cron_second") or data.get("second"),
        )
    if trigger_type == "interval":
        # 过滤掉None值
        kwargs = {}
        for key in ["weeks", "days", "hours", "minutes", "seconds"]:
            value = data.get(key)
            if value is not None and value > 0:
                kwargs[key] = value

        if not kwargs:
            return None

        return IntervalTrigger(**kwargs)
    if trigger_type == "date":
        run_date = data.get("run_date")
        if run_date:
            from datetime import datetime

            return DateTrigger(run_date=datetime.fromisoformat(run_date))

    return None
