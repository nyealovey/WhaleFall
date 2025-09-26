
"""
鲸落 - 数据库类型管理路由
提供数据库类型的Web界面和API接口
"""

from flask import Blueprint, Response, jsonify
from flask_login import login_required

from app.services.database_type_service import DatabaseTypeService
from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

# 创建蓝图
database_types_bp = Blueprint("database_types", __name__)


@database_types_bp.route("/api/list")
@login_required
def api_list() -> "Response":
    """API: 获取数据库类型列表"""
    types = DatabaseTypeService.get_all_types()
    return jsonify({"success": True, "data": [config.to_dict() for config in types]})


@database_types_bp.route("/api/active")
@login_required
def api_active() -> "Response":
    """API: 获取启用的数据库类型"""
    types = DatabaseTypeService.get_active_types()
    return jsonify({"success": True, "data": [config.to_dict() for config in types]})


@database_types_bp.route("/api/form-options")
@login_required
def api_form_options() -> "Response":
    """API: 获取用于表单的数据库类型选项"""
    options = DatabaseTypeService.get_database_types_for_form()
    return jsonify({"success": True, "data": options})
