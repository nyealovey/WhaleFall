
"""
鲸落 - 健康检查路由
"""

import time

import psutil
from flask import Blueprint, Response, request
from flask_login import login_required

from app import cache, db
from app.constants import TimeConstants, TaskStatus
from app.constants.system_constants import SuccessMessages
from app.errors import SystemError
from app.scheduler import get_scheduler
from app.services.cache_service import cache_manager
from app.services.scheduler_health_service import scheduler_health_service
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
from app.utils.decorators import scheduler_view_required
from app.utils.time_utils import time_utils

# 创建蓝图
health_bp = Blueprint("health", __name__)


@health_bp.route("/api/basic")
def health_check() -> Response:
    """基础健康检查"""
    try:
        return jsonify_unified_success(
            data={"status": "healthy", "timestamp": time.time(), "version": "1.0.7"},
            message="服务运行正常",
        )
    except Exception as exc:
        log_error("健康检查失败", module="health", error=str(exc))
        raise SystemError("健康检查失败") from exc


@health_bp.route("/api/detailed")
def detailed_health_check() -> Response:
    """详细健康检查"""
    try:
        # 检查数据库连接
        db_status = check_database_health()

        # 检查Redis连接
        cache_status = check_cache_health()

        # 检查系统资源
        system_status = check_system_health()

        # 综合状态
        overall_status = (
            "healthy"
            if all(
                [
                    db_status["healthy"],
                    cache_status["healthy"],
                    system_status["healthy"],
                ]
            )
            else "unhealthy"
        )

        log_info(
            "详细健康检查结果",
            module="health",
            status=overall_status,
            database=db_status,
            cache=cache_status,
            system=system_status,
        )

        return jsonify_unified_success(
            data={
                "status": overall_status,
                "timestamp": time.time(),
                "version": "1.1.2",
                "components": {
                    "database": db_status,
                    "cache": cache_status,
                    "system": system_status,
                },
            },
            message="详细健康检查完成",
        )

    except Exception as exc:
        log_error("详细健康检查失败", module="health", error=str(exc))
        raise SystemError("详细健康检查失败") from exc


@health_bp.route("/api/health")
def api_health() -> Response:
    """健康检查（供外部监控使用）"""
    start_time = time.time()

    # 检查数据库状态
    db_status = "connected"
    try:
        from sqlalchemy import text

        db.session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # 检查Redis状态
    redis_status = "connected"
    try:
        if cache_manager and cache_manager.health_check():
            redis_status = "connected"
        else:
            redis_status = "error"
    except Exception:
        redis_status = "error"

    overall_status = "healthy" if db_status == "connected" and redis_status == "connected" else "unhealthy"
    result = {
        "status": overall_status,
        "database": db_status,
        "redis": redis_status,
        "timestamp": time_utils.now_china().isoformat(),
        "uptime": get_system_uptime(),
    }

    duration = (time.time() - start_time) * 1000
    log_info(
        "健康检查API调用",
        module="health",
        ip_address=request.remote_addr,
        duration_ms=duration,
    )

    return jsonify_unified_success(
        data=result,
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@health_bp.route("/api/cache")
@login_required
def api_cache_health() -> Response:
    """缓存服务健康检查"""
    try:
        is_healthy = cache_manager.health_check()
    except Exception as exc:
        log_error("缓存健康检查失败", module="cache", error=str(exc))
        raise SystemError("缓存健康检查失败") from exc

    status_text = "正常" if is_healthy else "异常"
    data = {"healthy": is_healthy, "status": status_text}
    return jsonify_unified_success(data=data, message="缓存健康检查完成")


@health_bp.route("/api/scheduler")
@login_required
@scheduler_view_required
def api_scheduler_health() -> Response:
    """调度器健康检查"""
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


def check_database_health() -> dict:
    """检查数据库健康状态"""
    try:
        start_time = time.time()
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
        response_time = (time.time() - start_time) * 1000  # 毫秒

        return {
            "healthy": True,
            "response_time_ms": round(response_time, 2),
            "status": "connected",
        }
    except Exception as exc:
        log_error("数据库健康检查失败", module="health", error=str(exc))
        return {"healthy": False, "error": str(exc), "status": "disconnected"}


def check_cache_health() -> dict:
    """检查缓存健康状态"""
    try:
        start_time = time.time()
        cache.set("health_check", "ok", timeout=10)
        result = cache.get("health_check")
        response_time = (time.time() - start_time) * 1000  # 毫秒

        return {
            "healthy": result == "ok",
            "response_time_ms": round(response_time, 2),
            "status": "connected" if result == "ok" else "error",
        }
    except Exception as exc:
        log_error("缓存健康检查失败", module="health", error=str(exc))
        return {"healthy": False, "error": str(exc), "status": "disconnected"}


def check_system_health() -> dict:
    """检查系统资源健康状态"""
    try:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)

        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # 磁盘使用率
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100

        # 判断是否健康
        healthy = all(
            [
                cpu_percent < 90,  # CPU使用率低于90%
                memory_percent < 90,  # 内存使用率低于90%
                disk_percent < 90,  # 磁盘使用率低于90%
            ]
        )

        return {
            "healthy": healthy,
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory_percent, 2),
            "disk_percent": round(disk_percent, 2),
            "status": "healthy" if healthy else "warning",
        }
    except Exception as exc:
        log_error("系统健康检查失败", module="health", error=str(exc))
        return {"healthy": False, "error": str(exc), "status": "error"}


def get_system_uptime() -> "str | None":
    """获取应用运行时间"""
    try:
        from app import app_start_time

        current_time = time_utils.now_china()
        uptime = current_time - app_start_time

        days = uptime.days
        hours, remainder = divmod(uptime.seconds, TimeConstants.ONE_HOUR)
        minutes, _ = divmod(remainder, 60)

        return f"{days}天 {hours}小时 {minutes}分钟"
    except Exception:
        return "未知"
