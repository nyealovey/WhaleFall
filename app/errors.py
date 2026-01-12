"""鲸落 - 异常定义(兼容门面).

说明:
- 异常类型的“源位置”为 `app/core/exceptions.py`(shared kernel)
- 本模块仅保留为历史 import 路径的 re-export,避免大范围改动
"""

from __future__ import annotations

from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    NotFoundError,
    RateLimitError,
    SystemError,
    ValidationError,
)


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
