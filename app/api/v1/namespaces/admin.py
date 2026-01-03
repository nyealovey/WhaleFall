"""Admin namespace (misc)."""

from __future__ import annotations

from flask import current_app
from flask_restx import Namespace, fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource

ns = Namespace("admin", description="主路由/应用信息")

ErrorEnvelope = get_error_envelope_model(ns)

AppInfoData = ns.model(
    "AppInfoData",
    {
        "app_name": fields.String(required=True, description="应用名称", example="鲸落"),
        "app_version": fields.String(required=True, description="版本号", example="1.3.6"),
    },
)

AppInfoSuccessEnvelope = make_success_envelope_model(ns, "AppInfoSuccessEnvelope", AppInfoData)


@ns.route("/app-info")
class AdminAppInfoResource(BaseResource):
    """应用信息资源."""

    @ns.response(200, "OK", AppInfoSuccessEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取应用信息."""
        app_name = current_app.config.get("APP_NAME") or "鲸落"
        app_version = current_app.config.get("APP_VERSION") or "unknown"
        return self.success(
            data={"app_name": app_name, "app_version": app_version},
            message="获取应用信息成功",
        )
