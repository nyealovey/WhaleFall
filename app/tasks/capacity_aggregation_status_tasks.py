"""统计聚合状态/配置入口."""

from __future__ import annotations

from typing import Any

from app import create_app
from app.services.aggregation.aggregation_tasks_read_service import AggregationTasksReadService
from app.services.aggregation.capacity_aggregation_task_runner import (
    AGGREGATION_TASK_EXCEPTIONS,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils

TASK_MODULE = "aggregation_tasks"
MAX_HOUR_IN_DAY = 23


def get_aggregation_status() -> dict[str, Any]:
    """获取聚合状态信息."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            today = time_utils.now().date()
            status = AggregationTasksReadService().get_status()
            return {
                "status": STATUS_COMPLETED,
                "latest_aggregation": status.latest_aggregation.isoformat() if status.latest_aggregation else None,
                "aggregation_counts": status.aggregation_counts,
                "total_instances": status.total_instances,
                "check_date": today.isoformat(),
            }
        except AGGREGATION_TASK_EXCEPTIONS as exc:
            log_error(
                "获取聚合状态失败",
                module=TASK_MODULE,
                exception=exc,
            )
            return {
                "status": STATUS_FAILED,
                "message": f"获取聚合状态失败: {exc}",
                "error": str(exc),
            }


def validate_aggregation_config() -> dict[str, Any]:
    """验证聚合配置."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            config_issues: list[str] = []

            aggregation_enabled = bool(app.config.get("AGGREGATION_ENABLED", True))
            if not aggregation_enabled:
                config_issues.append("数据库大小统计聚合已禁用")

            aggregation_hour = int(app.config.get("AGGREGATION_HOUR", 4))
            if aggregation_hour < 0 or aggregation_hour > MAX_HOUR_IN_DAY:
                config_issues.append("聚合时间配置无效,应为0-23之间的整数")

            status = STATUS_COMPLETED if not config_issues else STATUS_FAILED
            message = "聚合配置验证通过" if not config_issues else "聚合配置存在需要关注的问题"
        except AGGREGATION_TASK_EXCEPTIONS as exc:
            log_error(
                "验证聚合配置失败",
                module=TASK_MODULE,
                exception=exc,
            )
            return {
                "status": STATUS_FAILED,
                "message": f"验证聚合配置失败: {exc}",
                "error": str(exc),
            }
        else:
            return {
                "status": status,
                "message": message,
                "issues": config_issues,
                "config": {
                    "enabled": aggregation_enabled,
                    "hour": aggregation_hour,
                },
            }
