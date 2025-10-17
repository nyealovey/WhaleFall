"""鲸落 - 数据库类型管理路由"""

from flask import Blueprint, Response
from flask_login import login_required

from app.errors import SystemError
from app.services.database_type_service import DatabaseTypeService
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
database_types_bp = Blueprint("database_types", __name__)


@database_types_bp.route("/api/list")
@login_required
def api_list() -> Response:
    """API: 获取数据库类型列表"""
    try:
        types = DatabaseTypeService.get_all_types()
        payload = [config.to_dict() for config in types]
        log_info("获取数据库类型列表成功", module="database_types", count=len(payload))
        return jsonify_unified_success(data={"database_types": payload}, message="数据库类型列表获取成功")
    except Exception as exc:
        log_error("获取数据库类型列表失败", module="database_types", error=str(exc))
        raise SystemError("获取数据库类型列表失败") from exc


@database_types_bp.route("/api/active")
@login_required
def api_active() -> Response:
    """API: 获取启用的数据库类型"""
    try:
        types = DatabaseTypeService.get_active_types()
        payload = [config.to_dict() for config in types]
        log_info("获取启用数据库类型成功", module="database_types", count=len(payload))
        return jsonify_unified_success(data={"database_types": payload}, message="启用数据库类型获取成功")
    except Exception as exc:
        log_error("获取启用数据库类型失败", module="database_types", error=str(exc))
        raise SystemError("获取启用数据库类型失败") from exc


@database_types_bp.route("/api/form-options")
@login_required
def api_form_options() -> Response:
    """API: 获取用于表单的数据库类型选项"""
    try:
        options = DatabaseTypeService.get_database_types_for_form()
        log_info("获取数据库类型表单选项成功", module="database_types", count=len(options))
        return jsonify_unified_success(data={"options": options}, message="数据库类型表单选项获取成功")
    except Exception as exc:
        log_error("获取数据库类型表单选项失败", module="database_types", error=str(exc))
        raise SystemError("获取数据库类型表单选项失败") from exc
