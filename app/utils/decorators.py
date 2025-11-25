"""
鲸落 - 装饰器工具
"""

from functools import wraps
from typing import Any, Optional

from flask import flash, redirect, request, url_for
from flask_login import current_user
from flask_wtf.csrf import CSRFError, validate_csrf

from app.constants.system_constants import ErrorMessages
from app.constants import TaskStatus, UserRole, FlashCategory, HttpHeaders
from app.errors import AuthenticationError, AuthorizationError
from app.utils.structlog_config import get_system_logger, should_log_debug

CSRF_HEADER = HttpHeaders.X_CSRF_TOKEN
SAFE_CSRF_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

def admin_required(f: Any) -> Any:  # noqa: ANN401
    """确保被装饰函数仅允许管理员访问的装饰器。

    验证当前用户是否已认证且具有管理员角色。
    如果验证失败，根据请求类型返回 JSON 错误或重定向到登录页。

    Args:
        f: 被装饰的函数。

    Returns:
        装饰后的函数。

    Raises:
        AuthenticationError: 当用户未认证时抛出（JSON 请求）。
        AuthorizationError: 当用户权限不足时抛出（JSON 请求）。
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
                user_agent=request.headers.get(HttpHeaders.USER_AGENT, ""),
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

            flash(ErrorMessages.AUTHENTICATION_REQUIRED, FlashCategory.WARNING)
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
                user_agent=request.headers.get(HttpHeaders.USER_AGENT, ""),
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

            flash(ErrorMessages.ADMIN_PERMISSION_REQUIRED, FlashCategory.ERROR)
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
    """要求调用者已登录的装饰器。"""

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
                user_agent=request.headers.get(HttpHeaders.USER_AGENT, ""),
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

            flash(ErrorMessages.AUTHENTICATION_REQUIRED, FlashCategory.WARNING)
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
    """校验指定权限（view/create/update/delete）的装饰器工厂。"""

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
                    user_agent=request.headers.get(HttpHeaders.USER_AGENT, ""),
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

                flash(ErrorMessages.AUTHENTICATION_REQUIRED, FlashCategory.WARNING)
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
                    user_agent=request.headers.get(HttpHeaders.USER_AGENT, ""),
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


def _extract_csrf_token() -> Optional[str]:
    """从请求中提取 CSRF 令牌."""
    token = request.headers.get(CSRF_HEADER)
    if token:
        return token

    if request.is_json:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            token = payload.get("csrf_token")
            if token:
                return token

    return request.form.get("csrf_token")


def require_csrf(f: Any) -> Any:  # noqa: ANN401
    """统一的 CSRF 校验装饰器."""

    @wraps(f)
    def decorated_function(*args, **kwargs: Any) -> Any:  # noqa: ANN401
        if request.method.upper() in SAFE_CSRF_METHODS:
            return f(*args, **kwargs)

        system_logger = get_system_logger()
        token = _extract_csrf_token()
        if not token:
            system_logger.warning(
                "CSRF 令牌缺失",
                module="decorators",
                request_path=request.path,
                request_method=request.method,
                ip_address=request.remote_addr,
                user_agent=request.headers.get(HttpHeaders.USER_AGENT, ""),
            )
            raise AuthorizationError(
                "缺少 CSRF 令牌",
                message_key="CSRF_MISSING",
                extra={
                    "request_path": request.path,
                    "request_method": request.method,
                },
            )

        try:
            validate_csrf(token)
        except CSRFError as exc:
            system_logger.warning(
                "CSRF 令牌校验失败",
                module="decorators",
                request_path=request.path,
                request_method=request.method,
                ip_address=request.remote_addr,
                user_agent=request.headers.get(HttpHeaders.USER_AGENT, ""),
                exception=str(exc),
            )
            raise AuthorizationError(
                "CSRF 令牌无效，请刷新后重试",
                message_key="CSRF_INVALID",
                extra={
                    "request_path": request.path,
                    "request_method": request.method,
                },
            ) from exc

        return f(*args, **kwargs)

    return decorated_function


def has_permission(user: Any, permission: str) -> bool:
    """检查给定用户是否具备指定权限。"""
    if not user or not user.is_authenticated:
        return False

    # 管理员拥有所有权限
    if user.role == UserRole.ADMIN:
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
    """校验查看权限的装饰器，可直接使用或指定自定义权限。"""

    def decorator(func: Any) -> Any:
        return permission_required(permission)(func)

    if callable(f):
        return decorator(f)
    return decorator


def create_required(f: Any = None, *, permission: str = "create") -> Any:  # noqa: ANN401
    """校验创建权限的装饰器。"""

    def decorator(func: Any) -> Any:
        return permission_required(permission)(func)

    if callable(f):
        return decorator(f)
    return decorator


def update_required(f: Any = None, *, permission: str = "update") -> Any:  # noqa: ANN401
    """校验更新权限的装饰器。"""

    def decorator(func: Any) -> Any:
        return permission_required(permission)(func)

    if callable(f):
        return decorator(f)
    return decorator


def delete_required(f: Any = None, *, permission: str = "delete") -> Any:  # noqa: ANN401
    """校验删除权限的装饰器。"""

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
