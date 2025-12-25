"""实例容量与统计相关接口."""

from flask_restx import marshal
from flask import flash, render_template
from flask_login import login_required

from app.constants import FlashCategory
from app.errors import SystemError
from app.routes.instances.manage import instances_bp
from app.routes.instances.restx_models import INSTANCE_STATISTICS_FIELDS
from app.services.instances.instance_statistics_read_service import InstanceStatisticsReadService
from app.types import RouteReturn
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call


@instances_bp.route("/statistics")
@login_required
@view_required
def statistics() -> RouteReturn:
    """实例统计页面.

    Returns:
        str: 渲染后的统计页面.

    """

    def _load() -> dict:
        return InstanceStatisticsReadService().build_statistics()

    try:
        stats = safe_route_call(
            _load,
            module="instances",
            action="statistics_page",
            public_error="获取实例统计信息失败",
            context={"endpoint": "instances_statistics_page"},
        )
    except SystemError:
        stats = InstanceStatisticsReadService.empty_statistics()
        flash("获取实例统计信息失败,请稍后重试", FlashCategory.ERROR)
    return render_template("instances/statistics.html", stats=stats)


@instances_bp.route("/api/statistics")
@login_required
@view_required
def get_instance_statistics() -> RouteReturn:
    """获取实例统计 API.

    Returns:
        Response: 包含统计数据的 JSON.

    """

    def _execute() -> RouteReturn:
        result = InstanceStatisticsReadService().build_statistics()
        payload = marshal(result, INSTANCE_STATISTICS_FIELDS)
        return jsonify_unified_success(data=payload, message="获取实例统计信息成功")

    return safe_route_call(
        _execute,
        module="instances",
        action="get_instance_statistics",
        public_error="获取实例统计信息失败",
        context={"endpoint": "instances_statistics_api"},
    )
