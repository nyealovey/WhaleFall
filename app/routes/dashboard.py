"""鲸落 - 系统仪表板路由."""

from flask import Blueprint, render_template, request
from flask_login import login_required
from flask_restx import marshal

from app.constants.system_constants import SuccessMessages

from app.routes.dashboard_restx_models import DASHBOARD_CHART_FIELDS
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


@dashboard_bp.route("/api/overview")
@login_required
def get_dashboard_overview() -> RouteReturn:
    """获取系统概览 API.

    返回系统的统计概览数据,包括用户、实例、账户、容量等信息.

    Returns:
        包含系统概览数据的 JSON 响应.

    """

    def _execute() -> RouteReturn:
        overview = get_system_overview()
        return jsonify_unified_success(
            data=overview,
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    return safe_route_call(
        _execute,
        module="dashboard",
        action="get_dashboard_overview",
        public_error="获取系统概览失败",
    )


@dashboard_bp.route("/api/charts")
@login_required
def get_dashboard_charts() -> RouteReturn:
    """获取仪表板图表数据.

    Returns:
        Response: 图表数据 JSON.

    """
    chart_type = request.args.get("type", "all", type=str)

    def _execute() -> RouteReturn:
        charts = get_chart_data(chart_type)
        response_fields = {key: DASHBOARD_CHART_FIELDS[key] for key in charts if key in DASHBOARD_CHART_FIELDS}
        payload = marshal(charts, response_fields)
        return jsonify_unified_success(
            data=payload,
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    return safe_route_call(
        _execute,
        module="dashboard",
        action="get_dashboard_charts",
        public_error="获取仪表板图表失败",
        context={"chart_type": chart_type},
    )


@dashboard_bp.route("/api/activities")
@login_required
def list_dashboard_activities() -> RouteReturn:
    """获取最近活动 API (已废弃).

    Returns:
        Response: 空数组和成功消息.

    """
    return safe_route_call(
        lambda: jsonify_unified_success(data=[], message=SuccessMessages.OPERATION_SUCCESS),
        module="dashboard",
        action="list_dashboard_activities",
        public_error="获取仪表板活动失败",
    )


@dashboard_bp.route("/api/status")
@login_required
def get_dashboard_status() -> RouteReturn:
    """获取系统状态 API.

    Returns:
        Response: 包含资源占用与服务健康的 JSON.

    """

    def _execute() -> RouteReturn:
        status = get_system_status()
        return jsonify_unified_success(
            data=status,
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    return safe_route_call(
        _execute,
        module="dashboard",
        action="get_dashboard_status",
        public_error="获取系统状态失败",
    )
