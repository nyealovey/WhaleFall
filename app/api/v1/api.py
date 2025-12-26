"""Flask-RESTX Api 定制.

目标:
- 保持项目既有的 JSON envelope / 错误口径不变
- 将 RestX 内部错误统一映射为 `unified_error_response`
"""

from __future__ import annotations

from flask import Response, jsonify, request
from flask_restx import Api

from app.utils.response_utils import unified_error_response
from app.utils.structlog_config import ErrorContext


class WhaleFallApi(Api):
    """统一错误封套的 RestX Api."""

    def handle_error(self, e: Exception) -> Response:  # type: ignore[override]
        payload, status_code = unified_error_response(e, context=ErrorContext(e, request))
        response = jsonify(payload)
        response.status_code = status_code
        return response
