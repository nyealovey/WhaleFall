
"""
鲸落 - 管理API路由
提供系统配置和常量管理功能
"""

from flask import Blueprint, Response

from app.utils.response_utils import jsonify_unified_success

# 创建管理蓝图
admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/api/app-info", methods=["GET"])
def app_info() -> tuple[Response, int]:
    """获取应用信息（公开接口，用于右上角显示）"""
    return jsonify_unified_success(data={"app_name": "鲸落", "app_version": "1.1.2"})


# 快速操作相关路由
