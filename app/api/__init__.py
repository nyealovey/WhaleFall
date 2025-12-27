"""WhaleFall JSON API (Flask-RESTX) 入口.

当前阶段(Phase 0):
- 新增 `/api/v1/**` 版本化 API blueprint
- 提供 Swagger UI 与 OpenAPI JSON 导出能力
"""

from __future__ import annotations

from flask import Flask, request

from app.constants import HttpStatus
from app.settings import Settings
from app.utils.response_utils import jsonify_unified_error_message


def _register_legacy_api_shutdown(app: Flask) -> None:
    """统一下线旧 `*/api/*` 端点.

    Phase 4 策略（强下线）:
    - `/api/v1/**` 为唯一可用的 JSON API 入口
    - 旧 `*/api/*` 端点统一返回 410 (Gone), 并输出标准错误封套
    """

    @app.before_request
    def _block_legacy_api():  # type: ignore[no-untyped-def]
        path = request.path or ""
        if path.startswith("/api/v1"):
            return None
        if "/api/" not in path:
            return None

        response, status = jsonify_unified_error_message(
            "旧版 API 已下线,请使用 /api/v1/**",
            status_code=HttpStatus.GONE,
            message_key="API_GONE",
            extra={
                "request_path": path,
                "replacement_prefix": "/api/v1",
            },
        )
        return response, status


def register_api_blueprints(app: Flask, settings: Settings) -> None:
    """按 Settings 注册 API blueprints.

    说明:
    - Phase 4 (强下线):
      - `/api/v1/**` 为唯一可用的对外 API
      - 旧 `*/api/*` 路由保留代码实现,但运行时统一 410
    """
    _register_legacy_api_shutdown(app)

    from app.api.v1 import create_api_v1_blueprint  # noqa: PLC0415

    api_v1_bp = create_api_v1_blueprint(settings)
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")
