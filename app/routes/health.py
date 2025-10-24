
"""
鲸落 - 健康检查路由
"""

import time

import psutil
from flask import Blueprint, Response, request

from app import cache, db
from app.constants.system_constants import SuccessMessages
from app.errors import SystemError
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
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
        from app.services.cache_manager import cache_manager

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
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        return f"{days}天 {hours}小时 {minutes}分钟"
    except Exception:
        return "未知"
