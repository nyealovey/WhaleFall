"""
鲸落 - 统一异常定义
集中维护业务异常类型、严重度与 HTTP 状态码映射
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from werkzeug.exceptions import HTTPException

from app.constants import HttpStatus
from app.constants.system_constants import ErrorCategory, ErrorMessages, ErrorSeverity


@dataclass(slots=True)
class ExceptionMetadata:
    """异常的元信息"""

    status_code: int
    category: ErrorCategory
    severity: ErrorSeverity
    default_message_key: str

    @property
    def default_message(self) -> str:
        """根据 message key 获取默认文案"""
        return getattr(ErrorMessages, self.default_message_key, ErrorMessages.INTERNAL_ERROR)

    @property
    def recoverable(self) -> bool:
        """根据严重度判断是否可恢复"""
        return self.severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM)


class AppError(Exception):
    """
    统一的基础业务异常。

    Args:
        message: 自定义错误文案，若为空则根据 ``message_key`` 推导。
        message_key: `ErrorMessages` 中的常量名称，便于统一管理/国际化。
        extra: 附加的上下文信息字典（例如 instance_id、payload 等安全字段）。
        severity: 可覆盖默认严重度，用于动态调整告警级别。
        category: 可覆盖默认错误分类，便于统计。
        status_code: HTTP 状态码，默认取 ``metadata`` 中的配置。
    """

    metadata = ExceptionMetadata(
        status_code=500,
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.HIGH,
        default_message_key="INTERNAL_ERROR",
    )

    def __init__(
        self,
        message: str | None = None,
        *,
        message_key: str | None = None,
        extra: Mapping[str, Any] | None = None,
        severity: ErrorSeverity | None = None,
        category: ErrorCategory | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message_key = message_key or self.metadata.default_message_key
        self.message = message or getattr(ErrorMessages, self.message_key, ErrorMessages.INTERNAL_ERROR)
        self.extra = dict(extra or {})
        self._severity = severity or self.metadata.severity
        self._category = category or self.metadata.category
        self._status_code = status_code or self.metadata.status_code
        super().__init__(self.message)

    @property
    def severity(self) -> ErrorSeverity:
        return self._severity

    @property
    def category(self) -> ErrorCategory:
        return self._category

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def recoverable(self) -> bool:
        return self.severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM)


class ValidationError(AppError):
    metadata = ExceptionMetadata(
        status_code=HttpStatus.BAD_REQUEST,
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.LOW,
        default_message_key="VALIDATION_ERROR",
    )


AppValidationError = ValidationError


class AuthenticationError(AppError):
    metadata = ExceptionMetadata(
        status_code=HttpStatus.UNAUTHORIZED,
        category=ErrorCategory.AUTHENTICATION,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="INVALID_CREDENTIALS",
    )


class AuthorizationError(AppError):
    metadata = ExceptionMetadata(
        status_code=HttpStatus.FORBIDDEN,
        category=ErrorCategory.AUTHORIZATION,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="PERMISSION_DENIED",
    )


class NotFoundError(AppError):
    metadata = ExceptionMetadata(
        status_code=HttpStatus.NOT_FOUND,
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.LOW,
        default_message_key="RESOURCE_NOT_FOUND",
    )


class ConflictError(AppError):
    metadata = ExceptionMetadata(
        status_code=HttpStatus.CONFLICT,
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="CONSTRAINT_VIOLATION",
    )


class RateLimitError(AppError):
    metadata = ExceptionMetadata(
        status_code=HttpStatus.TOO_MANY_REQUESTS,
        category=ErrorCategory.SECURITY,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="RATE_LIMIT_EXCEEDED" if hasattr(ErrorMessages, "RATE_LIMIT_EXCEEDED") else "INVALID_REQUEST",
    )


class ExternalServiceError(AppError):
    metadata = ExceptionMetadata(
        status_code=HttpStatus.BAD_GATEWAY,
        category=ErrorCategory.EXTERNAL,
        severity=ErrorSeverity.HIGH,
        default_message_key="TASK_EXECUTION_FAILED",
    )


class DatabaseError(AppError):
    metadata = ExceptionMetadata(
        status_code=HttpStatus.INTERNAL_SERVER_ERROR,
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.HIGH,
        default_message_key="DATABASE_QUERY_ERROR",
    )


class SystemError(AppError):
    metadata = ExceptionMetadata(
        status_code=HttpStatus.INTERNAL_SERVER_ERROR,
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.HIGH,
        default_message_key="INTERNAL_ERROR",
    )


EXCEPTION_STATUS_MAP: dict[type[BaseException], int] = {
    ValidationError: ValidationError.metadata.status_code,
    AuthenticationError: AuthenticationError.metadata.status_code,
    AuthorizationError: AuthorizationError.metadata.status_code,
    NotFoundError: NotFoundError.metadata.status_code,
    ConflictError: ConflictError.metadata.status_code,
    RateLimitError: RateLimitError.metadata.status_code,
    ExternalServiceError: ExternalServiceError.metadata.status_code,
    DatabaseError: DatabaseError.metadata.status_code,
    SystemError: SystemError.metadata.status_code,
}


def map_exception_to_status(error: Exception, default: int = HttpStatus.INTERNAL_SERVER_ERROR) -> int:
    """根据异常类型推导 HTTP 状态码"""
    if isinstance(error, AppError):
        return error.status_code

    if isinstance(error, HTTPException) and getattr(error, "code", None) is not None:
        return int(error.code)

    for exc_type, status in EXCEPTION_STATUS_MAP.items():
        if isinstance(error, exc_type):
            return status

    return default


__all__ = [
    "AppError",
    "AppValidationError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ExternalServiceError",
    "DatabaseError",
    "SystemError",
    "EXCEPTION_STATUS_MAP",
    "map_exception_to_status",
]
