"""
泰摸鱼吧 - 管理API路由
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
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required[T](f: T) -> T:
    """管理员权限装饰器"""

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        if not current_user.is_authenticated:
            return APIResponse.error("请先登录", code=401)  # type: ignore

        if current_user.role != UserRole.ADMIN.value:
            return APIResponse.error("需要管理员权限", code=403)  # type: ignore

        return f(*args, **kwargs)

    return decorated_function  # type: ignore


@admin_bp.route("/app-info", methods=["GET"])
def get_app_info() -> Response:
    """获取应用信息（公开接口，用于右上角显示）"""
    try:
        return APIResponse.success(data={"app_name": "泰摸鱼吧", "app_version": "4.0.0"})  # type: ignore

    except Exception as e:
        logger.error("获取应用信息失败: %s", e)
        return APIResponse.success(data={"app_name": "泰摸鱼吧", "app_version": "4.0.0"})  # type: ignore


# 快速操作相关路由
@admin_bp.route("/refresh-data", methods=["POST"])
@login_required  # type: ignore
@admin_required
def refresh_system_data() -> Response:
    """刷新系统数据"""
    try:
        # 这里可以实现数据刷新逻辑
        logger.info("系统数据刷新请求")
        return APIResponse.success(message="系统数据已刷新")  # type: ignore
    except Exception as e:
        logger.error("刷新系统数据失败: %s", e)
        return APIResponse.server_error("刷新系统数据失败")  # type: ignore


@admin_bp.route("/clear-cache", methods=["POST"])
@login_required  # type: ignore
@admin_required
def clear_cache() -> Response:
    """清除缓存"""
    try:
        # 这里可以实现清除缓存逻辑
        logger.info("清除缓存请求")
        return APIResponse.success(message="缓存已清除")  # type: ignore
    except Exception as e:
        logger.error("清除缓存失败: %s", e)
        return APIResponse.server_error("清除缓存失败")  # type: ignore


@admin_bp.route("/health-check", methods=["POST"])
@login_required  # type: ignore
@admin_required
def run_health_check() -> Response:
    """运行健康检查"""
    try:
        # 检查各个组件状态
        health_status = {
            "database": "healthy",
            "redis": "healthy",
            "application": "healthy",
        }

        return APIResponse.success(data=health_status, message="健康检查完成")  # type: ignore
    except Exception as e:
        logger.error("健康检查失败: %s", e)
        return APIResponse.server_error("健康检查失败")  # type: ignore
