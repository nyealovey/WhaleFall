"""WhaleFall JSON API (Flask-RESTX) 入口.

当前阶段(Phase 0):
- 新增 `/api/v1/**` 版本化 API blueprint
- 提供 Swagger UI 与 OpenAPI JSON 导出能力
"""

from __future__ import annotations

from flask import Flask

from app.settings import Settings


def register_api_blueprints(app: Flask, settings: Settings) -> None:
    """按 Settings 注册 API blueprints.

    说明:
    - `/api/v1/**` 为唯一可用的对外 JSON API.
    """
    from app.api.v1 import create_api_v1_blueprint  # noqa: PLC0415

    api_v1_bp = create_api_v1_blueprint(settings)
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")
