"""WhaleFall - 统一异常定义(Shared Kernel).

说明:
- 本模块只负责定义异常类型与语义字段,不包含 HTTP/Flask/Werkzeug 等框架细节.
- 异常到 HTTP status 的映射应在 API/HTTP 边界完成(见 `app/api/error_mapping.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants.system_constants import ErrorCategory, ErrorMessages, ErrorSeverity

if TYPE_CHECKING:
    from app.types.structures import LoggerExtra


@dataclass(frozen=True, slots=True)
class ExceptionMetadata:
    """异常的元信息(不包含传输层信息)."""

    category: ErrorCategory
    severity: ErrorSeverity
    default_message_key: str


class AppError(Exception):
    """统一的基础业务异常.

    Args:
        message: 自定义错误文案,若为空则根据 ``message_key`` 推导.
        message_key: 自定义消息键.
        extra: 结构化日志附加字段.
        severity: 错误严重度.
        category: 错误分类.
    """

    metadata = ExceptionMetadata(
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.HIGH,
        default_message_key="INTERNAL_ERROR",
    )

    def __init__(
        self,
        message: str | None = None,
        *,
        message_key: str | None = None,
        extra: LoggerExtra | None = None,
        severity: ErrorSeverity | None = None,
        category: ErrorCategory | None = None,
    ) -> None:
        """初始化基础业务异常.

        Args:
            message: 直接使用的错误提示,缺省时会根据 message_key 推导.
            message_key: 覆盖默认 message_key 的可选值.
            extra: 结构化日志附加字段.
            severity: 错误严重度.
            category: 错误分类.
        """
        self.message_key = message_key or self.metadata.default_message_key
        self.message = message or getattr(ErrorMessages, self.message_key, ErrorMessages.INTERNAL_ERROR)
        self.extra = dict(extra or {})
        self.severity = severity or self.metadata.severity
        self.category = category or self.metadata.category
        super().__init__(self.message)

    @property
    def recoverable(self) -> bool:
        """表示该异常是否可恢复."""

        return self.severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM)


class ValidationError(AppError):
    """表示输入参数或请求体验证失败."""

    metadata = ExceptionMetadata(
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.LOW,
        default_message_key="VALIDATION_ERROR",
    )


class AuthenticationError(AppError):
    """表示用户凭证无效或已过期."""

    metadata = ExceptionMetadata(
        category=ErrorCategory.AUTHENTICATION,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="INVALID_CREDENTIALS",
    )


class AuthorizationError(AppError):
    """表示当前主体缺少访问目标资源的权限."""

    metadata = ExceptionMetadata(
        category=ErrorCategory.AUTHORIZATION,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="PERMISSION_DENIED",
    )


class NotFoundError(AppError):
    """表示客户端请求的资源不存在或被删除."""

    metadata = ExceptionMetadata(
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.LOW,
        default_message_key="RESOURCE_NOT_FOUND",
    )


class ConflictError(AppError):
    """表示资源状态冲突或违反唯一性约束."""

    metadata = ExceptionMetadata(
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="CONSTRAINT_VIOLATION",
    )


class RateLimitError(AppError):
    """表示触发网关或业务层的限流策略."""

    metadata = ExceptionMetadata(
        category=ErrorCategory.SECURITY,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="RATE_LIMIT_EXCEEDED",
    )


class ExternalServiceError(AppError):
    """表示下游依赖(如外部 API、服务)不可用或超时."""

    metadata = ExceptionMetadata(
        category=ErrorCategory.EXTERNAL,
        severity=ErrorSeverity.HIGH,
        default_message_key="TASK_EXECUTION_FAILED",
    )


class DatabaseError(AppError):
    """表示数据库查询或事务执行失败."""

    metadata = ExceptionMetadata(
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.HIGH,
        default_message_key="DATABASE_QUERY_ERROR",
    )


class SystemError(AppError):
    """表示系统级未知错误或底层故障."""


__all__ = [
    "AppError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "DatabaseError",
    "ExternalServiceError",
    "NotFoundError",
    "RateLimitError",
    "SystemError",
    "ValidationError",
]
