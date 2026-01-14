"""Dashboard 概览/状态 Service.

职责:
- 聚合仪表盘 overview/status 所需的只读数据
- 组织 repository 与 health checks，不在 routes 中直接拼 Query
"""

from __future__ import annotations

from datetime import timedelta

import psutil
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.core.types.capacity_instances import InstanceAggregationsSummaryFilters
from app.repositories.account_statistics_repository import AccountStatisticsRepository
from app.repositories.capacity_instances_repository import CapacityInstancesRepository
from app.repositories.database_statistics_repository import DatabaseStatisticsRepository
from app.repositories.instance_statistics_repository import InstanceStatisticsRepository
from app.repositories.users_repository import UsersRepository
from app.services.health.health_checks_service import check_cache_health, check_database_health, get_system_uptime
from app.utils.cache_utils import dashboard_cache
from app.utils.structlog_config import log_info, log_warning
from app.utils.time_utils import time_utils


@dashboard_cache(timeout=300)
def get_system_overview() -> dict:
    """获取系统概览数据(缓存版本)."""
    total_users = UsersRepository.count_users()
    account_summary = AccountStatisticsRepository.fetch_summary()
    classification_overview = AccountStatisticsRepository.fetch_classification_overview()
    instance_summary = InstanceStatisticsRepository.fetch_summary()
    database_summary = DatabaseStatisticsRepository.fetch_summary()

    recent_date = time_utils.now_china().date() - timedelta(days=7)
    total_size_mb = 0
    try:
        with db.session.begin_nested():
            _, total_size_mb, _, _ = CapacityInstancesRepository().summarize_latest_stats(
                InstanceAggregationsSummaryFilters(
                    instance_id=None,
                    db_type=None,
                    period_type=None,
                    start_date=recent_date,
                    end_date=None,
                ),
            )
    except SQLAlchemyError as exc:
        log_warning("获取容量统计汇总失败,已使用兜底值", module="dashboard", exception=exc)
    total_capacity_gb = float(total_size_mb) / 1024
    capacity_summary = {
        "total_gb": round(total_capacity_gb, 1),
        "usage_percent": 0,
    }

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
    """获取系统状态(缓存版本)."""
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
