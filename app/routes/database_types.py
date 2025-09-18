"""
鲸落 - 数据库类型管理路由
提供数据库类型的Web界面和API接口
"""

from flask import Blueprint, Response, jsonify, render_template
from flask_login import login_required

from app.services.database_type_service import DatabaseTypeService
from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

database_types_bp = Blueprint("database_types", __name__, url_prefix="/database-types")


@database_types_bp.route("/")
@login_required
def index() -> str:
    """数据库类型管理首页"""
    types = DatabaseTypeService.get_all_types()
    return render_template("database_types/list.html", types=types)


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
