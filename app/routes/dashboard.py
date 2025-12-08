
"""
鲸落 - 系统仪表板路由
"""

from datetime import datetime, timedelta, date

import psutil
from flask import Blueprint, Response, render_template, request
from flask_login import login_required
from sqlalchemy import and_, func, or_, text, case

from app import db
from app.constants.system_constants import SuccessMessages
from app.constants import TaskStatus
from app.models.instance import Instance
from app.services.statistics.account_statistics_service import (
    fetch_classification_overview,
    fetch_summary as fetch_account_summary,
)
from app.services.statistics.database_statistics_service import fetch_summary as fetch_database_summary
from app.services.statistics.instance_statistics_service import (
    fetch_capacity_summary,
    fetch_summary as fetch_instance_summary,
)
from app.services.statistics.log_statistics_service import (
    fetch_log_level_distribution,
    fetch_log_trend_data,
)

# 移除SyncData导入，使用新的同步会话模型
from app.models.user import User
from app.routes.health import get_system_uptime
from app.utils.cache_utils import dashboard_cache
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import CHINA_TZ, time_utils
from app.scheduler import get_scheduler
from app.routes.health import check_database_health, check_cache_health

# 创建蓝图
dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index() -> str:
    """系统仪表板首页。

    渲染系统概览页面，展示实例、账户、容量等统计信息和图表。

    Returns:
        渲染后的 HTML 页面或 JSON 响应（根据请求类型）。

    """
    import time

    start_time = time.time()

    # 获取系统概览数据
    overview_data = get_system_overview()

    # 获取图表数据
    chart_data = get_chart_data()

    # 获取系统状态
    system_status = get_system_status()

    # 记录操作日志（仅记录重要操作）

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


@dashboard_bp.route("/api/overview")
@login_required
def get_dashboard_overview() -> "Response":
    """获取系统概览 API。

    返回系统的统计概览数据，包括用户、实例、账户、容量等信息。

    Returns:
        包含系统概览数据的 JSON 响应。

    """
    import time

    start_time = time.time()

    overview = get_system_overview()

    # 注释掉频繁的日志记录，减少日志噪音
    # duration = (time.time() - start_time) * 1000
    # log_info(
    #     "获取仪表板概览数据",
    #     module="dashboard",
    #     user_id=current_user.id,
    #     ip_address=request.remote_addr,
    #     duration_ms=duration,
    # )

    return jsonify_unified_success(
        data=overview,
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@dashboard_bp.route("/api/charts")
@login_required
def get_dashboard_charts() -> "Response":
    """获取仪表板图表数据。

    Returns:
        Response: 图表数据 JSON。

    """
    import time

    start_time = time.time()

    chart_type = request.args.get("type", "all", type=str)
    charts = get_chart_data(chart_type)

    # 注释掉频繁的日志记录，减少日志噪音
    # duration = (time.time() - start_time) * 1000
    # log_info(
    #     "获取仪表板图表数据",
    #     module="dashboard",
    #     user_id=current_user.id,
    #     ip_address=request.remote_addr,
    #     duration_ms=duration,
    # )

    return jsonify_unified_success(
        data=charts,
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@dashboard_bp.route("/api/activities")
@login_required
def list_dashboard_activities() -> "Response":
    """获取最近活动 API（已废弃）。

    Returns:
        Response: 空数组和成功消息。

    """
    return jsonify_unified_success(
        data=[],
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@dashboard_bp.route("/api/status")
@login_required
def get_dashboard_status() -> "Response":
    """获取系统状态 API。

    Returns:
        Response: 包含资源占用与服务健康的 JSON。

    """
    status = get_system_status()

    # 移除用户查看操作的日志记录

    return jsonify_unified_success(
        data=status,
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@dashboard_cache(timeout=300)
def get_system_overview() -> dict:
    """获取系统概览数据（缓存版本）。

    聚合各模块的统计数据，包括用户、实例、账户、分类、容量和数据库信息。
    结果缓存 5 分钟。

    Returns:
        包含系统概览数据的字典。

    """
    try:
        db.session.rollback()
        # 基础统计
        total_users = User.query.count()
        account_summary = fetch_account_summary()
        classification_overview = fetch_classification_overview()
        instance_summary = fetch_instance_summary()
        database_summary = fetch_database_summary()
        capacity_summary = fetch_capacity_summary()
        from app.models.unified_log import LogLevel, UnifiedLog

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

        # 最近同步数据（东八区） - 使用新的同步会话模型

        china_today = time_utils.now_china().date()

        return {
            "users": {"total": total_users, "active": total_users},  # 简化处理
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
    except Exception as e:
        db.session.rollback()
        log_error(f"获取系统概览失败: {e}", module="dashboard")
        return {
            "users": {"total": 0, "active": 0},
            "instances": {"total": 0, "active": 0},
            "accounts": {"total": 0, "active": 0, "locked": 0},
            "classified_accounts": {"total": 0, "auto": 0, "classifications": []},
            "capacity": {"total_gb": 0, "usage_percent": 0},
            "databases": {"total": 0, "active": 0, "inactive": 0},
        }


@dashboard_cache(timeout=180)
def get_chart_data(chart_type: str = "all") -> dict:
    """获取图表数据。

    Args:
        chart_type: 需要获取的图表类型（all/logs/tasks/syncs）。

    Returns:
        dict: 包含日志、任务、同步等图表数据的字典。

    """
    try:
        chart_type = (chart_type or "all").lower()
        charts = {}

        if chart_type in {"all", "logs"}:
            # 日志趋势图（最近7天）
            charts["log_trend"] = get_log_trend_data()

            # 日志级别分布
            charts["log_levels"] = get_log_level_distribution()

        if chart_type in {"all", "tasks"}:
            # 任务状态分布
            charts["task_status"] = get_task_status_distribution()

        if chart_type in {"all", "syncs"}:
            # 同步趋势图
            charts["sync_trend"] = get_sync_trend_data()

        return charts
    except Exception as e:
        log_error(f"获取图表数据失败: {e}", module="dashboard")
        return {}


@dashboard_cache(timeout=300)
def get_log_trend_data() -> list[dict[str, int | str]]:
    """获取日志趋势数据。

    Returns:
        list[dict[str, int | str]]: 最近 7 天的日志数，包含日期与数量。

    """

    return fetch_log_trend_data()


@dashboard_cache(timeout=300)
def get_log_level_distribution() -> list[dict[str, int | str]]:
    """获取日志级别分布。

    Returns:
        list[dict[str, int | str]]: 各日志级别对应的数量。

    """

    return fetch_log_level_distribution()


@dashboard_cache(timeout=60)
def get_task_status_distribution() -> list[dict[str, int | str]]:
    """获取任务状态分布（使用 APScheduler）。

    Returns:
        list[dict[str, int | str]]: 任务状态与数量列表。

    """
    try:
        from app.scheduler import get_scheduler

        scheduler = get_scheduler()
        if scheduler is None:
            return []

        jobs = scheduler.get_jobs()

        # 统计任务状态
        status_count = {}
        for job in jobs:
            status = "active" if job.next_run_time else "inactive"
            status_count[status] = status_count.get(status, 0) + 1

        return [{"status": status, "count": count} for status, count in status_count.items()]
    except Exception as e:
        log_error(f"获取任务状态分布失败: {e}", module="dashboard")
        return []


@dashboard_cache(timeout=300)
def get_sync_trend_data() -> list[dict[str, int | str]]:
    """获取同步趋势数据。

    Returns:
        list[dict[str, int | str]]: 最近 7 天同步任务数量。

    """
    try:
        db.session.rollback()
        from app.models.sync_session import SyncSession

        # 最近7天的同步数据（东八区）
        end_date = time_utils.now_china().date()
        start_date = end_date - timedelta(days=6)

        date_buckets: list[tuple[datetime, any, any]] = []
        for offset in range(7):
            day = start_date + timedelta(days=offset)
            start_dt = datetime(
                year=day.year,
                month=day.month,
                day=day.day,
                tzinfo=CHINA_TZ,
            )
            end_dt = start_dt + timedelta(days=1)
            start_utc = time_utils.to_utc(start_dt)
            end_utc = time_utils.to_utc(end_dt)
            if start_utc is None or end_utc is None:
                continue
            date_buckets.append((start_dt, start_utc, end_utc))

        if not date_buckets:
            return []

        select_columns = []
        labels: list[tuple[datetime, str]] = []
        for start_dt, start_utc, end_utc in date_buckets:
            label = f"sync_{time_utils.format_china_time(start_dt, '%Y%m%d')}"
            select_columns.append(
                func.sum(
                    case(
                        (
                            and_(
                                SyncSession.created_at >= start_utc,
                                SyncSession.created_at < end_utc,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label(label)
            )
            labels.append((start_dt, label))

        if not select_columns:
            return []

        result = (
            db.session.query(*select_columns)
            .filter(
                SyncSession.created_at >= date_buckets[0][1],
                SyncSession.created_at < date_buckets[-1][2],
            )
            .one_or_none()
        )
        result_mapping = result._mapping if result is not None else {}

        trend_data: list[dict[str, int | str]] = []
        for start_dt, label in labels:
            trend_data.append(
                {
                    "date": time_utils.format_china_time(start_dt, "%Y-%m-%d"),
                    "count": int(result_mapping.get(label) or 0),
                }
            )

        return trend_data
    except Exception as e:
        log_error(f"获取同步趋势数据失败: {e}", module="dashboard")
        return []


@dashboard_cache(timeout=30)
def get_system_status() -> dict:
    """获取系统状态。

    检查系统资源使用情况（CPU、内存、磁盘）和服务健康状态（数据库、Redis）。
    结果缓存 30 秒。

    Returns:
        包含系统状态信息的字典。

    """
    try:
        # 系统资源状态
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
    except Exception as e:
        log_error(f"获取系统状态失败: {e}", module="dashboard")
        return {
            "system": {
                "cpu": 0,
                "memory": {"used": 0, "total": 0, "percent": 0},
                "disk": {"used": 0, "total": 0, "percent": 0},
            },
            "services": {
                "database": "unknown",
                "redis": "unknown",
                "application": "unknown",
            },
            "uptime": "unknown",
        }
