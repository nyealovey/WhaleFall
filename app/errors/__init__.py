"""鲸落 - 统一异常定义.

集中维护业务异常类型、严重度与 HTTP 状态码映射.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, TypedDict, Unpack, cast

from werkzeug.exceptions import HTTPException

from app.constants import HttpStatus
from app.constants.system_constants import ErrorCategory, ErrorMessages, ErrorSeverity

if TYPE_CHECKING:
    from app.types.structures import LoggerExtra


class LegacyAppErrorKwargs(TypedDict, total=False):
    """AppError 兼容关键字参数结构.

    保留对旧版本 ``AppError`` 调用方式的支持,便于增量迁移.
    """

    message_key: str | None
    extra: LoggerExtra | None
    severity: ErrorSeverity | None
    category: ErrorCategory | None
    status_code: int | None


@dataclass(slots=True)
class ExceptionMetadata:
    """异常的元信息."""

    status_code: int
    category: ErrorCategory
    severity: ErrorSeverity
    default_message_key: str

    @property
    def default_message(self) -> str:
        """根据 message key 获取默认文案.

        Returns:
            str: 对应 `ErrorMessages` 中的默认消息.

        """
        return getattr(ErrorMessages, self.default_message_key, ErrorMessages.INTERNAL_ERROR)

    @property
    def recoverable(self) -> bool:
        """根据严重度判断是否可恢复.

        Returns:
            bool: 当严重度为 LOW/MEDIUM 时返回 True.

        """
        return self.severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM)


@dataclass(slots=True)
class AppErrorOptions:
    """AppError 初始化的可选配置."""

    message_key: str | None = None
    extra: LoggerExtra | None = None
    severity: ErrorSeverity | None = None
    category: ErrorCategory | None = None
    status_code: int | None = None


class AppError(Exception):
    """统一的基础业务异常.

    Args:
        message: 自定义错误文案,若为空则根据 ``message_key`` 推导.
        options: 额外配置对象,可覆盖 message_key、extra、severity、category、status_code。
        **legacy_kwargs: 为兼容旧调用方式保留的关键字参数,与 ``options`` 中字段一致。

    """

    metadata = ExceptionMetadata(
        status_code=500,
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.HIGH,
        default_message_key="INTERNAL_ERROR",
    )

    _OPTION_FIELD_NAMES: ClassVar[set[str]] = set(AppErrorOptions.__annotations__.keys())

    def __init__(
        self,
        message: str | None = None,
        *,
        options: AppErrorOptions | None = None,
        **legacy_kwargs: Unpack[LegacyAppErrorKwargs],
    ) -> None:
        """初始化基础业务异常.

        Args:
            message: 直接使用的错误提示,缺省时会根据 message_key 推导.
            options: 包含 message_key、extra、severity、category、status_code 的配置对象.
            **legacy_kwargs: 与 ``options`` 字段一致的关键字参数,用于维持兼容.

        """
        resolved_options = self._build_options(options, legacy_kwargs)
        self.message_key = resolved_options.message_key or self.metadata.default_message_key
        self.message = self._resolve_message(message, self.message_key)
        self.extra = dict(resolved_options.extra or {})
        self._severity = resolved_options.severity or self.metadata.severity
        self._category = resolved_options.category or self.metadata.category
        self._status_code = resolved_options.status_code or self.metadata.status_code
        super().__init__(self.message)

    @property
    def severity(self) -> ErrorSeverity:
        """返回异常实例对应的严重度.

        Returns:
            ErrorSeverity: 结合元数据或动态覆写后的严重度枚举值.

        """
        return self._severity

    @property
    def category(self) -> ErrorCategory:
        """返回异常所属的业务分类.

        Returns:
            ErrorCategory: 统一的错误分类,用于统计与监控.

        """
        return self._category

    @property
    def status_code(self) -> int:
        """返回异常对应的 HTTP 状态码.

        Returns:
            int: 对外暴露的 HTTP 状态码,默认为异常元数据配置.

        """
        return self._status_code

    @property
    def recoverable(self) -> bool:
        """表示该异常是否可恢复.

        Returns:
            bool: 严重度为 LOW 或 MEDIUM 时为 True,表示可重试或自动修复.

        """
        return self.severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM)

    def _build_options(
        self,
        options: AppErrorOptions | None,
        overrides: LegacyAppErrorKwargs,
    ) -> AppErrorOptions:
        """组装异常初始化配置.

        Args:
            options: 新调用路径传入的配置对象,可为空.
            overrides: 兼容旧接口的关键字参数集合.

        Returns:
            AppErrorOptions: 归一化后的配置对象,供异常初始化使用.

        """
        overrides_dict: LegacyAppErrorKwargs = cast(LegacyAppErrorKwargs, dict(overrides))
        self._validate_option_keys(overrides_dict)
        return self._options_from_kwargs(options, overrides_dict)

    @classmethod
    def _validate_option_keys(cls, overrides: LegacyAppErrorKwargs) -> None:
        """确保 legacy 关键字参数与支持列表一致.

        Args:
            overrides: 调用方透传的关键字参数.

        Raises:
            ValueError: 当存在未定义的关键字参数时抛出.

        """
        unexpected = set(overrides) - cls._OPTION_FIELD_NAMES
        if unexpected:
            invalid = ", ".join(sorted(unexpected))
            msg = f"AppError 不支持的参数: {invalid}"
            raise ValueError(msg)

    @staticmethod
    def _options_from_kwargs(
        options: AppErrorOptions | None,
        overrides: LegacyAppErrorKwargs,
    ) -> AppErrorOptions:
        """将 dataclass 与旧关键字参数合并.

        Args:
            options: dataclass 形式的可选配置对象.
            overrides: 旧版关键字参数,优先级高于 dataclass 字段.

        Returns:
            AppErrorOptions: 合并后的配置,确保字段齐备.

        """
        base_data: LegacyAppErrorKwargs = {
            "message_key": options.message_key if options else None,
            "extra": options.extra if options else None,
            "severity": options.severity if options else None,
            "category": options.category if options else None,
            "status_code": options.status_code if options else None,
        }
        base_data.update(overrides)
        return AppErrorOptions(**base_data)

    @staticmethod
    def _resolve_message(message: str | None, message_key: str) -> str:
        """根据 message 与 message_key 推导最终提示.

        Args:
            message: 调用方显式传入的文案.
            message_key: 需要查找默认文案的键名.

        Returns:
            str: 直接使用的自定义文案或默认枚举值.

        """
        if message:
            return message
        return getattr(ErrorMessages, message_key, ErrorMessages.INTERNAL_ERROR)


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


AppValidationError = ValidationError


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
        default_message_key=(
            "RATE_LIMIT_EXCEEDED" if hasattr(ErrorMessages, "RATE_LIMIT_EXCEEDED") else "INVALID_REQUEST"
        ),
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
    """根据异常类型推导 HTTP 状态码.

    结合应用内已知异常类型映射,保证向 API 层输出一致的 HTTP 状态.

    Args:
        error: 捕获到的异常对象.
        default: 无法匹配时的默认状态码.

    Returns:
        int: 与异常对应的 HTTP 状态码.

    """
    if isinstance(error, AppError):
        return error.status_code

    if isinstance(error, HTTPException):
        code = getattr(error, "code", None)
        if code is not None:
            return int(code)

    for exc_type, status in EXCEPTION_STATUS_MAP.items():
        if isinstance(error, exc_type):
            return status

    return default


__all__ = [
    "EXCEPTION_STATUS_MAP",
    "AppError",
    "AppValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "DatabaseError",
    "ExternalServiceError",
    "NotFoundError",
    "RateLimitError",
    "SystemError",
    "ValidationError",
    "map_exception_to_status",
]
