"""数据库大小采集定时任务."""

from __future__ import annotations

from typing import Any

from app import create_app, db
from app.services.capacity.capacity_collection_task_runner import (
    CAPACITY_TASK_EXCEPTIONS,
    CapacityCollectionTaskRunner,
    CapacitySyncTotals,
)
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


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
            task="collect_database_sizes",
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


def collect_database_sizes() -> dict[str, Any]:
    """容量同步定时任务(采集所有活跃实例的数据库容量)."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        runner = CapacityCollectionTaskRunner()
        active_instances = []
        session_obj = None
        records = []

        try:
            sync_logger.info("开始容量同步任务", module="capacity_sync")

            active_instances = runner.list_active_instances()
            if not active_instances:
                sync_logger.warning("没有找到活跃的数据库实例", module="capacity_sync")
                return runner.no_active_instances_result()

            sync_logger.info(
                "找到活跃实例,开始容量同步",
                module="capacity_sync",
                instance_count=len(active_instances),
            )

            session_obj, records = runner.create_capacity_session(active_instances)
            db.session.commit()
            totals = CapacitySyncTotals()
            results: list[dict[str, object]] = []

            for instance, record in zip(active_instances, records, strict=False):
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

            session_obj.successful_instances = totals.total_synced
            session_obj.failed_instances = totals.total_failed
            session_obj.status = "completed" if totals.total_failed == 0 else "failed"
            session_obj.completed_at = time_utils.now()
            db.session.commit()

            message = f"容量同步完成: 成功 {totals.total_synced} 个,失败 {totals.total_failed} 个"
            result = {
                "success": totals.total_failed == 0,
                "message": message,
                "instances_processed": totals.total_synced,
                "total_size_mb": totals.total_collected_size_mb,
                "session_id": session_obj.session_id,
                "details": results,
            }

            sync_logger.info(
                "容量同步任务完成",
                module="capacity_sync",
                session_id=session_obj.session_id,
                total_instances=len(active_instances),
                successful_instances=totals.total_synced,
                failed_instances=totals.total_failed,
                total_size_mb=totals.total_collected_size_mb,
            )

        except CAPACITY_TASK_EXCEPTIONS as exc:
            sync_logger.exception(
                "容量同步任务执行失败",
                module="capacity_sync",
                error=str(exc),
            )

            if session_obj is not None:
                session_obj.status = "failed"
                session_obj.completed_at = time_utils.now()
                session_obj.failed_instances = len(active_instances)
                db.session.commit()

            return {
                "success": False,
                "message": f"容量同步任务执行失败: {exc!s}",
                "error": str(exc),
            }
        except Exception as exc:  # pragma: no cover - 兜底避免会话卡死
            sync_logger.exception(
                "容量同步任务执行失败(未分类)",
                module="capacity_sync",
                error=str(exc),
            )

            if session_obj is not None:
                session_obj.status = "failed"
                session_obj.completed_at = time_utils.now()
                session_obj.failed_instances = len(active_instances)
                db.session.commit()

            return {
                "success": False,
                "message": f"容量同步任务执行失败: {exc!s}",
                "error": str(exc),
            }
        else:
            return result
