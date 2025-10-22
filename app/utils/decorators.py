"""
鲸落 - 装饰器工具
"""

from functools import wraps
from typing import Any

from flask import flash, redirect, request, url_for
from flask_login import current_user

from app.constants.system_constants import ErrorMessages
from app.errors import AuthenticationError, AuthorizationError
from app.utils.structlog_config import get_system_logger, should_log_debug


def admin_required(f: Any) -> Any:  # noqa: ANN401
    """
    管理员权限装饰器

    Args:
        f: 被装饰的函数

    Returns:
        装饰后的函数
    """

    @wraps(f)
    def decorated_function(*args, **kwargs: Any) -> Any:  # noqa: ANN401
        system_logger = get_system_logger()

        if not current_user.is_authenticated:
            system_logger.warning(
                "未认证访问管理员功能",
                module="decorators",
                user_id=None,
                request_path=request.path,
                request_method=request.method,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
                permission_type="admin",
                failure_reason="not_authenticated",
            )
            if request.is_json:
                raise AuthenticationError(
                    ErrorMessages.AUTHENTICATION_REQUIRED,
                    message_key="AUTHENTICATION_REQUIRED",
                    extra={
                        "request_path": request.path,
                        "request_method": request.method,
                        "permission_type": "admin",
                    },
                )

            flash(ErrorMessages.AUTHENTICATION_REQUIRED, "warning")
            return redirect(url_for("auth.login"))

        if not current_user.is_admin():
            system_logger.warning(
                "权限不足访问管理员功能",
                module="decorators",
                user_id=current_user.id,
                username=current_user.username,
                user_role=current_user.role,
                request_path=request.path,
                request_method=request.method,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
                permission_type="admin",
                failure_reason="insufficient_permissions",
            )
            if request.is_json:
                raise AuthorizationError(
                    ErrorMessages.ADMIN_PERMISSION_REQUIRED,
                    message_key="ADMIN_PERMISSION_REQUIRED",
                    extra={
                        "request_path": request.path,
                        "request_method": request.method,
                        "permission_type": "admin",
                        "user_role": current_user.role,
                    },
                )

            flash(ErrorMessages.ADMIN_PERMISSION_REQUIRED, "error")
            return redirect(url_for("main.index"))

        # 只在调试模式下记录成功验证
        if should_log_debug():  # DEBUG level
            system_logger.debug(
                "管理员权限验证通过",
                module="decorators",
                user_id=current_user.id,
                username=current_user.username,
                request_path=request.path,
                request_method=request.method,
                permission_type="admin",
            )
        return f(*args, **kwargs)

    return decorated_function


def login_required(f: Any) -> Any:  # noqa: ANN401
    """
    登录权限装饰器

    Args:
        f: 被装饰的函数

    Returns:
        装饰后的函数
    """

    @wraps(f)
    def decorated_function(*args, **kwargs: Any) -> Any:  # noqa: ANN401
        system_logger = get_system_logger()

        if not current_user.is_authenticated:
            system_logger.warning(
                "未认证访问受保护资源",
                module="decorators",
                user_id=None,
                request_path=request.path,
                request_method=request.method,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
                permission_type="login",
                failure_reason="not_authenticated",
            )
            if request.is_json:
                raise AuthenticationError(
                    ErrorMessages.AUTHENTICATION_REQUIRED,
                    message_key="AUTHENTICATION_REQUIRED",
                    extra={
                        "request_path": request.path,
                        "request_method": request.method,
                        "permission_type": "login",
                    },
                )

            flash(ErrorMessages.AUTHENTICATION_REQUIRED, "warning")
            return redirect(url_for("auth.login"))

        # 只在调试模式下记录成功验证
        if should_log_debug():  # DEBUG level
            system_logger.debug(
                "登录权限验证通过",
                module="decorators",
                user_id=current_user.id,
                username=current_user.username,
                request_path=request.path,
                request_method=request.method,
                permission_type="login",
            )
        return f(*args, **kwargs)

    return decorated_function


def permission_required(permission: str) -> Any:  # noqa: ANN401
    """
    权限验证装饰器

    Args:
        permission: 需要的权限 (view, create, update, delete)

    Returns:
        装饰器函数
    """

    def decorator(f: Any) -> Any:  # noqa: ANN401
        @wraps(f)
        def decorated_function(*args, **kwargs: Any) -> Any:  # noqa: ANN401
            system_logger = get_system_logger()

            if not current_user.is_authenticated:
                system_logger.warning(
                    "未认证访问权限资源",
                    module="decorators",
                    user_id=None,
                    request_path=request.path,
                    request_method=request.method,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get("User-Agent", ""),
                    permission_type=permission,
                    failure_reason="not_authenticated",
                )
                if request.is_json:
                    raise AuthenticationError(
                        ErrorMessages.AUTHENTICATION_REQUIRED,
                        message_key="AUTHENTICATION_REQUIRED",
                        extra={
                            "request_path": request.path,
                            "request_method": request.method,
                            "permission_type": permission,
                        },
                    )

                flash(ErrorMessages.AUTHENTICATION_REQUIRED, "warning")
                return redirect(url_for("auth.login"))

            # 检查权限
            if not has_permission(current_user, permission):
                system_logger.warning(
                    "权限不足访问权限资源",
                    module="decorators",
                    user_id=current_user.id,
                    username=current_user.username,
                    user_role=current_user.role,
                    request_path=request.path,
                    request_method=request.method,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get("User-Agent", ""),
                    permission_type=permission,
                    failure_reason="insufficient_permissions",
                )
                if request.is_json:
                    message = ErrorMessages.PERMISSION_REQUIRED.format(permission=permission)
                    raise AuthorizationError(
                        message,
                        message_key="PERMISSION_REQUIRED",
                        extra={
                            "request_path": request.path,
                            "request_method": request.method,
                            "permission_type": permission,
                            "user_role": current_user.role,
                        },
                    )

                flash(
                    ErrorMessages.PERMISSION_REQUIRED.format(permission=permission),
                    "error",
                )
                return redirect(url_for("main.index"))

            # 只在调试模式下记录成功验证
            if should_log_debug():  # DEBUG level
                system_logger.debug(
                    "权限验证通过",
                    module="decorators",
                    user_id=current_user.id,
                    username=current_user.username,
                    request_path=request.path,
                    request_method=request.method,
                    permission_type=permission,
                )
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def has_permission(user: Any, permission: str) -> bool:
    """检查用户是否有指定权限。

    Args:
        user: 用户对象。
        permission: 权限名称，可以是简单的字符串或以点分隔的路径。

    Returns:
        bool: 是否有权限。
    """
    if not user or not user.is_authenticated:
        return False

    # 管理员拥有所有权限
    if user.role == "admin":
        return True

    # 模拟从数据库或配置中加载的用户权限
    # 在真实应用中，这里应该查询数据库
    user_permissions = {
        "user": {
            "view",
            "instance_management.instance_list.view",
            "instance_management.instance_list.sync_capacity",  # 授予 user 角色同步权限
        },
        "guest": {"view"},
    }

    required_permissions = user_permissions.get(user.role, set())

    # 检查是否有所需的权限
    return permission in required_permissions


def view_required(f: Any = None, *, permission: str = "view") -> Any:  # noqa: ANN401
    """查看权限装饰器.

    可以作为 @view_required 或 @view_required(permission="...") 使用.
    """

    def decorator(func: Any) -> Any:
        return permission_required(permission)(func)

    if callable(f):
        return decorator(f)
    return decorator


def create_required(f: Any = None, *, permission: str = "create") -> Any:  # noqa: ANN401
    """创建权限装饰器."""

    def decorator(func: Any) -> Any:
        return permission_required(permission)(func)

    if callable(f):
        return decorator(f)
    return decorator


def update_required(f: Any = None, *, permission: str = "update") -> Any:  # noqa: ANN401
    """更新权限装饰器."""

    def decorator(func: Any) -> Any:
        return permission_required(permission)(func)

    if callable(f):
        return decorator(f)
    return decorator


def delete_required(f: Any = None, *, permission: str = "delete") -> Any:  # noqa: ANN401
    """删除权限装饰器."""

    def decorator(func: Any) -> Any:
        return permission_required(permission)(func)

    if callable(f):
        return decorator(f)
    return decorator


def scheduler_view_required(f: Any) -> Any:  # noqa: ANN401
    """定时任务查看权限装饰器."""
    return permission_required("scheduler.view")(f)


def scheduler_manage_required(f: Any) -> Any:  # noqa: ANN401
    """定时任务管理权限装饰器."""
    return permission_required("scheduler.manage")(f)
