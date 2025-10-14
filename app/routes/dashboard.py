
"""
鲸落 - 系统仪表板路由
"""

from datetime import datetime, timedelta, date

import psutil
from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import and_, distinct, func, or_, text, case

from app import db
from app.models.instance import Instance
from app.models.current_account_sync_data import CurrentAccountSyncData

# 移除SyncData导入，使用新的同步会话模型
from app.models.user import User
from app.utils.cache_manager import dashboard_cache
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import CHINA_TZ, time_utils
from app.scheduler import get_scheduler

# 创建蓝图
dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index() -> str:
    """系统仪表板首页"""
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
        return jsonify(
            {
                "overview": overview_data,
                "charts": chart_data,
                "status": system_status,
            }
        )

    return render_template(
        "dashboard/overview.html",
        overview=overview_data,
        charts=chart_data,
        status=system_status,
    )


@dashboard_bp.route("/api/overview")
@login_required
def api_overview() -> "Response":
    """获取系统概览API"""
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

    return jsonify(overview)


@dashboard_bp.route("/api/charts")
@login_required
def api_charts() -> "Response":
    """获取图表数据API"""
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

    return jsonify(charts)


@dashboard_bp.route("/api/activities")
@login_required
def api_activities() -> "Response":
    """获取最近活动API - 已废弃，返回空数据"""
    return jsonify([])


@dashboard_bp.route("/api/status")
@login_required
def api_status() -> "Response":
    """获取系统状态API"""
    status = get_system_status()

    # 移除用户查看操作的日志记录

    return jsonify(status)


@dashboard_cache(timeout=300)
def get_system_overview() -> dict:
    """获取系统概览数据（缓存版本）"""
    try:
        db.session.rollback()
        # 基础统计
        total_users = User.query.count()
        total_instances = Instance.query.count()
        from app.models.account_classification import AccountClassification, AccountClassificationAssignment
        from app.models.current_account_sync_data import CurrentAccountSyncData
        from app.models.unified_log import LogLevel, UnifiedLog

        # 获取容量统计
        from app.models.database_size_stat import DatabaseSizeStat
        from app.models.instance_size_stat import InstanceSizeStat
        
        # 获取最近的容量数据（最近7天）
        recent_date = datetime.now().date() - timedelta(days=7)
        
        # 计算总容量（使用实例大小统计）
        recent_instance_stats = InstanceSizeStat.query.filter(
            InstanceSizeStat.collected_date >= recent_date
        ).all()
        
        # 按实例分组，获取每个实例的最新大小
        instance_sizes = {}
        for stat in recent_instance_stats:
            if stat.instance_id not in instance_sizes or stat.collected_date > instance_sizes[stat.instance_id]['date']:
                instance_sizes[stat.instance_id] = {
                    'size_mb': stat.total_size_mb or 0,
                    'date': stat.collected_date
                }
        
        total_capacity_gb = sum(inst['size_mb'] for inst in instance_sizes.values()) / 1024
        
        # 计算数据库总数
        recent_db_stats = DatabaseSizeStat.query.filter(
            DatabaseSizeStat.collected_date >= recent_date
        ).all()
        
        # 按数据库分组，计算唯一数据库数量
        unique_databases = set()
        for stat in recent_db_stats:
            unique_databases.add(f"{stat.instance_id}_{stat.database_name}")
        
        total_databases = len(unique_databases)

        total_accounts = CurrentAccountSyncData.query.filter_by(is_deleted=False).count()
        log_info(
            "dashboard_base_counts",
            module="dashboard",
            total_users=total_users,
            total_instances=total_instances,
            total_accounts=total_accounts,
            total_capacity_gb=round(total_capacity_gb, 1),
            total_databases=total_databases,
        )

        # 分类统计（聚合查询，避免N+1）
        classification_rows = (
            db.session.query(
                AccountClassification.name,
                AccountClassification.color,
                AccountClassification.priority,
                func.count(distinct(AccountClassificationAssignment.account_id)).label("count")
            )
            .outerjoin(
                AccountClassificationAssignment,
                and_(
                    AccountClassificationAssignment.classification_id == AccountClassification.id,
                    AccountClassificationAssignment.is_active.is_(True)
                )
            )
            .outerjoin(
                CurrentAccountSyncData,
                and_(
                    CurrentAccountSyncData.id == AccountClassificationAssignment.account_id,
                    CurrentAccountSyncData.is_deleted.is_(False)
                )
            )
            .outerjoin(
                Instance,
                and_(
                    Instance.id == CurrentAccountSyncData.instance_id,
                    Instance.is_active.is_(True),
                    Instance.deleted_at.is_(None)
                )
            )
            .filter(AccountClassification.is_active.is_(True))
            .group_by(AccountClassification.id)
            .order_by(AccountClassification.priority.desc())
            .all()
        )
        classification_stats = [
            (name, color, priority, count or 0)
            for name, color, priority, count in classification_rows
        ]
        total_classified_accounts = sum(count for _, _, _, count in classification_stats)

        auto_classified_accounts = (
            db.session.query(func.count(distinct(AccountClassificationAssignment.account_id)))
            .join(
                CurrentAccountSyncData,
                and_(
                    CurrentAccountSyncData.id == AccountClassificationAssignment.account_id,
                    CurrentAccountSyncData.is_deleted.is_(False)
                )
            )
            .join(
                Instance,
                and_(
                    Instance.id == CurrentAccountSyncData.instance_id,
                    Instance.is_active.is_(True),
                    Instance.deleted_at.is_(None)
                )
            )
            .filter(
                AccountClassificationAssignment.is_active.is_(True),
                AccountClassificationAssignment.assignment_type == "auto"
            )
            .scalar()
            or 0
        )

        log_info(
            "dashboard_classification_counts",
            module="dashboard",
            classifications=len(classification_stats),
            total_classified_accounts=total_classified_accounts,
            auto_classified_accounts=auto_classified_accounts,
        )

        # 活跃实例数
        active_instances = Instance.query.filter_by(is_active=True).count()

        active_accounts = (
            db.session.query(func.count(CurrentAccountSyncData.id))
            .join(Instance, Instance.id == CurrentAccountSyncData.instance_id)
            .filter(
                CurrentAccountSyncData.is_deleted.is_(False),
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                or_(
                    CurrentAccountSyncData.is_active.is_(None),
                    CurrentAccountSyncData.is_active.is_(True)
                )
            )
            .scalar()
            or 0
        )

        log_info(
            "dashboard_active_counts",
            module="dashboard",
            total_accounts=total_accounts,
            active_accounts=active_accounts,
            active_instances=active_instances,
        )

        # 获取最新的容量使用率（可选，用于显示使用情况）
        capacity_usage_percent = 0
        if total_capacity_gb > 0:
            # 这里可以根据实际需求计算使用率，暂时设为0
            capacity_usage_percent = 0

        # 最近同步数据（东八区） - 使用新的同步会话模型

        china_today = time_utils.now_china().date()

        return {
            "users": {"total": total_users, "active": total_users},  # 简化处理
            "instances": {"total": total_instances, "active": active_instances},
            "accounts": {"total": total_accounts, "active": active_accounts},
            "classified_accounts": {
                "total": total_classified_accounts,
                "auto": auto_classified_accounts,
                "classifications": [
                    {"name": name, "color": color or "#6c757d", "priority": priority, "count": count}
                    for name, color, priority, count in classification_stats
                ],
            },
            "capacity": {"total_gb": round(total_capacity_gb, 1), "usage_percent": capacity_usage_percent},
            "databases": {"total": total_databases, "active": total_databases},
        }
    except Exception as e:
        db.session.rollback()
        log_error(f"获取系统概览失败: {e}", module="dashboard")
        return {
            "users": {"total": 0, "active": 0},
            "instances": {"total": 0, "active": 0},
            "accounts": {"total": 0, "active": 0},
            "classified_accounts": {"total": 0, "auto": 0, "classifications": []},
            "capacity": {"total_gb": 0, "usage_percent": 0},
            "databases": {"total": 0, "active": 0},
        }


@dashboard_cache(timeout=180)
def get_chart_data(chart_type: str = "all") -> dict:
    """获取图表数据"""
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
    """获取日志趋势数据（分别显示错误和告警日志）"""
    try:
        db.session.rollback()
        from app.models.unified_log import LogLevel, UnifiedLog

        # 最近7天的日志数据（东八区）
        china_today = time_utils.now_china().date()
        start_date = china_today - timedelta(days=6)

        date_buckets: list[tuple[date, datetime, datetime]] = []
        for offset in range(7):
            day = start_date + timedelta(days=offset)
            start_dt = datetime.combine(day, datetime.min.time()).replace(tzinfo=CHINA_TZ)
            end_dt = start_dt + timedelta(days=1)
            start_utc = time_utils.to_utc(start_dt)
            end_utc = time_utils.to_utc(end_dt)
            if start_utc is None or end_utc is None:
                continue
            date_buckets.append((day, start_utc, end_utc))

        if not date_buckets:
            return []

        select_columns = []
        labels: list[tuple[date, str, str]] = []
        for day, start_utc, end_utc in date_buckets:
            suffix = day.strftime("%Y%m%d")
            error_label = f"error_{suffix}"
            warning_label = f"warning_{suffix}"
            select_columns.append(
                func.sum(
                    case(
                        (
                            and_(
                                UnifiedLog.timestamp >= start_utc,
                                UnifiedLog.timestamp < end_utc,
                                UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL]),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label(error_label)
            )
            select_columns.append(
                func.sum(
                    case(
                        (
                            and_(
                                UnifiedLog.timestamp >= start_utc,
                                UnifiedLog.timestamp < end_utc,
                                UnifiedLog.level == LogLevel.WARNING,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label(warning_label)
            )
            labels.append((day, error_label, warning_label))

        if not select_columns:
            return []

        relevant_levels = [LogLevel.ERROR, LogLevel.WARNING, LogLevel.CRITICAL]
        query = (
            db.session.query(*select_columns)
            .filter(
                UnifiedLog.timestamp >= date_buckets[0][1],
                UnifiedLog.timestamp < date_buckets[-1][2],
                UnifiedLog.level.in_(relevant_levels),
            )
        )
        result = query.one_or_none()
        result_mapping = result._mapping if result is not None else {}

        trend_data: list[dict[str, int | str]] = []
        for day, error_label, warning_label in labels:
            trend_data.append(
                {
                    "date": day.strftime("%Y-%m-%d"),
                    "error_count": int(result_mapping.get(error_label) or 0),
                    "warning_count": int(result_mapping.get(warning_label) or 0),
                }
            )

        return trend_data
    except Exception as e:
        log_error(f"获取日志趋势数据失败: {e}", module="dashboard")
        return []


@dashboard_cache(timeout=300)
def get_log_level_distribution() -> list[dict[str, int | str]]:
    """获取日志级别分布（只显示错误和告警日志）"""
    try:
        db.session.rollback()
        from app.models.unified_log import LogLevel, UnifiedLog

        level_stats = (
            db.session.query(UnifiedLog.level, db.func.count(UnifiedLog.id).label("count"))
            .filter(UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.WARNING, LogLevel.CRITICAL]))
            .group_by(UnifiedLog.level)
            .all()
        )

        return [{"level": stat.level.value, "count": stat.count} for stat in level_stats]
    except Exception as e:
        log_error(f"获取日志级别分布失败: {e}", module="dashboard")
        return []


@dashboard_cache(timeout=60)
def get_task_status_distribution() -> list[dict[str, int | str]]:
    """获取任务状态分布（使用APScheduler）"""
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
    """获取同步趋势数据"""
    try:
        db.session.rollback()
        from app.models.sync_session import SyncSession

        # 最近7天的同步数据（东八区）
        end_date = time_utils.now_china().date()
        start_date = end_date - timedelta(days=6)

        date_buckets: list[tuple[date, datetime, datetime]] = []
        for offset in range(7):
            day = start_date + timedelta(days=offset)
            start_dt = datetime.combine(day, datetime.min.time()).replace(tzinfo=CHINA_TZ)
            end_dt = start_dt + timedelta(days=1)
            start_utc = time_utils.to_utc(start_dt)
            end_utc = time_utils.to_utc(end_dt)
            if start_utc is None or end_utc is None:
                continue
            date_buckets.append((day, start_utc, end_utc))

        if not date_buckets:
            return []

        select_columns = []
        labels: list[tuple[date, str]] = []
        for day, start_utc, end_utc in date_buckets:
            label = f"sync_{day.strftime('%Y%m%d')}"
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
            labels.append((day, label))

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
        for day, label in labels:
            trend_data.append(
                {
                    "date": day.strftime("%Y-%m-%d"),
                    "count": int(result_mapping.get(label) or 0),
                }
            )

        return trend_data
    except Exception as e:
        log_error(f"获取同步趋势数据失败: {e}", module="dashboard")
        return []


@dashboard_cache(timeout=30)
def get_system_status() -> dict:
    """获取系统状态"""
    try:
        # 系统资源状态
        cpu_percent = psutil.cpu_percent(interval=None)
        if cpu_percent == 0.0:
            cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # 数据库状态
        db_status = "healthy"
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db_status = "error"

        # Redis状态（通过缓存检查）
        redis_status = "healthy"
        try:
            from flask import current_app
            from app.services.cache_manager import cache_manager

            if cache_manager and cache_manager.health_check():
                redis_status = "healthy"
            else:
                redis_status = "error"
        except Exception as e:
            log_warning(f"Redis连接检查失败: {e}", module="dashboard")
            redis_status = "error"

        # 应用状态
        app_status = "running"

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
                "application": app_status,
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


def get_system_uptime() -> "str | None":
    """获取应用运行时间"""
    try:
        from app import app_start_time
        from app.utils.time_utils import now_china

        # 计算应用运行时间
        current_time = now_china()
        uptime = current_time - app_start_time

        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        return f"{days}天 {hours}小时 {minutes}分钟"
    except Exception:
        return "未知"
