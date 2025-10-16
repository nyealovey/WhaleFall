
"""
鲸落 - 管理API路由
提供系统配置和常量管理功能
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import Blueprint, Response, request
from flask_login import current_user, login_required  # type: ignore

from app.constants import UserRole
from app.constants.system_constants import ErrorMessages
from app.errors import AuthenticationError, AuthorizationError
from app.utils.response_utils import jsonify_unified_success

F = TypeVar("F", bound=Callable[..., Any])

# 创建管理蓝图
admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """管理员权限装饰器"""

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
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

        if current_user.role != UserRole.ADMIN.value:
            raise AuthorizationError(
                ErrorMessages.ADMIN_PERMISSION_REQUIRED,
                message_key="ADMIN_PERMISSION_REQUIRED",
                extra={
                    "request_path": request.path,
                    "request_method": request.method,
                    "user_role": current_user.role,
                },
            )

        return f(*args, **kwargs)

    return decorated_function  # type: ignore


@admin_bp.route("/api/app-info", methods=["GET"])
def app_info() -> tuple[Response, int]:
    """获取应用信息（公开接口，用于右上角显示）"""
    return jsonify_unified_success(data={"app_name": "鲸落", "app_version": "1.1.2"})


# 快速操作相关路由
