"""Base Resource helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Unpack, cast

from flask import Response
from flask_restx import Resource

from app.constants import HttpStatus
from app.constants.system_constants import ErrorCategory, ErrorSeverity
from app.utils.response_utils import jsonify_unified_error_message, unified_success_response
from app.utils.route_safety import safe_route_call

if TYPE_CHECKING:
    from app.types import JsonDict, JsonValue, RouteSafetyOptions

R = TypeVar("R")


class BaseResource(Resource):
    """统一封套与 safe_route_call 适配."""

    def success(
        self,
        data: object | None = None,
        message: object | None = None,
        *,
        status: int = 200,
        meta: Mapping[str, object] | None = None,
    ) -> tuple[JsonDict, int]:
        """构造统一成功响应封套."""
        return unified_success_response(data=data, message=message, status=status, meta=meta)

    def error_message(
        self,
        message: str,
        *,
        status: int = HttpStatus.BAD_REQUEST,
        message_key: str = "INVALID_REQUEST",
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        extra: Mapping[str, JsonValue] | None = None,
    ) -> Response:
        """构造统一错误消息响应."""
        response, status_code = jsonify_unified_error_message(
            message,
            status_code=status,
            message_key=message_key,
            category=category,
            severity=severity,
            extra=extra,
        )
        response.status_code = status_code
        return response

    def safe_call(
        self,
        func: Callable[[], R],
        *,
        module: str,
        action: str,
        public_error: str,
        **options: Unpack[RouteSafetyOptions],
    ) -> R:
        """通过 `safe_route_call` 执行并统一错误处理."""
        return safe_route_call(
            func,
            module=module,
            action=action,
            public_error=public_error,
            **cast("dict[str, Any]", options),
        )
