"""数据库大小采集定时任务."""

from __future__ import annotations

from typing import Any

from app import create_app, db
from app.core.exceptions import ValidationError
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.services.capacity.capacity_collection_task_runner import (
    CAPACITY_TASK_EXCEPTIONS,
    CapacityCollectionTaskRunner,
    CapacitySyncTotals,
)
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


def _finalize_task_failed(
    *,
    sync_logger: Any,
    session_obj: Any | None,
    active_instances: list[Any],
    run_id: str | None,
    task_runs_service: TaskRunsWriteService | None,
    message: str,
    exc: Exception,
) -> dict[str, Any]:
    sync_logger.exception(
        message,
        module="capacity_sync",
        error=str(exc),
    )

    if session_obj is not None:
        session_obj.status = "failed"
        session_obj.completed_at = time_utils.now()
        session_obj.failed_instances = len(active_instances)
        db.session.commit()

    if run_id and task_runs_service:
        now = time_utils.now()
        current_run = TaskRun.query.filter_by(run_id=run_id).first()
        if current_run is not None and current_run.status != "cancelled":
            current_run.status = "failed"
            current_run.error_message = str(exc)
            current_run.completed_at = now
            for item in TaskRunItem.query.filter_by(run_id=run_id).all():
                if item.status in {"pending", "running"}:
                    item.status = "failed"
                    item.error_message = str(exc)
                    item.completed_at = now
            task_runs_service.finalize_run(run_id)
            db.session.commit()

    return {
        "success": False,
        "message": f"数据库同步任务执行失败: {exc!s}",
        "error": str(exc),
    }


def _process_instance_with_fallback(
    *,
    runner: CapacityCollectionTaskRunner,
    session_obj: Any,
    record: Any,
    instance: Any,
    sync_logger: Any,
) -> tuple[dict[str, object], CapacitySyncTotals]:
    runner.start_instance_sync(record.id)
    db.session.commit()
    try:
        payload, delta = runner.process_capacity_instance(
            session=session_obj,
            record=record,
            instance=instance,
            sync_logger=sync_logger,
        )
    except Exception as exc:  # pragma: no cover - 兜底避免会话卡死
        db.session.rollback()
        error_msg = f"实例同步异常: {exc!s}"
        sync_logger.exception(
            "实例同步异常(未分类)",
            module="capacity_sync",
            task="sync_databases",
            action="process_capacity_instance",
            session_id=session_obj.session_id,
            instance_id=instance.id,
            instance_name=instance.name,
            fallback=True,
            fallback_reason="capacity_instance_sync_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        runner.fail_instance_sync(record.id, error_msg)
        db.session.commit()
        payload = {
            "instance_id": instance.id,
            "instance_name": instance.name,
            "success": False,
            "error": str(exc),
        }
        delta = CapacitySyncTotals(total_failed=1)
    else:
        db.session.commit()

    return payload, delta


def sync_databases(
    *,
    manual_run: bool = False,
    created_by: int | None = None,
    run_id: str | None = None,
    **_: object,
) -> dict[str, Any]:
    """数据库同步任务(采集所有活跃实例的数据库容量)."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        runner = CapacityCollectionTaskRunner()
        task_runs_service = TaskRunsWriteService()

        trigger_source = "manual" if manual_run else "scheduled"
        resolved_run_id = run_id
        if resolved_run_id:
            existing_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            if existing_run is None:
                raise ValidationError("run_id 不存在,无法写入任务运行记录", extra={"run_id": resolved_run_id})
        else:
            resolved_run_id = task_runs_service.start_run(
                task_key="sync_databases",
                task_name="数据库同步",
                task_category="capacity",
                trigger_source=trigger_source,
                created_by=created_by,
                summary_json=None,
                result_url="/databases/ledgers",
            )
            db.session.commit()

        def _is_cancelled() -> bool:
            current = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            return bool(current and current.status == "cancelled")

        active_instances: list[Any] = []
        session_obj: Any | None = None
        records: list[Any] = []

        try:
            if _is_cancelled():
                sync_logger.info(
                    "任务已取消,跳过执行",
                    module="capacity_sync",
                    task="sync_databases",
                    run_id=resolved_run_id,
                )
                return {"success": True, "message": "任务已取消"}

            sync_logger.info(
                "开始数据库同步任务",
                module="capacity_sync",
                task="sync_databases",
                run_id=resolved_run_id,
            )

            active_instances = runner.list_active_instances()
            if not active_instances:
                sync_logger.warning(
                    "没有找到活跃的数据库实例",
                    module="capacity_sync",
                    task="sync_databases",
                    run_id=resolved_run_id,
                )
                task_runs_service.finalize_run(resolved_run_id)
                db.session.commit()
                return {"run_id": resolved_run_id, **runner.no_active_instances_result()}

            sync_logger.info(
                "找到活跃实例,开始数据库同步",
                module="capacity_sync",
                task="sync_databases",
                instance_count=len(active_instances),
                manual_run=manual_run,
                created_by=created_by,
                run_id=resolved_run_id,
            )

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

            session_obj, records = runner.create_capacity_session(active_instances)
            db.session.commit()

            totals = CapacitySyncTotals()
            results: list[dict[str, object]] = []

            for instance, record in zip(active_instances, records, strict=False):
                if _is_cancelled():
                    sync_logger.info(
                        "任务已取消,提前退出实例循环",
                        module="capacity_sync",
                        task="sync_databases",
                        run_id=resolved_run_id,
                    )
                    break

                task_runs_service.start_item(
                    resolved_run_id,
                    item_type="instance",
                    item_key=str(instance.id),
                )
                db.session.commit()

                payload, delta = _process_instance_with_fallback(
                    runner=runner,
                    session_obj=session_obj,
                    record=record,
                    instance=instance,
                    sync_logger=sync_logger,
                )

                totals.total_synced += delta.total_synced
                totals.total_failed += delta.total_failed
                totals.total_collected_size_mb += delta.total_collected_size_mb
                results.append(payload)

                payload_success = bool(payload.get("success"))
                metrics = {
                    "database_count": payload.get("database_count", 0),
                    "size_mb": payload.get("size_mb", 0),
                    "saved_count": payload.get("saved_count", 0),
                }
                if payload_success:
                    task_runs_service.complete_item(
                        resolved_run_id,
                        item_type="instance",
                        item_key=str(instance.id),
                        metrics_json=metrics,
                        details_json=dict(payload),
                    )
                else:
                    error_message = str(payload.get("error") or payload.get("message") or "实例容量同步失败")
                    task_runs_service.fail_item(
                        resolved_run_id,
                        item_type="instance",
                        item_key=str(instance.id),
                        error_message=error_message,
                        details_json=dict(payload),
                    )
                db.session.commit()

            if session_obj is not None:
                session_obj.successful_instances = totals.total_synced
                session_obj.failed_instances = totals.total_failed
                session_obj.status = "completed" if totals.total_failed == 0 else "failed"
                session_obj.completed_at = time_utils.now()
                db.session.commit()

            current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            if current_run is not None and current_run.status != "cancelled":
                current_run.summary_json = {
                    "instances_total": len(active_instances),
                    "instances_processed": totals.total_synced + totals.total_failed,
                    "instances_successful": totals.total_synced,
                    "instances_failed": totals.total_failed,
                    "total_size_mb": totals.total_collected_size_mb,
                }

            task_runs_service.finalize_run(resolved_run_id)
            db.session.commit()

            message = f"数据库同步完成: 成功 {totals.total_synced} 个,失败 {totals.total_failed} 个"
            result = {
                "success": totals.total_failed == 0,
                "message": message,
                "instances_processed": totals.total_synced,
                "total_size_mb": totals.total_collected_size_mb,
                "run_id": resolved_run_id,
                "session_id": getattr(session_obj, "session_id", None),
                "details": results,
            }

            sync_logger.info(
                "数据库同步任务完成",
                module="capacity_sync",
                task="sync_databases",
                run_id=resolved_run_id,
                session_id=getattr(session_obj, "session_id", None),
                total_instances=len(active_instances),
                successful_instances=totals.total_synced,
                failed_instances=totals.total_failed,
                total_size_mb=totals.total_collected_size_mb,
            )

            return result

        except CAPACITY_TASK_EXCEPTIONS as exc:
            db.session.rollback()
            return _finalize_task_failed(
                sync_logger=sync_logger,
                session_obj=session_obj,
                active_instances=active_instances,
                run_id=resolved_run_id,
                task_runs_service=task_runs_service,
                message="数据库同步任务执行失败",
                exc=exc,
            )
        except Exception as exc:  # pragma: no cover - 兜底避免会话卡死
            db.session.rollback()
            return _finalize_task_failed(
                sync_logger=sync_logger,
                session_obj=session_obj,
                active_instances=active_instances,
                run_id=resolved_run_id,
                task_runs_service=task_runs_service,
                message="数据库同步任务执行失败(未分类)",
                exc=exc,
            )
