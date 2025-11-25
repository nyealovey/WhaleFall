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
        """根据 message key 获取默认文案。

        Returns:
            str: 对应 `ErrorMessages` 中的默认消息。
        """
        return getattr(ErrorMessages, self.default_message_key, ErrorMessages.INTERNAL_ERROR)

    @property
    def recoverable(self) -> bool:
        """根据严重度判断是否可恢复。

        Returns:
            bool: 当严重度为 LOW/MEDIUM 时返回 True。
        """
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
        """返回异常实例对应的严重度。

        Returns:
            ErrorSeverity: 结合元数据或动态覆写后的严重度枚举值。
        """

        return self._severity

    @property
    def category(self) -> ErrorCategory:
        """返回异常所属的业务分类。

        Returns:
            ErrorCategory: 统一的错误分类，用于统计与监控。
        """

        return self._category

    @property
    def status_code(self) -> int:
        """返回异常对应的 HTTP 状态码。

        Returns:
            int: 对外暴露的 HTTP 状态码，默认为异常元数据配置。
        """

        return self._status_code

    @property
    def recoverable(self) -> bool:
        """表示该异常是否可恢复。

        Returns:
            bool: 严重度为 LOW 或 MEDIUM 时为 True，表示可重试或自动修复。
        """

        return self.severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM)


class ValidationError(AppError):
    """表示输入参数或请求体验证失败。

    常用于表单校验、接口必填字段缺失等场景，默认返回 400。
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.BAD_REQUEST,
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.LOW,
        default_message_key="VALIDATION_ERROR",
    )


AppValidationError = ValidationError


class AuthenticationError(AppError):
    """表示用户凭证无效或已过期。

    通常由登录、令牌刷新流程抛出，默认返回 401。
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.UNAUTHORIZED,
        category=ErrorCategory.AUTHENTICATION,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="INVALID_CREDENTIALS",
    )


class AuthorizationError(AppError):
    """表示当前主体缺少访问目标资源的权限。

    常见于权限校验或资源级 ACL 判断，默认返回 403。
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.FORBIDDEN,
        category=ErrorCategory.AUTHORIZATION,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="PERMISSION_DENIED",
    )


class NotFoundError(AppError):
    """表示客户端请求的资源不存在或被删除。

    适用于实例/账户查找失败等情况，默认返回 404。
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.NOT_FOUND,
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.LOW,
        default_message_key="RESOURCE_NOT_FOUND",
    )


class ConflictError(AppError):
    """表示资源状态冲突或违反唯一性约束。

    典型场景为重复创建、并发修改冲突，默认返回 409。
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.CONFLICT,
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="CONSTRAINT_VIOLATION",
    )


class RateLimitError(AppError):
    """表示触发网关或业务层的限流策略。

    当请求频率超出限制时抛出，默认返回 429。
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.TOO_MANY_REQUESTS,
        category=ErrorCategory.SECURITY,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="RATE_LIMIT_EXCEEDED" if hasattr(ErrorMessages, "RATE_LIMIT_EXCEEDED") else "INVALID_REQUEST",
    )


class ExternalServiceError(AppError):
    """表示下游依赖（如外部 API、服务）不可用或超时。

    抛出后提醒调用方重试或降级，默认返回 502。
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.BAD_GATEWAY,
        category=ErrorCategory.EXTERNAL,
        severity=ErrorSeverity.HIGH,
        default_message_key="TASK_EXECUTION_FAILED",
    )


class DatabaseError(AppError):
    """表示数据库查询或事务执行失败。

    可用于 SQL 异常、连接失败等情况，默认返回 500。
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.INTERNAL_SERVER_ERROR,
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.HIGH,
        default_message_key="DATABASE_QUERY_ERROR",
    )


class SystemError(AppError):
    """表示系统级未知错误或底层故障。

    用于捕获无法归类的异常，默认返回 500。
    """

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
    """根据异常类型推导 HTTP 状态码。

    Args:
        error: 捕获到的异常对象。
        default: 无法匹配时的默认状态码。

    Returns:
        int: 与异常对应的 HTTP 状态码。
    """
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
