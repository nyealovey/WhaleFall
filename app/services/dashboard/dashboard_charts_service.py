"""Dashboard 图表数据 Service.

负责聚合日志/任务/同步等图表数据,供 DashboardOverviewPage 使用.
"""

from __future__ import annotations

from typing import Any

from app.repositories.dashboard_charts_repository import DashboardChartsRepository
from app.scheduler import get_scheduler
from app.services.statistics.log_statistics_service import fetch_log_level_distribution, fetch_log_trend_data
from app.utils.cache_utils import dashboard_cache


@dashboard_cache(timeout=300)
def get_log_trend_data() -> list[dict[str, int | str]]:
    return fetch_log_trend_data()


@dashboard_cache(timeout=300)
def get_log_level_distribution() -> list[dict[str, int | str]]:
    return fetch_log_level_distribution()


@dashboard_cache(timeout=60)
def get_task_status_distribution() -> list[dict[str, int | str]]:
    scheduler = get_scheduler()
    if scheduler is None:
        return []

    jobs = scheduler.get_jobs()
    status_count: dict[str, int] = {}
    for job in jobs:
        status = "active" if job.next_run_time else "inactive"
        status_count[status] = status_count.get(status, 0) + 1

    return [{"status": status, "count": count} for status, count in status_count.items()]


@dashboard_cache(timeout=300)
def get_sync_trend_data(*, days: int = 7) -> list[dict[str, int | str]]:
    return DashboardChartsRepository().fetch_sync_trend(days=days)


@dashboard_cache(timeout=180)
def get_chart_data(chart_type: str = "all") -> dict[str, Any]:
    chart_type_normalized = (chart_type or "all").lower()
    charts: dict[str, Any] = {}

    if chart_type_normalized in {"all", "logs"}:
        charts["log_trend"] = get_log_trend_data()
        charts["log_levels"] = get_log_level_distribution()

    if chart_type_normalized in {"all", "tasks"}:
        charts["task_status"] = get_task_status_distribution()

    if chart_type_normalized in {"all", "syncs"}:
        charts["sync_trend"] = get_sync_trend_data(days=7)

    return charts

