"""鲸落 - 系统仪表板路由."""

from flask import Blueprint, render_template, request
from flask_login import login_required
from app.constants.system_constants import SuccessMessages
from app.services.dashboard.dashboard_charts_service import get_chart_data
from app.services.dashboard.dashboard_overview_service import get_system_overview, get_system_status
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.types import RouteReturn

# 创建蓝图
dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index() -> RouteReturn:
    """系统仪表板首页.

    渲染系统概览页面,展示实例、账户、容量等统计信息和图表.

    Returns:
        渲染后的 HTML 页面或 JSON 响应 (根据请求类型).

    """

    def _execute() -> RouteReturn:
        overview_data = get_system_overview()
        chart_data = get_chart_data()
        system_status = get_system_status()

        if request.is_json:
            return jsonify_unified_success(
                data={
                    "overview": overview_data,
                    "charts": chart_data,
                    "status": system_status,
                },
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return render_template(
            "dashboard/overview.html",
            overview=overview_data,
            charts=chart_data,
            status=system_status,
        )

    return safe_route_call(
        _execute,
        module="dashboard",
        action="index",
        public_error="加载仪表板失败",
        context={"accept_json": request.is_json},
    )
