"""容量统计当前周期聚合任务.

用于页面按钮触发的异步聚合任务:
- 统一创建/复用 TaskRun
- 按实例维度写入 TaskRunItem 进度
"""

from __future__ import annotations

import time
from typing import Any

from app import create_app, db
from app.core.exceptions import ValidationError
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.repositories.instances_repository import InstancesRepository
from app.schemas.task_run_summary import TaskRunSummaryFactory
from app.services.aggregation.aggregation_service import AggregationService
from app.services.aggregation.results import AggregationStatus
from app.services.task_runs.task_run_summary_builders import build_capacity_aggregate_current_summary
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils

_ALLOWED_SCOPES = {"instance", "database", "all"}


class TaskRunCancelledError(Exception):
    """用于从聚合 callbacks 中中断 runner 的取消异常."""


def _validate_scope(scope: str) -> str:
    cleaned = (scope or "all").strip().lower()
    if cleaned not in _ALLOWED_SCOPES:
        raise ValidationError("scope 参数仅支持 instance、database 或 all")
    return cleaned


def capacity_aggregate_current(
    *,
    scope: str = "all",
    created_by: int | None = None,
    run_id: str | None = None,
    **_: object,
) -> dict[str, Any]:
    """执行当前周期聚合(当前强制 daily),并写入 TaskRun."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        task_runs_service = TaskRunsWriteService()

        resolved_scope = _validate_scope(scope)
        resolved_run_id = run_id
        if resolved_run_id:
            existing_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            if existing_run is None:
                raise ValidationError("run_id 不存在,无法写入任务运行记录", extra={"run_id": resolved_run_id})
        else:
            resolved_run_id = task_runs_service.start_run(
                task_key="capacity_aggregate_current",
                task_name="容量统计(当前周期)",
                task_category="aggregation",
                trigger_source="manual",
                created_by=created_by,
                summary_json=TaskRunSummaryFactory.base(
                    task_key="capacity_aggregate_current",
                    inputs={"scope": resolved_scope},
                ),
                result_url=("/capacity/databases" if resolved_scope == "database" else "/capacity/instances"),
            )
            db.session.commit()

        def _is_cancelled() -> bool:
            current = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            return bool(current and current.status == "cancelled")

        if _is_cancelled():
            sync_logger.info(
                "任务已取消,跳过执行",
                module="capacity_aggregations",
                task="capacity_aggregate_current",
                run_id=resolved_run_id,
                scope=resolved_scope,
            )
            return {"success": True, "message": "任务已取消", "run_id": resolved_run_id}

        started_at = time.perf_counter()
        service = AggregationService()
        period_type = "daily"
        period_start_date, period_end_date = service.period_calculator.get_current_period(period_type)

        active_instances = InstancesRepository.list_active_instances()
        task_runs_service.init_items(
            resolved_run_id,
            items=[
                TaskRunItemInit(
                    item_type="instance",
                    item_key=str(instance.id),
                    item_name=instance.name,
                    instance_id=instance.id,
                )
                for instance in active_instances
            ],
        )
        db.session.commit()

        current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
        if current_run is not None and current_run.status != "cancelled":
            current_run.summary_json = build_capacity_aggregate_current_summary(
                task_key="capacity_aggregate_current",
                inputs={"scope": resolved_scope},
                scope=resolved_scope,
                requested_period_type=period_type,
                effective_period_type=period_type,
                period_start=period_start_date,
                period_end=period_end_date,
                status=None,
                message=None,
            )
        db.session.commit()

        def _ensure_not_cancelled() -> None:
            if _is_cancelled():
                raise TaskRunCancelledError()

        def _build_callback_group(kind: str) -> dict[str, Any]:
            def _on_start(instance) -> None:
                _ensure_not_cancelled()
                task_runs_service.start_item(resolved_run_id, item_type="instance", item_key=str(instance.id))
                db.session.commit()

            def _on_complete(instance, payload: dict[str, Any]) -> None:
                _ensure_not_cancelled()
                status = str(payload.get("status") or AggregationStatus.FAILED.value).lower()
                processed_value = payload.get("processed_records")
                processed = int(processed_value) if processed_value is not None else 0
                details = dict(payload)
                metrics = {
                    "processed_records": processed,
                    "runner": kind,
                    "scope": resolved_scope,
                    "period_type": period_type,
                }
                if status == AggregationStatus.FAILED.value:
                    task_runs_service.fail_item(
                        resolved_run_id,
                        item_type="instance",
                        item_key=str(instance.id),
                        error_message=str(payload.get("message") or "聚合失败"),
                        details_json=details,
                    )
                else:
                    task_runs_service.complete_item(
                        resolved_run_id,
                        item_type="instance",
                        item_key=str(instance.id),
                        metrics_json=metrics,
                        details_json=details,
                    )
                db.session.commit()

            def _on_error(instance, payload: dict[str, Any]) -> None:
                _ensure_not_cancelled()
                details = dict(payload)
                task_runs_service.fail_item(
                    resolved_run_id,
                    item_type="instance",
                    item_key=str(instance.id),
                    error_message=str(payload.get("message") or payload.get("error") or "聚合失败"),
                    details_json=details,
                )
                db.session.commit()

            return {"on_start": _on_start, "on_complete": _on_complete, "on_error": _on_error}

        progress_callbacks: dict[str, dict[str, Any]] = {}
        if resolved_scope in {"database", "all"}:
            progress_callbacks["database"] = _build_callback_group("database")
        if resolved_scope in {"instance", "all"}:
            progress_callbacks["instance"] = _build_callback_group("instance")

        try:
            result = service.aggregate_current_period(
                period_type=period_type,
                scope=resolved_scope,
                progress_callbacks=progress_callbacks,
            )
        except TaskRunCancelledError:
            sync_logger.info(
                "任务已取消,提前终止聚合",
                module="capacity_aggregations",
                task="capacity_aggregate_current",
                run_id=resolved_run_id,
                scope=resolved_scope,
            )
            task_runs_service.finalize_run(resolved_run_id)
            db.session.commit()
            return {"success": True, "message": "任务已取消", "run_id": resolved_run_id}
        except Exception as exc:
            db.session.rollback()
            sync_logger.exception(
                "当前周期聚合失败",
                module="capacity_aggregations",
                task="capacity_aggregate_current",
                run_id=resolved_run_id,
                scope=resolved_scope,
                error=str(exc),
            )

            now = time_utils.now()
            current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            if current_run is not None and current_run.status != "cancelled":
                current_run.status = "failed"
                current_run.error_message = str(exc)
                current_run.completed_at = now
                for item in TaskRunItem.query.filter_by(run_id=resolved_run_id).all():
                    if item.status in {"pending", "running"}:
                        item.status = "failed"
                        item.error_message = str(exc)
                        item.completed_at = now
                task_runs_service.finalize_run(resolved_run_id)
                db.session.commit()

            return {
                "success": False,
                "message": f"当前周期聚合失败: {exc!s}",
                "error": str(exc),
                "run_id": resolved_run_id,
            }

        current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
        if current_run is not None and current_run.status != "cancelled":
            status_value = result.get("status")
            message_value = result.get("message")
            current_run.summary_json = build_capacity_aggregate_current_summary(
                task_key="capacity_aggregate_current",
                inputs={"scope": resolved_scope},
                scope=resolved_scope,
                requested_period_type=period_type,
                effective_period_type=period_type,
                period_start=period_start_date,
                period_end=period_end_date,
                status=str(status_value) if status_value is not None else None,
                message=str(message_value) if message_value is not None else None,
            )

        task_runs_service.finalize_run(resolved_run_id)
        db.session.commit()

        sync_logger.info(
            "当前周期聚合完成",
            module="capacity_aggregations",
            task="capacity_aggregate_current",
            run_id=resolved_run_id,
            scope=resolved_scope,
            duration_seconds=round(time.perf_counter() - started_at, 2),
        )
        return {"success": True, "message": "当前周期聚合完成", "run_id": resolved_run_id}
