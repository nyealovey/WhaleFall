"""Flask-RESTX Api 定制.

目标:
- 保持项目既有的 JSON envelope / 错误口径不变
- 将 RestX 内部错误统一映射为 `unified_error_response`
"""

from __future__ import annotations

from flask import Response, jsonify, request
from flask_restx import Api

from app.utils.response_utils import jsonify_unified_success, unified_error_response
from app.utils.structlog_config import ErrorContext


class WhaleFallApi(Api):
    """统一错误封套的 RestX Api."""

    def render_root(self) -> tuple[Response, int]:  # type: ignore[override]
        """为 `/api/v1/` 提供可发现性入口(避免误判“未部署”)."""
        prefix = request.path.rstrip("/")
        docs_url = f"{prefix}{self._doc}" if self._doc else None
        return jsonify_unified_success(
            data={
                "docs_url": docs_url,
                "openapi_url": f"{prefix}/openapi.json",
                "swagger_url": f"{prefix}/{self.default_swagger_filename}",
                "health_ping_url": f"{prefix}/health/ping",
            },
            message="API v1 已就绪",
        )

    def handle_error(self, e: Exception) -> Response:  # type: ignore[override]
        payload, status_code = unified_error_response(e, context=ErrorContext(e, request))
        response = jsonify(payload)
        response.status_code = status_code
        return response
