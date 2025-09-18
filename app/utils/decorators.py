"""
泰摸鱼吧 - 装饰器工具
"""

from functools import wraps
from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.utils.structlog_config import get_system_logger


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
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "请先登录",
                            "code": "UNAUTHORIZED",
                        }
                    ),
                    401,
                )
            from flask import flash, redirect, url_for

            flash("请先登录", "warning")
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
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "需要管理员权限",
                            "code": "FORBIDDEN",
                        }
                    ),
                    403,
                )
            from flask import flash, redirect, url_for

            flash("需要管理员权限", "error")
            return redirect(url_for("main.index"))

        # 只在调试模式下记录成功验证
        if system_logger.isEnabledFor(10):  # DEBUG level
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


def scheduler_manage_required(f: Any) -> Any:  # noqa: ANN401
    """
    定时任务管理权限装饰器
    只有管理员可以管理定时任务（创建、编辑、删除、启用/禁用、运行）

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
                "未认证访问任务管理功能",
                module="decorators",
                user_id=None,
                request_path=request.path,
                request_method=request.method,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
                permission_type="scheduler_manage",
                failure_reason="not_authenticated",
            )
            if request.is_json:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "请先登录",
                            "code": "UNAUTHORIZED",
                        }
                    ),
                    401,
                )
            from flask import flash, redirect, url_for

            flash("请先登录", "warning")
            return redirect(url_for("auth.login"))

        if not current_user.is_admin():
            system_logger.warning(
                "权限不足访问任务管理功能",
                module="decorators",
                user_id=current_user.id,
                username=current_user.username,
                user_role=current_user.role,
                request_path=request.path,
                request_method=request.method,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
                permission_type="scheduler_manage",
                failure_reason="insufficient_permissions",
            )
            if request.is_json:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "需要管理员权限才能管理定时任务",
                            "code": "FORBIDDEN",
                        }
                    ),
                    403,
                )
            from flask import flash, redirect, url_for

            flash("需要管理员权限才能管理定时任务", "error")
            return redirect(url_for("main.index"))

        # 只在调试模式下记录成功验证
        if system_logger.isEnabledFor(10):  # DEBUG level
            system_logger.debug(
                "任务管理权限验证通过",
                module="decorators",
                user_id=current_user.id,
                username=current_user.username,
                request_path=request.path,
                request_method=request.method,
                permission_type="scheduler_manage",
            )
        return f(*args, **kwargs)

    return decorated_function


def scheduler_view_required(f: Any) -> Any:  # noqa: ANN401
    """
    定时任务查看权限装饰器
    普通用户可以查看定时任务状态，但不能操作

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
                "未认证访问任务查看功能",
                module="decorators",
                user_id=None,
                request_path=request.path,
                request_method=request.method,
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
                permission_type="scheduler_view",
                failure_reason="not_authenticated",
            )
            if request.is_json:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "请先登录",
                            "code": "UNAUTHORIZED",
                        }
                    ),
                    401,
                )
            from flask import flash, redirect, url_for

            flash("请先登录", "warning")
            return redirect(url_for("auth.login"))

        # 只在调试模式下记录成功验证
        if system_logger.isEnabledFor(10):  # DEBUG level
            system_logger.debug(
                "任务查看权限验证通过",
                module="decorators",
                user_id=current_user.id,
                username=current_user.username,
                request_path=request.path,
                request_method=request.method,
                permission_type="scheduler_view",
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
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "请先登录",
                            "code": "UNAUTHORIZED",
                        }
                    ),
                    401,
                )
            from flask import flash, redirect, url_for

            flash("请先登录", "warning")
            return redirect(url_for("auth.login"))

        # 只在调试模式下记录成功验证
        if system_logger.isEnabledFor(10):  # DEBUG level
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


def login_required_json(f: Any) -> Any:  # noqa: ANN401
    """
    JSON API登录装饰器

    Args:
        f: 被装饰的函数

    Returns:
        装饰后的函数
    """

    @wraps(f)
    def decorated_function(*args, **kwargs: Any) -> Any:  # noqa: ANN401
        if not current_user.is_authenticated:
            return (
                jsonify({"success": False, "message": "请先登录", "code": "UNAUTHORIZED"}),
                401,
            )

        return f(*args, **kwargs)

    return decorated_function


def rate_limit(requests_per_minute: int = 60) -> Any:  # noqa: ANN401
    """
    速率限制装饰器

    Args:
        requests_per_minute: 每分钟请求次数限制

    Returns:
        装饰器函数
    """

    def decorator(f: Any) -> Any:  # noqa: ANN401
        @wraps(f)
        def decorated_function(*args, **kwargs: Any) -> Any:  # noqa: ANN401
            # 这里可以集成速率限制逻辑
            # 目前只是简单实现
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def validate_json(required_fields: list[str] | None = None) -> Any:  # noqa: ANN401
    """
    JSON数据验证装饰器

    Args:
        required_fields: 必需字段列表

    Returns:
        装饰器函数
    """

    def decorator(f: Any) -> Any:  # noqa: ANN401
        @wraps(f)
        def decorated_function(*args, **kwargs: Any) -> Any:  # noqa: ANN401
            if not request.is_json:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "请求必须是JSON格式",
                            "code": "INVALID_CONTENT_TYPE",
                        }
                    ),
                    400,
                )

            data = request.get_json()
            if not data:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "请求数据不能为空",
                            "code": "EMPTY_DATA",
                        }
                    ),
                    400,
                )

            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": f"缺少必需字段: {', '.join(missing_fields)}",
                                "code": "MISSING_FIELDS",
                            }
                        ),
                        400,
                    )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


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
                    "未认证访问%s权限资源",
                    permission,
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
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "请先登录",
                                "code": "UNAUTHORIZED",
                            }
                        ),
                        401,
                    )
                from flask import flash, redirect, url_for

                flash("请先登录", "warning")
                return redirect(url_for("auth.login"))

            # 检查权限
            if not has_permission(current_user, permission):
                system_logger.warning(
                    "权限不足访问%s权限资源",
                    permission,
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
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": f"需要{permission}权限",
                                "code": "FORBIDDEN",
                            }
                        ),
                        403,
                    )
                from flask import flash, redirect, url_for

                flash(f"需要{permission}权限", "error")
                return redirect(url_for("main.index"))

            # 只在调试模式下记录成功验证
            if system_logger.isEnabledFor(10):  # DEBUG level
                system_logger.debug(
                    "%s权限验证通过",
                    permission,
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


def has_permission(user: Any, permission: str) -> bool:  # noqa: ANN401
    """
    检查用户是否有指定权限

    Args:
        user: 用户对象
        permission: 权限名称

    Returns:
        bool: 是否有权限
    """
    # 权限级别定义

    # 角色权限映射
    ROLE_PERMISSIONS = {
        "admin": ["view", "create", "update", "delete"],
        "user": ["view"],
    }  # 普通用户只能查看

    if not user or not user.is_authenticated:
        return False

    # 管理员拥有所有权限
    if user.role == "admin":
        return True

    # 检查用户角色是否有该权限
    user_permissions = ROLE_PERMISSIONS.get(user.role, [])
    return permission in user_permissions


def view_required(f: Any) -> Any:  # noqa: ANN401
    """查看权限装饰器"""
    return permission_required("view")(f)


def create_required(f: Any) -> Any:  # noqa: ANN401
    """创建权限装饰器"""
    return permission_required("create")(f)


def update_required(f: Any) -> Any:  # noqa: ANN401
    """更新权限装饰器"""
    return permission_required("update")(f)


def delete_required(f: Any) -> Any:  # noqa: ANN401
    """删除权限装饰器"""
    return permission_required("delete")(f)
