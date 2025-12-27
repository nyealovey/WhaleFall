"""API v1 (Flask-RESTX).

该包仅承载对外 JSON API 的路由层与 OpenAPI 文档能力.
业务编排与数据访问仍复用既有 services/repositories.
"""

from __future__ import annotations

from typing import cast

from flask import Blueprint, Response, jsonify

from app.api.v1.api import WhaleFallApi
from app.api.v1.namespaces.accounts import ns as accounts_ns
from app.api.v1.namespaces.auth import ns as auth_ns
from app.api.v1.namespaces.common import ns as common_ns
from app.api.v1.namespaces.connections import ns as connections_ns
from app.api.v1.namespaces.credentials import ns as credentials_ns
from app.api.v1.namespaces.dashboard import ns as dashboard_ns
from app.api.v1.namespaces.health import ns as health_ns
from app.api.v1.namespaces.instances import ns as instances_ns
from app.api.v1.namespaces.tags import ns as tags_ns
from app.settings import Settings


def create_api_v1_blueprint(settings: Settings) -> Blueprint:
    """创建并配置 `/api/v1` Blueprint.

    Phase 0 目标:
    - Swagger UI: `/api/v1/docs`(可配置关闭)
    - OpenAPI JSON: `/api/v1/openapi.json`
    """
    blueprint = Blueprint("api_v1", __name__)

    docs_path = "/docs" if settings.api_v1_docs_enabled else cast(str, False)
    api = WhaleFallApi(
        blueprint,
        title=settings.app_name,
        version=settings.app_version,
        doc=docs_path,
    )

    api.add_namespace(auth_ns, path="/auth")
    api.add_namespace(health_ns, path="/health")
    api.add_namespace(common_ns, path="/common")
    api.add_namespace(connections_ns, path="/connections")
    api.add_namespace(instances_ns, path="/instances")
    api.add_namespace(tags_ns, path="/tags")
    api.add_namespace(credentials_ns, path="/credentials")
    api.add_namespace(accounts_ns, path="/accounts")
    api.add_namespace(dashboard_ns, path="/dashboard")

    @blueprint.get("/openapi.json")
    def openapi_json() -> tuple[Response, int]:
        return jsonify(api.__schema__), 200

    return blueprint
