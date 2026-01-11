"""统计聚合手动任务入口."""

from __future__ import annotations

from datetime import date
from typing import Any

from app import create_app, db
from app.services.aggregation.aggregation_service import AggregationService
from app.services.aggregation.aggregation_tasks_read_service import AggregationTasksReadService
from app.services.aggregation.capacity_aggregation_task_runner import (
    AGGREGATION_TASK_EXCEPTIONS,
    PREVIOUS_PERIOD_OVERRIDES,
    STATUS_FAILED,
    STATUS_SKIPPED,
)
from app.utils.structlog_config import log_error, log_info

TASK_MODULE = "aggregation_tasks"


def calculate_instance_aggregations(instance_id: int) -> dict[str, Any]:
    """计算指定实例的统计聚合."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            log_info(
                "开始计算实例统计聚合",
                module=TASK_MODULE,
                instance_id=instance_id,
            )

            instance = AggregationTasksReadService.get_instance_by_id(instance_id)
            if not instance:
                return {
                    "status": STATUS_FAILED,
                    "message": f"实例 {instance_id} 不存在",
                }

            if not instance.is_active:
                return {
                    "status": STATUS_SKIPPED,
                    "message": f"实例 {instance_id} 未激活",
                }

            result = AggregationService().calculate_instance_aggregations(
                instance_id,
                use_current_periods=PREVIOUS_PERIOD_OVERRIDES,
            )
            db.session.commit()

            log_info(
                "实例统计聚合完成",
                module=TASK_MODULE,
                instance_id=instance_id,
                status=result.get("status"),
                result_message=result.get("message"),
            )

        except AGGREGATION_TASK_EXCEPTIONS as exc:
            log_error(
                "计算实例统计聚合失败",
                module=TASK_MODULE,
                exception=exc,
                instance_id=instance_id,
            )
            return {
                "status": STATUS_FAILED,
                "message": f"计算实例 {instance_id} 统计聚合失败: {exc}",
                "error": str(exc),
            }
        else:
            return result


def calculate_period_aggregations(period_type: str, start_date: date, end_date: date) -> dict[str, Any]:
    """计算指定周期的统计聚合."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            log_info(
                "开始计算指定周期统计聚合",
                module=TASK_MODULE,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )

            result = AggregationService().calculate_period_aggregations(period_type, start_date, end_date)
            db.session.commit()

            log_info(
                "指定周期统计聚合完成",
                module=TASK_MODULE,
                period_type=period_type,
                status=result.get("status"),
                result_message=result.get("message"),
            )

        except AGGREGATION_TASK_EXCEPTIONS as exc:
            log_error(
                "计算指定周期统计聚合失败",
                module=TASK_MODULE,
                exception=exc,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            return {
                "status": STATUS_FAILED,
                "message": f"计算 {period_type} 周期统计聚合失败: {exc}",
                "error": str(exc),
            }
        else:
            return result

