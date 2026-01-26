"""Health namespace (Phase 0 示例端点)."""

from __future__ import annotations

import time
from typing import ClassVar

from flask import request
from flask_restx import Namespace, fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required
from app.core.constants.system_constants import SuccessMessages
from app.services.health.health_checks_service import (
    check_cache_health as check_cache_health_service,
    check_database_health as check_database_health_service,
    check_ping,
    get_basic_health,
    get_system_uptime,
)
from app.settings import APP_VERSION
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

ns = Namespace("health", description="健康检查")


def check_database_health() -> dict[str, object]:
    """检查数据库健康状态."""
    result = check_database_health_service()
    is_ok = bool(result.get("healthy"))
    return {"healthy": is_ok, "status": "connected" if is_ok else "error"}


def check_cache_health() -> dict[str, object]:
    """检查缓存健康状态."""
    result = check_cache_health_service()
    is_ok = bool(result.get("healthy"))
    return {"healthy": is_ok, "status": "connected" if is_ok else "error"}


PingData = ns.model(
    "HealthPingData",
    {
        "status": fields.String(required=True, description="服务状态", example="ok"),
    },
)

PingSuccessEnvelope = make_success_envelope_model(ns, "HealthPingSuccessEnvelope", PingData)
ErrorEnvelope = get_error_envelope_model(ns)

BasicData = ns.model(
    "HealthBasicData",
    {
        "status": fields.String(required=True, description="服务状态", example="healthy"),
        "timestamp": fields.Float(required=True, description="时间戳(秒)"),
        "version": fields.String(required=True, description="版本号", example="1.4.0"),
    },
)

BasicSuccessEnvelope = make_success_envelope_model(ns, "HealthBasicSuccessEnvelope", BasicData)

HealthData = ns.model(
    "HealthCheckData",
    {
        "status": fields.String(required=True, description="整体状态", example="healthy"),
        "database": fields.String(required=True, description="数据库状态", example="connected"),
        "redis": fields.String(required=True, description="缓存状态", example="connected"),
        "timestamp": fields.String(required=True, description="时间戳(ISO8601)"),
        "uptime": fields.String(required=True, description="运行时长"),
    },
)

HealthSuccessEnvelope = make_success_envelope_model(ns, "HealthCheckSuccessEnvelope", HealthData)

CacheHealthData = ns.model(
    "HealthCacheData",
    {
        "healthy": fields.Boolean(required=True, description="缓存服务是否健康"),
        "status": fields.String(required=True, description="connected/error"),
    },
)

CacheHealthSuccessEnvelope = make_success_envelope_model(ns, "HealthCacheSuccessEnvelope", CacheHealthData)

HealthComponentData = ns.model(
    "HealthComponentData",
    {
        "healthy": fields.Boolean(required=True),
        "status": fields.String(required=False),
    },
)

HealthDetailedComponentsData = ns.model(
    "HealthDetailedComponentsData",
    {
        "database": fields.Nested(HealthComponentData),
        "cache": fields.Nested(HealthComponentData),
        "system": fields.Nested(HealthComponentData),
    },
)

HealthDetailedData = ns.model(
    "HealthDetailedData",
    {
        "status": fields.String(required=True),
        "timestamp": fields.String(required=True, description="ISO8601 时间戳"),
        "version": fields.String(required=True),
        "components": fields.Nested(HealthDetailedComponentsData),
    },
)

HealthDetailedSuccessEnvelope = make_success_envelope_model(ns, "HealthDetailedSuccessEnvelope", HealthDetailedData)


@ns.route("/ping")
class HealthPingResource(BaseResource):
    """健康检查 Ping 资源."""

    @ns.response(200, "OK", PingSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """执行 Ping 健康检查."""

        def _execute():
            return self.success(data=check_ping(), message="健康检查成功")

        return self.safe_call(
            _execute,
            module="health",
            action="ping",
            public_error="健康检查失败",
            context={"route": "api_v1.health.ping"},
        )


@ns.route("/basic")
class HealthBasicResource(BaseResource):
    """基础健康检查资源."""

    @ns.response(200, "OK", BasicSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取基础健康状态."""
        return self.safe_call(
            lambda: self.success(
                data=get_basic_health(),
                message="服务运行正常",
            ),
            module="health",
            action="health_check",
            public_error="健康检查失败",
        )


@ns.route("")
class HealthCheckResource(BaseResource):
    """健康检查资源."""

    @ns.response(200, "OK", HealthSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取健康检查结果."""

        def _execute():
            start_time = time.time()

            db_result = check_database_health()
            raw_db_status = db_result.get("status")
            db_status = str(raw_db_status) if raw_db_status is not None else "error"

            cache_result = check_cache_health()
            raw_redis_status = cache_result.get("status")
            redis_status = str(raw_redis_status) if raw_redis_status is not None else "error"

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

            return self.success(data=result, message=SuccessMessages.OPERATION_SUCCESS)

        return self.safe_call(
            _execute,
            module="health",
            action="get_health",
            public_error="健康检查失败",
        )


def check_system_health() -> dict[str, object]:
    """检查系统健康状态."""
    return {"healthy": True, "status": "ok"}


@ns.route("/cache")
class HealthCacheResource(BaseResource):
    """缓存健康检查资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", CacheHealthSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取缓存健康状态."""

        def _execute():
            result = check_cache_health()
            return self.success(
                data=result,
                message="缓存健康检查成功",
            )

        return self.safe_call(
            _execute,
            module="health",
            action="get_health_cache",
            public_error="缓存健康检查失败",
        )


@ns.route("/detailed")
class HealthDetailedResource(BaseResource):
    """详细健康检查资源."""

    @ns.response(200, "OK", HealthDetailedSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取详细健康检查结果."""

        def _execute():
            components = {
                "database": check_database_health(),
                "cache": check_cache_health(),
                "system": check_system_health(),
            }

            overall_healthy = all(bool(component.get("healthy")) for component in components.values())
            status = "healthy" if overall_healthy else "unhealthy"

            return self.success(
                data={
                    "status": status,
                    "timestamp": time_utils.now_china().isoformat(),
                    "version": APP_VERSION,
                    "components": components,
                },
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="health",
            action="get_health_detailed",
            public_error="健康检查失败",
        )
