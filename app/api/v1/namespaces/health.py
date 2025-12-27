"""Health namespace (Phase 0 示例端点)."""

from __future__ import annotations

from flask_restx import Namespace, fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource

ns = Namespace("health", description="健康检查")

PingData = ns.model(
    "HealthPingData",
    {
        "status": fields.String(required=True, description="服务状态", example="ok"),
    },
)

PingSuccessEnvelope = make_success_envelope_model(ns, "HealthPingSuccessEnvelope", PingData)
ErrorEnvelope = get_error_envelope_model(ns)


@ns.route("/ping")
class HealthPingResource(BaseResource):
    @ns.response(200, "OK", PingSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        return self.success({"status": "ok"}, message="健康检查成功")
