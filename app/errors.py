"""鲸落 - 统一异常定义.

集中维护业务异常类型与元数据定义.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.constants import HttpStatus
from app.constants.system_constants import ErrorCategory, ErrorMessages, ErrorSeverity

if TYPE_CHECKING:
    from app.types.structures import LoggerExtra


@dataclass(frozen=True, slots=True)
class ExceptionMetadata:
    """异常的元信息."""

    status_code: int
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
        status_code: HTTP 状态码.

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
        extra: LoggerExtra | None = None,
        severity: ErrorSeverity | None = None,
        category: ErrorCategory | None = None,
        status_code: int | None = None,
    ) -> None:
        """初始化基础业务异常.

        Args:
            message: 直接使用的错误提示,缺省时会根据 message_key 推导.
            message_key: 覆盖默认 message_key 的可选值.
            extra: 结构化日志附加字段.
            severity: 错误严重度.
            category: 错误分类.
            status_code: HTTP 状态码.

        """
        self.message_key = message_key or self.metadata.default_message_key
        self.message = message or getattr(ErrorMessages, self.message_key, ErrorMessages.INTERNAL_ERROR)
        self.extra = dict(extra or {})
        self.severity = severity or self.metadata.severity
        self.category = category or self.metadata.category
        self.status_code = status_code or self.metadata.status_code
        super().__init__(self.message)

    @property
    def recoverable(self) -> bool:
        """表示该异常是否可恢复.

        Returns:
            bool: 严重度为 LOW 或 MEDIUM 时为 True,表示可重试或自动修复.

        """
        return self.severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM)


class ValidationError(AppError):
    """表示输入参数或请求体验证失败.

    常用于表单校验、接口必填字段缺失等场景,默认返回 400.
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.BAD_REQUEST,
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.LOW,
        default_message_key="VALIDATION_ERROR",
    )


class AuthenticationError(AppError):
    """表示用户凭证无效或已过期.

    通常由登录、令牌刷新流程抛出,默认返回 401.
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.UNAUTHORIZED,
        category=ErrorCategory.AUTHENTICATION,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="INVALID_CREDENTIALS",
    )


class AuthorizationError(AppError):
    """表示当前主体缺少访问目标资源的权限.

    常见于权限校验或资源级 ACL 判断,默认返回 403.
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.FORBIDDEN,
        category=ErrorCategory.AUTHORIZATION,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="PERMISSION_DENIED",
    )


class NotFoundError(AppError):
    """表示客户端请求的资源不存在或被删除.

    适用于实例/账户查找失败等情况,默认返回 404.
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.NOT_FOUND,
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.LOW,
        default_message_key="RESOURCE_NOT_FOUND",
    )


class ConflictError(AppError):
    """表示资源状态冲突或违反唯一性约束.

    典型场景为重复创建、并发修改冲突,默认返回 409.
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.CONFLICT,
        category=ErrorCategory.BUSINESS,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="CONSTRAINT_VIOLATION",
    )


class RateLimitError(AppError):
    """表示触发网关或业务层的限流策略.

    当请求频率超出限制时抛出,默认返回 429.
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.TOO_MANY_REQUESTS,
        category=ErrorCategory.SECURITY,
        severity=ErrorSeverity.MEDIUM,
        default_message_key="RATE_LIMIT_EXCEEDED",
    )


class ExternalServiceError(AppError):
    """表示下游依赖(如外部 API、服务)不可用或超时.

    抛出后提醒调用方重试或降级,默认返回 502.
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.BAD_GATEWAY,
        category=ErrorCategory.EXTERNAL,
        severity=ErrorSeverity.HIGH,
        default_message_key="TASK_EXECUTION_FAILED",
    )


class DatabaseError(AppError):
    """表示数据库查询或事务执行失败.

    可用于 SQL 异常、连接失败等情况,默认返回 500.
    """

    metadata = ExceptionMetadata(
        status_code=HttpStatus.INTERNAL_SERVER_ERROR,
        category=ErrorCategory.DATABASE,
        severity=ErrorSeverity.HIGH,
        default_message_key="DATABASE_QUERY_ERROR",
    )


class SystemError(AppError):
    """表示系统级未知错误或底层故障.

    用于捕获无法归类的异常,默认返回 500.
    """

    pass


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
