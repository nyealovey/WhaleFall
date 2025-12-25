"""鲸落 - 系统仪表板路由."""

import psutil
from flask import Blueprint, render_template, request
from flask_login import login_required
from flask_restx import marshal

from app import db
from app.constants.system_constants import SuccessMessages

# 移除SyncData导入,使用新的同步会话模型
from app.models.user import User
from app.routes.dashboard_restx_models import DASHBOARD_CHART_FIELDS
from app.routes.health import check_cache_health, check_database_health, get_system_uptime
from app.services.dashboard.dashboard_charts_service import get_chart_data
from app.services.statistics.account_statistics_service import (
    fetch_classification_overview,
    fetch_summary as fetch_account_summary,
)
from app.services.statistics.database_statistics_service import fetch_summary as fetch_database_summary
from app.services.statistics.instance_statistics_service import (
    fetch_capacity_summary,
    fetch_summary as fetch_instance_summary,
)
from app.utils.cache_utils import dashboard_cache
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils
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
        response_fields = {key: DASHBOARD_CHART_FIELDS[key] for key in charts.keys() if key in DASHBOARD_CHART_FIELDS}
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


@dashboard_cache(timeout=300)
def get_system_overview() -> dict:
    """获取系统概览数据 (缓存版本).

    聚合各模块的统计数据,包括用户、实例、账户、分类、容量和数据库信息.
    结果缓存 5 分钟.

    Returns:
        包含系统概览数据的字典.

    """
    db.session.rollback()

    total_users = User.query.count()
    account_summary = fetch_account_summary()
    classification_overview = fetch_classification_overview()
    instance_summary = fetch_instance_summary()
    database_summary = fetch_database_summary()
    capacity_summary = fetch_capacity_summary()

    log_info(
        "dashboard_base_counts",
        module="dashboard",
        total_users=total_users,
        total_instances=instance_summary["total_instances"],
        total_accounts=account_summary["total_accounts"],
        total_capacity_gb=capacity_summary["total_gb"],
        total_databases=database_summary["total_databases"],
        active_accounts=account_summary["active_accounts"],
        locked_accounts=account_summary["locked_accounts"],
        active_databases=database_summary["active_databases"],
    )

    log_info(
        "dashboard_classification_counts",
        module="dashboard",
        classifications=len(classification_overview["classifications"]),
        total_classified_accounts=classification_overview["total"],
        auto_classified_accounts=classification_overview["auto"],
    )

    log_info(
        "dashboard_active_counts",
        module="dashboard",
        total_accounts=account_summary["total_accounts"],
        active_accounts=account_summary["active_accounts"],
        active_instances=instance_summary["active_instances"],
    )

    time_utils.now_china().date()

    return {
        "users": {"total": total_users, "active": total_users},
        "instances": {
            "total": instance_summary["total_instances"],
            "active": instance_summary["active_instances"],
        },
        "accounts": {
            "total": account_summary["total_accounts"],
            "active": account_summary["active_accounts"],
            "locked": account_summary["locked_accounts"],
        },
        "classified_accounts": classification_overview,
        "capacity": capacity_summary,
        "databases": {
            "total": database_summary["total_databases"],
            "active": database_summary["active_databases"],
            "inactive": database_summary["inactive_databases"],
        },
    }


@dashboard_cache(timeout=30)
def get_system_status() -> dict:
    """获取系统状态.

    检查系统资源使用情况 (CPU、内存、磁盘) 和服务健康状态 (数据库、Redis).
    结果缓存 30 秒.

    Returns:
        包含系统状态信息的字典.

    """
    cpu_percent = psutil.cpu_percent(interval=None)
    if cpu_percent == 0.0:
        cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    db_status_info = check_database_health()
    db_status = "healthy" if db_status_info.get("healthy") else "error"

    cache_status_info = check_cache_health()
    redis_status = "healthy" if cache_status_info.get("healthy") else "error"

    return {
        "system": {
            "cpu": cpu_percent,
            "memory": {
                "used": memory.used,
                "total": memory.total,
                "percent": memory.percent,
            },
            "disk": {
                "used": disk.used,
                "total": disk.total,
                "percent": disk.percent,
            },
        },
        "services": {
            "database": db_status,
            "redis": redis_status,
        },
        "uptime": get_system_uptime(),
    }
