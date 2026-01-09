"""健康检查 Service.

职责:
- 组织基础设施探活(数据库/缓存/系统资源)
- 不做 Response、不 commit
"""

from __future__ import annotations

import time

import psutil
from sqlalchemy.exc import SQLAlchemyError

from app import app_start_time, cache
from app.constants import TimeConstants
from app.repositories.health_repository import HealthRepository
from app.services.cache_service import CACHE_EXCEPTIONS
from app.settings import APP_VERSION
from app.utils.route_safety import log_with_context
from app.utils.time_utils import time_utils

RESOURCE_USAGE_THRESHOLD = 90

DATABASE_HEALTH_EXCEPTIONS: tuple[type[BaseException], ...] = (SQLAlchemyError,)
CACHE_HEALTH_EXCEPTIONS: tuple[type[BaseException], ...] = (*CACHE_EXCEPTIONS, ConnectionError)
SYSTEM_HEALTH_EXCEPTIONS: tuple[type[BaseException], ...] = (psutil.Error, OSError, ValueError)
UPTIME_EXCEPTIONS: tuple[type[BaseException], ...] = (AttributeError, TypeError, ValueError)


def check_ping() -> dict[str, str]:
    """Ping 探活."""
    return {"status": "ok"}


def get_basic_health(*, version: str = APP_VERSION) -> dict[str, object]:
    """获取基础健康状态."""
    return {"status": "healthy", "timestamp": time.time(), "version": version}


def check_database_health() -> dict:
    """检查数据库健康状态."""
    try:
        start_time = time.time()
        HealthRepository.ping_database()
        response_time = (time.time() - start_time) * 1000  # 毫秒

        return {
            "healthy": True,
            "response_time_ms": round(response_time, 2),
            "status": "connected",
        }
    except DATABASE_HEALTH_EXCEPTIONS as exc:
        log_with_context(
            "warning",
            "数据库健康检查失败",
            module="health",
            action="check_database_health",
            extra={"error_message": str(exc)},
            include_actor=False,
        )
        return {"healthy": False, "error": str(exc), "status": "disconnected"}


def check_cache_health() -> dict:
    """检查缓存健康状态."""
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
    except CACHE_HEALTH_EXCEPTIONS as exc:
        log_with_context(
            "warning",
            "缓存健康检查失败",
            module="health",
            action="check_cache_health",
            extra={"error_message": str(exc)},
            include_actor=False,
        )
        return {"healthy": False, "error": str(exc), "status": "disconnected"}


def check_system_health() -> dict:
    """检查系统资源健康状态."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100

        healthy = all(
            [
                cpu_percent < RESOURCE_USAGE_THRESHOLD,
                memory_percent < RESOURCE_USAGE_THRESHOLD,
                disk_percent < RESOURCE_USAGE_THRESHOLD,
            ],
        )

        return {
            "healthy": healthy,
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory_percent, 2),
            "disk_percent": round(disk_percent, 2),
            "status": "healthy" if healthy else "warning",
        }
    except SYSTEM_HEALTH_EXCEPTIONS as exc:
        log_with_context(
            "warning",
            "系统健康检查失败",
            module="health",
            action="check_system_health",
            extra={"error_message": str(exc)},
            include_actor=False,
        )
        return {"healthy": False, "error": str(exc), "status": "error"}


def get_system_uptime() -> str:
    """获取应用运行时间."""
    try:
        current_time = time_utils.now_china()
        uptime = current_time - app_start_time
    except UPTIME_EXCEPTIONS:
        return "未知"

    days = uptime.days
    hours, remainder = divmod(uptime.seconds, TimeConstants.ONE_HOUR)
    minutes, _ = divmod(remainder, 60)

    return f"{days}天 {hours}小时 {minutes}分钟"
