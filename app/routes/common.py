"""通用 API 路由.

提供跨模块使用的通用接口.
"""

from flask import Blueprint, Response, request
from flask_login import login_required
from flask_restx import marshal

from app.errors import SystemError, ValidationError
from app.models.instance import Instance
from app.routes.common_restx_models import (
    COMMON_DATABASES_OPTIONS_RESPONSE_FIELDS,
    COMMON_DBTYPES_OPTIONS_RESPONSE_FIELDS,
    COMMON_INSTANCES_OPTIONS_RESPONSE_FIELDS,
)
from app.services.common.filter_options_service import FilterOptionsService
from app.types.common_filter_options import CommonDatabasesOptionsFilters
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info

# 创建蓝图
common_bp = Blueprint("common", __name__)
_filter_options_service = FilterOptionsService()


@common_bp.route("/api/instances-options", methods=["GET"])
@login_required
@view_required
def get_instance_options() -> tuple[Response, int]:
    """获取实例下拉选项(通用).

    Args:
        db_type: 请求参数,可选的数据库类型筛选.

    Returns:
        Response: 含实例选项列表的 JSON 响应.

    """

    def _execute() -> tuple[Response, int]:
        db_type = request.args.get("db_type")
        result = _filter_options_service.get_common_instances_options(db_type=db_type)
        payload = marshal(result, COMMON_INSTANCES_OPTIONS_RESPONSE_FIELDS)

        log_info("加载实例选项成功", module="common", count=len(result.instances), db_type=db_type)
        return jsonify_unified_success(data=payload, message="实例选项获取成功")

    return safe_route_call(
        _execute,
        module="common",
        action="get_instance_options",
        public_error="加载实例选项失败",
        context={"endpoint": "instances-options"},
        expected_exceptions=(SystemError,),
    )


@common_bp.route("/api/databases-options", methods=["GET"])
@login_required
@view_required
def get_database_options() -> tuple[Response, int]:
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

    def _execute() -> tuple[Response, int]:
        try:
            limit = int(request.args.get("limit", 100))
            offset = int(request.args.get("offset", 0))
        except ValueError as exc:
            msg = "limit/offset 必须为整数"
            raise ValidationError(msg) from exc

        result = _filter_options_service.get_common_databases_options(
            CommonDatabasesOptionsFilters(
                instance_id=instance_id,
                limit=limit,
                offset=offset,
            ),
        )
        payload = marshal(result, COMMON_DATABASES_OPTIONS_RESPONSE_FIELDS)

        log_info(
            "加载数据库选项成功",
            module="common",
            instance_id=instance_id,
            count=len(result.databases),
        )
        return jsonify_unified_success(data=payload, message="数据库选项获取成功")

    return safe_route_call(
        _execute,
        module="common",
        action="get_database_options",
        public_error="获取实例数据库列表失败",
        context={"instance_id": instance_id},
        expected_exceptions=(ValidationError, SystemError),
    )


@common_bp.route("/api/dbtypes-options", methods=["GET"])
@login_required
@view_required
def get_database_type_options() -> tuple[Response, int]:
    """获取数据库类型选项(通用).

    Returns:
        Response: 含数据库类型配置的 JSON 响应.

    """

    def _execute() -> tuple[Response, int]:
        result = _filter_options_service.get_common_database_types_options()
        payload = marshal(result, COMMON_DBTYPES_OPTIONS_RESPONSE_FIELDS)

        log_info("加载数据库类型选项成功", module="common", count=len(result.options))
        return jsonify_unified_success(data=payload, message="数据库类型选项获取成功")

    return safe_route_call(
        _execute,
        module="common",
        action="get_database_type_options",
        public_error="加载数据库类型选项失败",
        context={"endpoint": "dbtypes-options"},
        expected_exceptions=(SystemError,),
    )
