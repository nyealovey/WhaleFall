"""
鲸落 - 统一异常定义
集中维护业务异常类型、严重度与 HTTP 状态码映射
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from werkzeug.exceptions import HTTPException

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

    - message_key 对应 ErrorMessages 的属性名称，便于统一国际化处理
    - extra 用于承载额外上下文信息（不会直接暴露堆栈等敏感数据）
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
        status_code=400,
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.LOW,
        default_message_key="VALIDATION_ERROR",
    )


class AuthenticationError(AppError):
    metadata = ExceptionMetadata(
        status_code=401,
        category=ErrorCategory.AUTHENTICATION,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="INVALID_CREDENTIALS",
    )


class AuthorizationError(AppError):
    metadata = ExceptionMetadata(
        status_code=403,
        category=ErrorCategory.AUTHORIZATION,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="PERMISSION_DENIED",
    )


class NotFoundError(AppError):
    metadata = ExceptionMetadata(
        status_code=404,
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.LOW,
        default_message_key="RESOURCE_NOT_FOUND",
    )


class ConflictError(AppError):
    metadata = ExceptionMetadata(
        status_code=409,
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="CONSTRAINT_VIOLATION",
    )


class RateLimitError(AppError):
    metadata = ExceptionMetadata(
        status_code=429,
        category=ErrorCategory.SECURITY,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="RATE_LIMIT_EXCEEDED" if hasattr(ErrorMessages, "RATE_LIMIT_EXCEEDED") else "INVALID_REQUEST",
    )


class ExternalServiceError(AppError):
    metadata = ExceptionMetadata(
        status_code=502,
        category=ErrorCategory.EXTERNAL,
        severity=ErrorSeverity.HIGH,
        default_message_key="TASK_EXECUTION_FAILED",
    )


class DatabaseError(AppError):
    metadata = ExceptionMetadata(
        status_code=500,
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.HIGH,
        default_message_key="DATABASE_QUERY_ERROR",
    )


class SystemError(AppError):
    metadata = ExceptionMetadata(
        status_code=500,
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


def map_exception_to_status(error: Exception, default: int = 500) -> int:
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
