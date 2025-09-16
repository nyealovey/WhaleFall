"""
泰摸鱼吧 - 数据库类型管理路由
提供数据库类型的Web界面和API接口
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app.services.database_type_service import DatabaseTypeService

database_types_bp = Blueprint("database_types", __name__, url_prefix="/database-types")


@database_types_bp.route("/")
@login_required
def index() -> str:
    """数据库类型管理首页"""
    types = DatabaseTypeService.get_all_types()
    return render_template("database_types/list.html", types=types)


@database_types_bp.route("/create", methods=["GET", "POST"])
@login_required
def create() -> "Response":
    """创建数据库类型 - 已禁用"""
    if request.is_json:
        return jsonify({"success": False, "message": "数据库类型管理功能已禁用"}), 403
    flash("数据库类型管理功能已禁用", "error")
    return redirect(url_for("database_types.index"))


@database_types_bp.route("/<int:type_id>/edit", methods=["GET", "POST"])
@login_required
def edit(type_id: int) -> "Response":
    """编辑数据库类型 - 已禁用"""
    if request.is_json:
        return jsonify({"success": False, "message": "数据库类型管理功能已禁用"}), 403
    flash("数据库类型管理功能已禁用", "error")
    return redirect(url_for("database_types.index"))


@database_types_bp.route("/<int:type_id>/delete", methods=["POST"])
@login_required
def delete(type_id: int) -> "Response":
    """删除数据库类型 - 已禁用"""
    if request.is_json:
        return jsonify({"success": False, "message": "数据库类型管理功能已禁用"}), 403
    flash("数据库类型管理功能已禁用", "error")
    return redirect(url_for("database_types.index"))


@database_types_bp.route("/<int:type_id>/toggle", methods=["POST"])
@login_required
def toggle_status(type_id: int) -> "Response":
    """切换启用状态 - 已禁用"""
    return jsonify({"success": False, "message": "数据库类型管理功能已禁用"}), 403


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


@database_types_bp.route("/init-defaults", methods=["POST"])
@login_required
def init_defaults() -> "Response":
    """初始化默认数据库类型 - 已禁用"""
    return jsonify({"success": False, "message": "数据库类型管理功能已禁用"}), 403
