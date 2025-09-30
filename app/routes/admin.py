
"""
鲸落 - 管理API路由
提供系统配置和常量管理功能
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import Blueprint, Response
from flask_login import current_user, login_required  # type: ignore

from app.constants import UserRole
from app.utils.api_response import APIResponse

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)

# 创建管理蓝图
admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """管理员权限装饰器"""

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        if not current_user.is_authenticated:
            return APIResponse.error("请先登录", code=401)  # type: ignore

        if current_user.role != UserRole.ADMIN.value:
            return APIResponse.error("需要管理员权限", code=403)  # type: ignore

        return f(*args, **kwargs)

    return decorated_function  # type: ignore


@admin_bp.route("/api/app-info", methods=["GET"])
def app_info() -> Response:
    """获取应用信息（公开接口，用于右上角显示）"""
    try:
        return APIResponse.success(data={"app_name": "鲸落", "app_version": "1.1.0"})  # type: ignore

    except Exception as e:
        logger.error("获取应用信息失败: %s", e)
        return APIResponse.success(data={"app_name": "鲸落", "app_version": "1.1.0"})  # type: ignore


# 快速操作相关路由
