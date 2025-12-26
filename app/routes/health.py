"""鲸落 - 健康检查路由."""

import time

from flask import Blueprint, request
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError

from app.constants.system_constants import SuccessMessages
from app.repositories.health_repository import HealthRepository
from app.services.cache_service import CACHE_EXCEPTIONS, CacheService, cache_service
from app.services.health.health_checks_service import (
    check_cache_health,
    check_database_health,
    check_system_health,
    get_system_uptime,
)
from app.types import RouteReturn
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

# 创建蓝图
health_bp = Blueprint("health", __name__)

DATABASE_HEALTH_EXCEPTIONS: tuple[type[BaseException], ...] = (SQLAlchemyError,)
CACHE_HEALTH_EXCEPTIONS: tuple[type[BaseException], ...] = (*CACHE_EXCEPTIONS, ConnectionError)


def _get_cache_service() -> CacheService | None:
    """返回已初始化的缓存服务实例."""
    return cache_service


@health_bp.route("/api/basic")
def health_check() -> RouteReturn:
    """基础健康检查.

    Returns:
        JSON 响应,包含服务状态和版本信息.

    Raises:
        SystemError: 当健康检查失败时抛出.

    """
    return safe_route_call(
        lambda: jsonify_unified_success(
            data={"status": "healthy", "timestamp": time.time(), "version": "1.0.7"},
            message="服务运行正常",
        ),
        module="health",
        action="health_check",
        public_error="健康检查失败",
    )


@health_bp.route("/api/detailed")
def detailed_health_check() -> RouteReturn:
    """详细健康检查.

    检查数据库、缓存和系统资源的健康状态.

    Returns:
        JSON 响应,包含各组件的详细健康状态.

    Raises:
        SystemError: 当健康检查失败时抛出.

    """

    def _execute() -> RouteReturn:
        db_status = check_database_health()
        cache_status = check_cache_health()
        system_status = check_system_health()
        overall_status = (
            "healthy"
            if all(
                [
                    db_status["healthy"],
                    cache_status["healthy"],
                    system_status["healthy"],
                ],
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

    return safe_route_call(
        _execute,
        module="health",
        action="detailed_health_check",
        public_error="详细健康检查失败",
    )


@health_bp.route("/api/health")
def get_health() -> RouteReturn:
    """健康检查(供外部监控使用).

    快速检查数据库和 Redis 连接状态,适用于监控系统.

    Returns:
        JSON 响应,包含各组件的连接状态和系统运行时间.

    """
    start_time = time.time()

    # 检查数据库状态
    db_status = "connected"
    try:
        HealthRepository.ping_database()
    except DATABASE_HEALTH_EXCEPTIONS:
        db_status = "error"

    # 检查Redis状态
    redis_status = "connected"
    manager = _get_cache_service()
    try:
        redis_status = "connected" if manager and manager.health_check() else "error"
    except CACHE_HEALTH_EXCEPTIONS:
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
def get_cache_health() -> RouteReturn:
    """缓存服务健康检查.

    Returns:
        JSON 响应,包含缓存健康状态.

    Raises:
        SystemError: 当健康检查失败时抛出.

    """

    def _execute() -> RouteReturn:
        manager = _get_cache_service()
        if manager is None:
            return jsonify_unified_success(data={"healthy": False, "status": "未配置缓存"}, message="缓存未启用")

        is_healthy = manager.health_check()
        status_text = "正常" if is_healthy else "异常"
        data = {"healthy": is_healthy, "status": status_text}
        return jsonify_unified_success(data=data, message="缓存健康检查完成")

    return safe_route_call(
        _execute,
        module="health",
        action="get_cache_health",
        public_error="缓存健康检查失败",
    )
