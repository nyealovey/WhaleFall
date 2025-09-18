"""
泰摸鱼吧 - 健康检查路由
"""

import time

import psutil
from flask import Blueprint, Response

from app import cache, db
from app.utils.api_response import APIResponse
from app.utils.structlog_config import get_system_logger

# 创建蓝图
health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health_check() -> "Response":
    """基础健康检查"""
    try:
        return APIResponse.success(
            data={"status": "healthy", "timestamp": time.time(), "version": "1.0.0"},
            message="服务运行正常",
        )
    except Exception as e:
        system_logger = get_system_logger()
        system_logger.error("健康检查失败", module="health", exception=e)
        return APIResponse.server_error("健康检查失败")


@health_bp.route("/health/detailed")
def detailed_health_check() -> "Response":
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

        return APIResponse.success(
            data={
                "status": overall_status,
                "timestamp": time.time(),
                "version": "1.0.0",
                "components": {
                    "database": db_status,
                    "cache": cache_status,
                    "system": system_status,
                },
            },
            message="详细健康检查完成",
        )

    except Exception as e:
        system_logger = get_system_logger()
        system_logger.error("详细健康检查失败", module="health", exception=e)
        return APIResponse.server_error("详细健康检查失败")


def check_database_health() -> dict:
    """检查数据库健康状态"""
    try:
        start_time = time.time()
        db.session.execute("SELECT 1")
        response_time = (time.time() - start_time) * 1000  # 毫秒

        return {
            "healthy": True,
            "response_time_ms": round(response_time, 2),
            "status": "connected",
        }
    except Exception as e:
        system_logger = get_system_logger()
        system_logger.error("数据库健康检查失败", module="health", exception=e)
        return {"healthy": False, "error": str(e), "status": "disconnected"}


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
    except Exception as e:
        system_logger = get_system_logger()
        system_logger.error("缓存健康检查失败", module="health", exception=e)
        return {"healthy": False, "error": str(e), "status": "disconnected"}


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
    except Exception as e:
        system_logger = get_system_logger()
        system_logger.error("系统健康检查失败", module="health", exception=e)
        return {"healthy": False, "error": str(e), "status": "error"}


@health_bp.route("/health/readiness")
def readiness_check() -> "Response":
    """就绪检查 - 用于Kubernetes等容器编排"""
    try:
        # 检查关键服务是否就绪
        db_ready = check_database_health()["healthy"]
        cache_ready = check_cache_health()["healthy"]

        if db_ready and cache_ready:
            return APIResponse.success(data={"status": "ready"}, message="服务就绪")
        return APIResponse.error(message="服务未就绪", code=503)
    except Exception as e:
        system_logger = get_system_logger()
        system_logger.error("就绪检查失败", module="health", exception=e)
        return APIResponse.server_error("就绪检查失败")


@health_bp.route("/health/liveness")
def liveness_check() -> "Response":
    """存活检查 - 用于Kubernetes等容器编排"""
    try:
        # 简单的存活检查
        return APIResponse.success(data={"status": "alive"}, message="服务存活")
    except Exception as e:
        system_logger = get_system_logger()
        system_logger.error("存活检查失败", module="health", exception=e)
        return APIResponse.server_error("存活检查失败")
