"""API v1 decorators.

说明:
- API v1 的错误语义应始终为 JSON（禁止 redirect/flash）
- 统一通过 AppError 体系让全局错误处理器输出标准错误封套
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from flask import request
from flask_login import current_user

from app.core.constants.system_constants import ErrorMessages
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.utils.decorators import has_permission

P = ParamSpec("P")
R = TypeVar("R")


def api_login_required(func: Callable[P, R]) -> Callable[P, R]:
    """要求调用者已登录（API v1 专用）."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if not current_user.is_authenticated:
            raise AuthenticationError(
                ErrorMessages.AUTHENTICATION_REQUIRED,
                message_key="AUTHENTICATION_REQUIRED",
                extra={
                    "request_path": request.path,
                    "request_method": request.method,
                    "permission_type": "login",
                },
            )
        return func(*args, **kwargs)

    return wrapper


def api_permission_required(permission: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """校验指定权限(view/create/update/delete)（API v1 专用）."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not current_user.is_authenticated:
                raise AuthenticationError(
                    ErrorMessages.AUTHENTICATION_REQUIRED,
                    message_key="AUTHENTICATION_REQUIRED",
                    extra={
                        "request_path": request.path,
                        "request_method": request.method,
                        "permission_type": permission,
                    },
                )
            if not has_permission(cast(Any, current_user), permission):
                raise AuthorizationError(
                    ErrorMessages.PERMISSION_REQUIRED.format(permission=permission),
                    message_key="PERMISSION_REQUIRED",
                    extra={
                        "request_path": request.path,
                        "request_method": request.method,
                        "permission_type": permission,
                    },
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def api_view_required(func: Callable[P, R]) -> Callable[P, R]:
    """校验 view 权限（API v1 专用）."""
    return api_permission_required("view")(func)


def api_admin_required(func: Callable[P, R]) -> Callable[P, R]:
    """要求调用者为管理员（API v1 专用）."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if not current_user.is_authenticated:
            raise AuthenticationError(
                ErrorMessages.AUTHENTICATION_REQUIRED,
                message_key="AUTHENTICATION_REQUIRED",
                extra={
                    "request_path": request.path,
                    "request_method": request.method,
                    "permission_type": "admin",
                },
            )

        is_admin = bool(getattr(current_user, "is_admin", lambda: False)())
        if not is_admin:
            raise AuthorizationError(
                ErrorMessages.ADMIN_PERMISSION_REQUIRED,
                message_key="ADMIN_PERMISSION_REQUIRED",
                extra={
                    "request_path": request.path,
                    "request_method": request.method,
                    "permission_type": "admin",
                    "user_role": getattr(current_user, "role", None),
                },
            )

        return func(*args, **kwargs)

    return wrapper
