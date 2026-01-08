"""鲸落 - 装饰器工具."""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, Protocol, cast, overload

from flask import flash, redirect, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user
from flask_wtf.csrf import CSRFError, validate_csrf

from app.constants import FlashCategory, HttpHeaders, UserRole
from app.constants.system_constants import ErrorMessages
from app.errors import AuthenticationError, AuthorizationError
from app.utils.structlog_config import get_system_logger, should_log_debug

P = ParamSpec("P")
ReturnType = ResponseReturnValue


class PermissionUser(Protocol):
    """用于描述具备角色信息的用户协议."""

    is_authenticated: bool
    role: str


CSRF_HEADER = HttpHeaders.X_CSRF_TOKEN
SAFE_CSRF_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def admin_required(func: Callable[P, ResponseReturnValue]) -> Callable[P, ReturnType]:
    """确保被装饰函数仅允许管理员访问的装饰器.

    验证当前用户是否已认证且具有管理员角色.
    如果验证失败,根据请求类型返回 JSON 错误或重定向到登录页.

    Args:
        func: 被装饰的视图或业务函数.

    Returns:
        装饰后的函数.

    Raises:
        AuthenticationError: 当用户未认证时抛出(JSON 请求).
        AuthorizationError: 当用户权限不足时抛出(JSON 请求).

    """

    @wraps(func)
    def decorated_function(*args: P.args, **kwargs: P.kwargs) -> ReturnType:
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
        return func(*args, **kwargs)

    return decorated_function


def login_required(func: Callable[P, ResponseReturnValue]) -> Callable[P, ReturnType]:
    """要求调用者已登录的装饰器.

    Args:
        func: 原始视图函数.

    Returns:
        包装后的函数,若用户未登录将重定向或抛出异常.

    """

    @wraps(func)
    def decorated_function(*args: P.args, **kwargs: P.kwargs) -> ReturnType:
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
        return func(*args, **kwargs)

    return decorated_function


def permission_required(permission: str) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ReturnType]]:
    """校验指定权限(view/create/update/delete)的装饰器工厂.

    Args:
        permission: 需要验证的权限字符串.

    Returns:
        可装饰视图的校验器,未通过时会告警或抛出异常.

    """

    def decorator(func: Callable[P, ResponseReturnValue]) -> Callable[P, ReturnType]:
        @wraps(func)
        def decorated_function(*args: P.args, **kwargs: P.kwargs) -> ReturnType:
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
            if not has_permission(cast(PermissionUser, current_user), permission):
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
            return func(*args, **kwargs)

        return decorated_function

    return decorator


def _extract_csrf_token() -> str | None:
    """从请求头或表单中提取 CSRF 令牌.

    Returns:
        提取到的 CSRF 字符串,若不存在返回 None.

    """
    token = request.headers.get(CSRF_HEADER)
    if token:
        return token

    return request.form.get("csrf_token")


def require_csrf(func: Callable[P, ResponseReturnValue]) -> Callable[P, ReturnType]:
    """统一的 CSRF 校验装饰器.

    Args:
        func: 需要保护的视图函数.

    Returns:
        装饰后的函数,校验失败时抛出 AuthorizationError.

    """

    @wraps(func)
    def decorated_function(*args: P.args, **kwargs: P.kwargs) -> ReturnType:
        if request.method.upper() in SAFE_CSRF_METHODS:
            return func(*args, **kwargs)

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
            msg = "缺少 CSRF 令牌"
            raise AuthorizationError(
                msg,
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
            msg = "CSRF 令牌无效,请刷新后重试"
            raise AuthorizationError(
                msg,
                message_key="CSRF_INVALID",
                extra={
                    "request_path": request.path,
                    "request_method": request.method,
                },
            ) from exc

        return func(*args, **kwargs)

    return decorated_function


def has_permission(user: PermissionUser | None, permission: str) -> bool:
    """检查给定用户是否具备指定权限.

    Args:
        user: 当前用户对象.
        permission: 待验证的权限字符串.

    Returns:
        True 表示具有权限,False 表示缺失或未登录.

    """
    if not user or not user.is_authenticated:
        return False

    # 管理员拥有所有权限
    if user.role == UserRole.ADMIN:
        return True

    # 模拟从数据库或配置中加载的用户权限
    # 在真实应用中,这里应该查询数据库
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


@overload
def view_required(func: Callable[P, ResponseReturnValue], *, permission: str = "view") -> Callable[P, ReturnType]: ...


@overload
def view_required(
    func: None = None, *, permission: str = "view"
) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ReturnType]]: ...


def view_required(
    func: Callable[P, ResponseReturnValue] | None = None,
    *,
    permission: str = "view",
) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ReturnType]] | Callable[P, ReturnType]:
    """校验查看权限的装饰器,可直接使用或指定自定义权限.

    Args:
        func: 待装饰函数,支持无参直接使用.
        permission: 自定义权限名称,默认 `view`.

    Returns:
        满足 Flask 惰性装饰器模式的函数或装饰器.

    """
    if func is not None and not callable(func):
        permission = str(func)
        func = None

    def decorator(target: Callable[P, ResponseReturnValue]) -> Callable[P, ReturnType]:
        return permission_required(permission)(target)

    if func is not None:
        return decorator(func)
    return decorator


@overload
def create_required(
    func: Callable[P, ResponseReturnValue], *, permission: str = "create"
) -> Callable[P, ReturnType]: ...


@overload
def create_required(
    func: None = None, *, permission: str = "create"
) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ReturnType]]: ...


def create_required(
    func: Callable[P, ResponseReturnValue] | None = None,
    *,
    permission: str = "create",
) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ReturnType]] | Callable[P, ReturnType]:
    """校验创建权限的装饰器.

    Args:
        func: 待装饰函数.
        permission: 自定义权限名称,默认为 `create`.

    Returns:
        装饰器或已装饰函数.

    """

    def decorator(target: Callable[P, ResponseReturnValue]) -> Callable[P, ReturnType]:
        return permission_required(permission)(target)

    if func is not None:
        return decorator(func)
    return decorator


@overload
def update_required(
    func: Callable[P, ResponseReturnValue], *, permission: str = "update"
) -> Callable[P, ReturnType]: ...


@overload
def update_required(
    func: None = None, *, permission: str = "update"
) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ReturnType]]: ...


def update_required(
    func: Callable[P, ResponseReturnValue] | None = None,
    *,
    permission: str = "update",
) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ReturnType]] | Callable[P, ReturnType]:
    """校验更新权限的装饰器.

    Args:
        func: 待装饰函数.
        permission: 自定义权限名称,默认为 `update`.

    Returns:
        装饰器或已装饰函数.

    """

    def decorator(target: Callable[P, ResponseReturnValue]) -> Callable[P, ReturnType]:
        return permission_required(permission)(target)

    if func is not None:
        return decorator(func)
    return decorator


@overload
def delete_required(
    func: Callable[P, ResponseReturnValue], *, permission: str = "delete"
) -> Callable[P, ReturnType]: ...


@overload
def delete_required(
    func: None = None, *, permission: str = "delete"
) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ReturnType]]: ...


def delete_required(
    func: Callable[P, ResponseReturnValue] | None = None,
    *,
    permission: str = "delete",
) -> Callable[[Callable[P, ResponseReturnValue]], Callable[P, ReturnType]] | Callable[P, ReturnType]:
    """校验删除权限的装饰器.

    Args:
        func: 待装饰函数.
        permission: 自定义权限名称,默认为 `delete`.

    Returns:
        装饰器或已装饰函数.

    """

    def decorator(target: Callable[P, ResponseReturnValue]) -> Callable[P, ReturnType]:
        return permission_required(permission)(target)

    if func is not None:
        return decorator(func)
    return decorator


def scheduler_view_required(func: Callable[P, ResponseReturnValue]) -> Callable[P, ReturnType]:
    """定时任务查看权限装饰器.

    Args:
        func: 原始视图函数.

    Returns:
        添加 scheduler.view 权限校验后的函数.

    """
    return permission_required("scheduler.view")(func)


def scheduler_manage_required(func: Callable[P, ResponseReturnValue]) -> Callable[P, ReturnType]:
    """定时任务管理权限装饰器.

    Args:
        func: 原始视图函数.

    Returns:
        添加 scheduler.manage 权限校验后的函数.

    """
    return permission_required("scheduler.manage")(func)
