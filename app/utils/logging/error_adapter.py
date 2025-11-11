"""Enhanced error handling utilities shared by logging stack."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import uuid4

from flask import has_request_context
from werkzeug.exceptions import HTTPException

from app.constants import HttpStatus
from app.constants.system_constants import ErrorCategory, ErrorMessages, ErrorSeverity
from app.errors import AppError
from app.utils.logging.context_vars import request_id_var, user_id_var
from app.utils.time_utils import time_utils


@dataclass(slots=True)
class ErrorContext:
    """Error context captured at exception time."""

    error: Exception
    request: Any | None = None
    error_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=time_utils.now)
    request_id: str | None = field(default_factory=lambda: request_id_var.get())
    user_id: int | None = field(default_factory=lambda: user_id_var.get())
    url: str | None = None
    method: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def ensure_request(self) -> None:
        if self.request is None and has_request_context():
            from flask import request as flask_request

            self.request = flask_request

        if self.request is not None:
            self.url = getattr(self.request, "url", self.url)
            self.method = getattr(self.request, "method", self.method)
            self.extra.setdefault("ip_address", getattr(self.request, "remote_addr", None))
            user_agent = getattr(self.request, "user_agent", None)
            if user_agent:
                self.extra.setdefault("user_agent", getattr(user_agent, "string", user_agent))


@dataclass(slots=True)
class ErrorMetadata:
    """Derived error metadata for classification."""

    status_code: int
    category: ErrorCategory
    severity: ErrorSeverity
    message_key: str
    message: str
    recoverable: bool


def derive_error_metadata(error: Exception) -> ErrorMetadata:
    if isinstance(error, AppError):
        return ErrorMetadata(
            status_code=error.status_code,
            category=error.category,
            severity=error.severity,
            message_key=error.message_key,
            message=error.message,
            recoverable=error.recoverable,
        )

    if isinstance(error, HTTPException):
        status_code = int(getattr(error, "code", HttpStatus.INTERNAL_SERVER_ERROR) or HttpStatus.INTERNAL_SERVER_ERROR)
        message = getattr(error, "description", ErrorMessages.INTERNAL_ERROR)
        message_key = "INTERNAL_ERROR" if status_code >= HttpStatus.INTERNAL_SERVER_ERROR else "INVALID_REQUEST"
        severity = ErrorSeverity.HIGH if status_code >= HttpStatus.INTERNAL_SERVER_ERROR else ErrorSeverity.MEDIUM
        category = ErrorCategory.SYSTEM if status_code >= HttpStatus.INTERNAL_SERVER_ERROR else ErrorCategory.BUSINESS
        return ErrorMetadata(
            status_code=status_code,
            category=category,
            severity=severity,
            message_key=message_key,
            message=message,
            recoverable=severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM),
        )

    message_lower = str(error).lower()
    if "timeout" in message_lower or "connection" in message_lower:
        message_key = "DATABASE_TIMEOUT"
        message = getattr(ErrorMessages, message_key, ErrorMessages.DATABASE_TIMEOUT)
        return ErrorMetadata(
            status_code=504,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            message_key=message_key,
            message=message,
            recoverable=False,
        )

    if any(word in message_lower for word in ["permission", "forbidden", "denied"]):
        message_key = "PERMISSION_DENIED"
        message = getattr(ErrorMessages, message_key, ErrorMessages.PERMISSION_DENIED)
        return ErrorMetadata(
            status_code=403,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.MEDIUM,
            message_key=message_key,
            message=message,
            recoverable=False,
        )

    if any(word in message_lower for word in ["validation", "invalid"]):
        message_key = "VALIDATION_ERROR"
        message = getattr(ErrorMessages, message_key, ErrorMessages.VALIDATION_ERROR)
        return ErrorMetadata(
            status_code=400,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            message_key=message_key,
            message=message,
            recoverable=True,
        )

    return ErrorMetadata(
        status_code=500,
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.HIGH,
        message_key="INTERNAL_ERROR",
        message=ErrorMessages.INTERNAL_ERROR,
        recoverable=False,
    )


def build_public_context(context: ErrorContext) -> dict[str, Any]:
    context.ensure_request()
    payload: dict[str, Any] = {
        "request_id": context.request_id,
        "user_id": context.user_id,
    }
    if context.url:
        payload["url"] = context.url
    if context.method:
        payload["method"] = context.method
    if context.extra:
        payload["meta"] = {key: value for key, value in context.extra.items() if value is not None}
    return payload


def get_error_suggestions(category: ErrorCategory) -> list[str]:
    suggestions_map = {
        ErrorCategory.VALIDATION: ["检查输入数据", "根据提示修正请求参数"],
        ErrorCategory.BUSINESS: ["确认业务规则", "联系管理员核对数据"],
        ErrorCategory.AUTHENTICATION: ["重新登录", "验证凭据有效性"],
        ErrorCategory.AUTHORIZATION: ["检查权限配置", "联系管理员"],
        ErrorCategory.SECURITY: ["稍后重试", "联系管理员"],
        ErrorCategory.DATABASE: ["检查数据库连接", "联系数据库管理员"],
        ErrorCategory.EXTERNAL: ["确认第三方服务状态", "稍后重试"],
        ErrorCategory.NETWORK: ["检查网络连接", "稍后重试"],
        ErrorCategory.SYSTEM: ["联系管理员", "查看错误日志"],
    }
    return suggestions_map.get(category, ["联系管理员", "查看错误日志"])


__all__ = [
    "ErrorContext",
    "ErrorMetadata",
    "derive_error_metadata",
    "build_public_context",
    "get_error_suggestions",
]
