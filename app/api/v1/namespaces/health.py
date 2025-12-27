"""Health namespace (Phase 0 示例端点)."""

from __future__ import annotations

import time

from flask import request
from flask_restx import Namespace, fields
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.constants.system_constants import SuccessMessages
from app.repositories.health_repository import HealthRepository
from app.services.cache_service import CACHE_EXCEPTIONS, CacheService, cache_service
from app.services.health.health_checks_service import get_system_uptime
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

ns = Namespace("health", description="健康检查")

DATABASE_HEALTH_EXCEPTIONS: tuple[type[BaseException], ...] = (SQLAlchemyError,)
CACHE_HEALTH_EXCEPTIONS: tuple[type[BaseException], ...] = (*CACHE_EXCEPTIONS, ConnectionError)


def _get_cache_service() -> CacheService | None:
    """返回已初始化的缓存服务实例."""
    return cache_service


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
        "version": fields.String(required=True, description="版本号", example="1.0.7"),
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


@ns.route("/ping")
class HealthPingResource(BaseResource):
    @ns.response(200, "OK", PingSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        return self.success({"status": "ok"}, message="健康检查成功")


@ns.route("/basic")
class HealthBasicResource(BaseResource):
    @ns.response(200, "OK", BasicSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        return self.safe_call(
            lambda: self.success(
                data={"status": "healthy", "timestamp": time.time(), "version": "1.0.7"},
                message="服务运行正常",
            ),
            module="health",
            action="health_check",
            public_error="健康检查失败",
        )


@ns.route("/health")
class HealthCheckResource(BaseResource):
    @ns.response(200, "OK", HealthSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            start_time = time.time()

            db_status = "connected"
            try:
                HealthRepository.ping_database()
            except DATABASE_HEALTH_EXCEPTIONS:
                db_status = "error"

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

            return self.success(data=result, message=SuccessMessages.OPERATION_SUCCESS)

        return self.safe_call(
            _execute,
            module="health",
            action="get_health",
            public_error="健康检查失败",
        )
