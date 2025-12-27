"""Base Resource helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from flask import Response
from flask_restx import Resource

from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call

if TYPE_CHECKING:
    from app.types import ContextDict, JsonValue, LoggerExtra, RouteSafetyOptions

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
    ) -> tuple[Response, int]:
        return jsonify_unified_success(data=data, message=message, status=status, meta=meta)

    def safe_call(
        self,
        func: Callable[[], R],
        *,
        module: str,
        action: str,
        public_error: str,
        context: ContextDict | None = None,
        extra: LoggerExtra | None = None,
        **options: RouteSafetyOptions,
    ) -> R:
        return safe_route_call(
            func,
            module=module,
            action=action,
            public_error=public_error,
            context=cast("ContextDict | None", context),
            extra=cast("dict[str, JsonValue] | None", extra),
            **cast("dict[str, Any]", options),
        )
