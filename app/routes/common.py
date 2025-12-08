"""通用 API 路由
提供跨模块使用的通用接口.
"""

from flask import Blueprint, Response, request
from flask_login import login_required
from sqlalchemy import func

from app.errors import SystemError, ValidationError
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.services.database_type_service import DatabaseTypeService
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
common_bp = Blueprint("common", __name__)


@common_bp.route("/api/instances-options", methods=["GET"])
@login_required
@view_required
def get_instance_options() -> Response:
    """获取实例下拉选项(通用).

    Args:
        db_type: 请求参数,可选的数据库类型筛选.

    Returns:
        Response: 含实例选项列表的 JSON 响应.

    """
    try:
        db_type = request.args.get("db_type")

        query = Instance.query.filter(Instance.is_active.is_(True))
        if db_type:
            db_type_lower = db_type.lower()
            query = query.filter(func.lower(Instance.db_type) == db_type_lower)

        instances = query.order_by(Instance.name.asc()).all()

        options = [
            {
                "id": instance.id,
                "name": instance.name,
                "db_type": instance.db_type,
                "display_name": f"{instance.name} ({instance.db_type.upper()})",
            }
            for instance in instances
        ]

        log_info("加载实例选项成功", module="common", count=len(options), db_type=db_type)
        return jsonify_unified_success(data={"instances": options}, message="实例选项获取成功")

    except Exception as exc:
        log_error("加载实例选项失败", module="common", error=str(exc))
        msg = "加载实例选项失败"
        raise SystemError(msg) from exc


@common_bp.route("/api/databases-options", methods=["GET"])
@login_required
@view_required
def get_database_options() -> Response:
    """获取指定实例的数据库下拉选项(通用).

    Args:
        instance_id: 请求参数,必填的实例ID.
        limit: 请求参数,返回数量(默认100).
        offset: 请求参数,数据偏移量(默认0).

    Returns:
        Response: 包含数据库列表及分页信息的 JSON 响应.

    """
    instance_id = request.args.get("instance_id", type=int)
    if not instance_id:
        msg = "instance_id 为必填参数"
        raise ValidationError(msg)

    Instance.query.get_or_404(instance_id)

    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except ValueError as exc:
        msg = "limit/offset 必须为整数"
        raise ValidationError(msg) from exc

    try:
        query = (
            InstanceDatabase.query.filter(InstanceDatabase.instance_id == instance_id)
            .order_by(InstanceDatabase.database_name)
        )
        total_count = query.count()
        databases = query.offset(offset).limit(limit).all()
    except Exception as exc:
        log_error(
            "获取实例数据库列表失败",
            module="common",
            instance_id=instance_id,
            error=str(exc),
        )
        msg = "获取实例数据库列表失败"
        raise SystemError(msg) from exc

    data = [
        {
            "id": db.id,
            "database_name": db.database_name,
            "is_active": db.is_active,
            "first_seen_date": db.first_seen_date.isoformat() if db.first_seen_date else None,
            "last_seen_date": db.last_seen_date.isoformat() if db.last_seen_date else None,
            "deleted_at": db.deleted_at.isoformat() if db.deleted_at else None,
        }
        for db in databases
    ]

    payload = {
        "databases": data,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }

    log_info(
        "加载数据库选项成功",
        module="common",
        instance_id=instance_id,
        count=len(data),
    )
    return jsonify_unified_success(data=payload, message="数据库选项获取成功")


@common_bp.route("/api/dbtypes-options", methods=["GET"])
@login_required
@view_required
def get_database_type_options() -> Response:
    """获取数据库类型选项(通用).

    Returns:
        Response: 含数据库类型配置的 JSON 响应.

    """
    try:
        options = DatabaseTypeService.get_database_types_for_form()
        log_info("加载数据库类型选项成功", module="common", count=len(options))
        return jsonify_unified_success(data={"options": options}, message="数据库类型选项获取成功")
    except Exception as exc:
        log_error("加载数据库类型选项失败", module="common", error=str(exc))
        msg = "加载数据库类型选项失败"
        raise SystemError(msg) from exc
