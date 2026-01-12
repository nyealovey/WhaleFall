"""WhaleFall - 异常与 HTTP 状态码映射(API 边界).

说明:
- 异常定义属于 shared kernel(`app/core/exceptions.py`),不感知 HTTP.
- 本模块负责将异常映射为对外 HTTP 状态码,仅应在 HTTP 边界调用.
"""

from __future__ import annotations

from werkzeug.exceptions import HTTPException

from app.constants import HttpStatus
from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

_EXCEPTION_STATUS_MAP: tuple[tuple[type[Exception], int], ...] = (
    (ValidationError, HttpStatus.BAD_REQUEST),
    (AuthenticationError, HttpStatus.UNAUTHORIZED),
    (AuthorizationError, HttpStatus.FORBIDDEN),
    (NotFoundError, HttpStatus.NOT_FOUND),
    (ConflictError, HttpStatus.CONFLICT),
    (RateLimitError, HttpStatus.TOO_MANY_REQUESTS),
    (ExternalServiceError, HttpStatus.BAD_GATEWAY),
)


def map_exception_to_status(error: Exception, default: int = HttpStatus.INTERNAL_SERVER_ERROR) -> int:
    """根据异常类型推导 HTTP 状态码."""

    for exc_type, status in _EXCEPTION_STATUS_MAP:
        if isinstance(error, exc_type):
            return status

    if isinstance(error, AppError):
        return default

    if isinstance(error, HTTPException):
        code = getattr(error, "code", None)
        if code is not None:
            return int(code)

    return default


__all__ = ["map_exception_to_status"]
