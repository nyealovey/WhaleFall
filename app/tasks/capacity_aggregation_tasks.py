"""数据库大小统计聚合定时任务."""

from __future__ import annotations

import time
from contextlib import suppress
from typing import Any

from app import create_app, db
from app.core.exceptions import ValidationError
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.services.aggregation.aggregation_service import AggregationService
from app.services.aggregation.capacity_aggregation_task_runner import (
    AGGREGATION_TASK_EXCEPTIONS,
    STATUS_COMPLETED,
    STATUS_FAILED,
    CapacityAggregationTaskRunner,
)
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


def _prepare_aggregation_run(
    *,
    app: Any,
    runner: CapacityAggregationTaskRunner,
    sync_logger: Any,
    manual_run: bool,
    periods: list[str] | None,
) -> tuple[AggregationService, list[Any], list[str]] | dict[str, Any]:
    if not bool(app.config.get("AGGREGATION_ENABLED", True)):
        sync_logger.info("数据库大小统计聚合功能已禁用", module="aggregation_sync")
        return runner.build_skip_response("统计聚合功能已禁用")

    active_instances = runner.list_active_instances()
    if not active_instances:
        sync_logger.warning("没有找到活跃的数据库实例", module="aggregation_sync")
        return runner.build_skip_response("没有活跃的数据库实例需要聚合")

    service = AggregationService()
    selected_periods = runner.select_periods(periods, sync_logger, service.period_types)
    if not selected_periods:
        sync_logger.warning(
            "未选择任何有效的聚合周期,任务直接完成",
            module="aggregation_sync",
            requested_periods=periods,
        )
        return runner.build_skip_response("未选择有效的聚合周期,未执行统计任务")

    if not manual_run and periods is None:
        selected_periods = runner.filter_periods_already_aggregated(
            service=service,
            selected_periods=selected_periods,
            logger=sync_logger,
        )
        if not selected_periods:
            sync_logger.info("所有周期均已聚合,任务直接跳过", module="aggregation_sync")
            return runner.build_skip_response("所有周期均已聚合,无需重复执行")

    return service, active_instances, selected_periods


def _aggregate_instances(
    *,
    runner: CapacityAggregationTaskRunner,
    service: AggregationService,
    active_instances: list[Any],
    selected_periods: list[str],
    records_by_instance: dict[int, Any],
    task_run_id: str,
    task_runs_service: TaskRunsWriteService,
    is_cancelled: Any,
    sync_logger: Any,
    started_record_ids: set[int],
    finalized_record_ids: set[int],
) -> tuple[dict[int, dict[str, Any]], int, int, int]:
    instance_details: dict[int, dict[str, Any]] = {}
    successful_instances = 0
    failed_instances = 0
    total_instance_aggregations = 0

    for instance in active_instances:
        if bool(is_cancelled and is_cancelled()):
            sync_logger.info(
                "任务已取消,提前退出实例循环",
                module="aggregation_sync",
                run_id=task_run_id,
            )
            break

        task_runs_service.start_item(task_run_id, item_type="instance", item_key=str(instance.id))
        db.session.commit()

        record = records_by_instance.get(instance.id)

        if record:
            runner.start_instance_sync(record.id)
            started_record_ids.add(record.id)
            db.session.commit()

        details, success, aggregated_count = runner.calculate_instance_aggregation(
            service=service,
            instance=instance,
            selected_periods=selected_periods,
            logger=sync_logger,
        )

        if record:
            errors = details.get("errors")
            error_message = "; ".join(errors) if (not success and isinstance(errors, list)) else None
            runner.complete_instance_sync(
                record.id,
                success=success,
                aggregated_count=aggregated_count,
                details=details,
                error_message=error_message,
            )
            finalized_record_ids.add(record.id)
            db.session.commit()

        if success:
            task_runs_service.complete_item(
                task_run_id,
                item_type="instance",
                item_key=str(instance.id),
                metrics_json={"aggregated_count": aggregated_count},
                details_json=details,
            )
        else:
            error_list = details.get("errors")
            error_message = (
                "; ".join(str(err) for err in error_list)
                if isinstance(error_list, list) and error_list
                else "实例聚合失败"
            )
            task_runs_service.fail_item(
                task_run_id,
                item_type="instance",
                item_key=str(instance.id),
                error_message=error_message,
                details_json=details,
            )
        db.session.commit()

        instance_details[instance.id] = {
            "aggregations_created": aggregated_count,
            "errors": details.get("errors", []),
            "period_results": details.get("periods"),
        }
        total_instance_aggregations += aggregated_count
        if success:
            successful_instances += 1
        else:
            failed_instances += 1

    return instance_details, successful_instances, failed_instances, total_instance_aggregations


def _handle_aggregation_task_exception(
    *,
    exc: BaseException,
    runner: CapacityAggregationTaskRunner,
    sync_logger: Any,
    task_started_at: float,
    session: Any | None,
    started_record_ids: set[int],
    finalized_record_ids: set[int],
    selected_periods: list[str] | None,
) -> dict[str, Any]:
    sync_logger.exception(
        "统计聚合任务异常",
        module="aggregation_sync",
        error=str(exc),
        duration_seconds=round(time.perf_counter() - task_started_at, 2),
    )
    if session is not None:
        with suppress(*AGGREGATION_TASK_EXCEPTIONS):  # pragma: no cover
            db.session.rollback()

        leftover_ids = started_record_ids - finalized_record_ids
        for record_id in leftover_ids:
            with suppress(*AGGREGATION_TASK_EXCEPTIONS):
                runner.fail_instance_sync(record_id, f"聚合任务异常: {exc}")

        session.status = "failed"
        session.completed_at = time_utils.now()
        db.session.commit()

    return {
        "status": STATUS_FAILED,
        "message": f"统计聚合任务执行失败: {exc}",
        "error": str(exc),
        "periods_executed": selected_periods,
    }


def calculate_database_aggregations(
    *,
    manual_run: bool = False,
    periods: list[str] | None = None,
    created_by: int | None = None,
    run_id: str | None = None,
    **_: object,
) -> dict[str, Any]:
    """计算数据库大小统计聚合(按日/周/月/季依次执行)."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        runner = CapacityAggregationTaskRunner()
        task_runs_service = TaskRunsWriteService()
        task_started_at = time.perf_counter()
        session = None
        started_record_ids: set[int] = set()
        finalized_record_ids: set[int] = set()
        selected_periods: list[str] | None = None

        trigger_source = "manual" if manual_run else "scheduled"
        resolved_run_id = run_id
        if resolved_run_id:
            existing_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            if existing_run is None:
                raise ValidationError("run_id 不存在,无法写入任务运行记录", extra={"run_id": resolved_run_id})
        else:
            resolved_run_id = task_runs_service.start_run(
                task_key="calculate_database_aggregations",
                task_name="统计数据库聚合",
                task_category="aggregation",
                trigger_source=trigger_source,
                created_by=created_by,
                summary_json={"requested_periods": periods},
                result_url="/capacity/instances",
            )
            db.session.commit()

        def _is_cancelled() -> bool:
            current = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            return bool(current and current.status == "cancelled")

        try:
            if _is_cancelled():
                sync_logger.info(
                    "任务已取消,跳过执行",
                    module="aggregation_sync",
                    task="calculate_database_aggregations",
                    run_id=resolved_run_id,
                )
                return {"status": "cancelled", "message": "任务已取消", "run_id": resolved_run_id}

            sync_logger.info(
                "开始执行数据库大小统计聚合任务",
                module="aggregation_sync",
                task="calculate_database_aggregations",
                run_id=resolved_run_id,
            )

            prepared = _prepare_aggregation_run(
                app=app,
                runner=runner,
                sync_logger=sync_logger,
                manual_run=manual_run,
                periods=periods,
            )
            if isinstance(prepared, dict):
                current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
                if current_run is not None and current_run.status != "cancelled":
                    current_run.summary_json = {
                        "skipped": True,
                        "skip_reason": prepared.get("message"),
                        "requested_periods": periods,
                    }
                task_runs_service.finalize_run(resolved_run_id)
                db.session.commit()
                return {"run_id": resolved_run_id, **prepared}
            service, active_instances, selected_periods = prepared

            sync_logger.info(
                "找到活跃实例,准备创建同步会话",
                module="aggregation_sync",
                instance_count=len(active_instances),
                manual_run=manual_run,
                periods=selected_periods,
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

            session, records_by_instance = runner.init_aggregation_session(
                manual_run=manual_run,
                created_by=created_by,
                active_instances=active_instances,
                selected_periods=selected_periods,
                logger=sync_logger,
            )
            db.session.commit()

            instance_details, successful_instances, failed_instances, total_instance_aggregations = (
                _aggregate_instances(
                    runner=runner,
                    service=service,
                    active_instances=active_instances,
                    selected_periods=selected_periods,
                    records_by_instance=records_by_instance,
                    task_run_id=resolved_run_id,
                    task_runs_service=task_runs_service,
                    is_cancelled=_is_cancelled,
                    sync_logger=sync_logger,
                    started_record_ids=started_record_ids,
                    finalized_record_ids=finalized_record_ids,
                )
            )

            if _is_cancelled():
                sync_logger.info(
                    "任务已取消,跳过剩余聚合汇总",
                    module="aggregation_sync",
                    task="calculate_database_aggregations",
                    run_id=resolved_run_id,
                )
                task_runs_service.finalize_run(resolved_run_id)
                db.session.commit()
                return {"status": "cancelled", "message": "任务已取消", "run_id": resolved_run_id}

            period_summaries, total_database_aggregations = runner.summarize_database_periods(
                service=service,
                selected_periods=selected_periods,
                logger=sync_logger,
            )

            session.successful_instances = successful_instances
            session.failed_instances = failed_instances
            session.status = "completed" if failed_instances == 0 else "failed"
            session.completed_at = time_utils.now()
            db.session.commit()

            current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            if current_run is not None and current_run.status != "cancelled":
                current_run.summary_json = {
                    "periods_executed": selected_periods,
                    "instances_total": len(active_instances),
                    "instances_successful": successful_instances,
                    "instances_failed": failed_instances,
                    "records": {
                        "instance": total_instance_aggregations,
                        "database": total_database_aggregations,
                        "total": total_instance_aggregations + total_database_aggregations,
                    },
                }

            task_runs_service.finalize_run(resolved_run_id)
            db.session.commit()

            overall_status = STATUS_COMPLETED if failed_instances == 0 else STATUS_FAILED
            message = (
                f"统计聚合完成: 成功 {successful_instances} 个实例,失败 {failed_instances} 个实例"
                if failed_instances
                else f"统计聚合完成,共处理 {successful_instances} 个实例"
            )
            duration_seconds = round(time.perf_counter() - task_started_at, 2)

            sync_logger.info(
                "统计聚合任务完成",
                module="aggregation_sync",
                session_id=session.session_id,
                run_id=resolved_run_id,
                successful_instances=successful_instances,
                failed_instances=failed_instances,
                total_instance_aggregations=total_instance_aggregations,
                total_database_aggregations=total_database_aggregations,
                manual_run=manual_run,
                duration_seconds=duration_seconds,
            )

            return {
                "status": overall_status,
                "message": message,
                "run_id": resolved_run_id,
                "session_id": session.session_id,
                "periods_executed": selected_periods,
                "details": {
                    "periods": period_summaries,
                    "instances": instance_details,
                },
                "metrics": {
                    "instances": {
                        "total": len(active_instances),
                        "successful": successful_instances,
                        "failed": failed_instances,
                    },
                    "records": {
                        "instance": total_instance_aggregations,
                        "database": total_database_aggregations,
                        "total": total_instance_aggregations + total_database_aggregations,
                    },
                },
            }
        except AGGREGATION_TASK_EXCEPTIONS as exc:
            db.session.rollback()

            current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            if current_run is not None and current_run.status != "cancelled":
                now = time_utils.now()
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

            result = _handle_aggregation_task_exception(
                exc=exc,
                runner=runner,
                sync_logger=sync_logger,
                task_started_at=task_started_at,
                session=session,
                started_record_ids=started_record_ids,
                finalized_record_ids=finalized_record_ids,
                selected_periods=selected_periods,
            )
            result["run_id"] = resolved_run_id
            return result
