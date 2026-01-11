"""数据库大小统计聚合任务 runner.

职责:
- 承载 `capacity_aggregation_tasks` 的重逻辑(周期选择、实例聚合结果整理、会话/记录状态更新).
- 不创建 Flask app context(由 tasks 层保证).
- 不做 `db.session.commit/rollback`(由写边界入口负责).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

import structlog
from sqlalchemy.exc import SQLAlchemyError

from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.errors import AppError
from app.models.instance import Instance
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.services.aggregation.aggregation_service import AggregationService
from app.services.aggregation.aggregation_tasks_read_service import AggregationTasksReadService
from app.services.sync_session_service import SyncItemStats, sync_session_service

STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"

PREVIOUS_PERIOD_OVERRIDES = {"daily": False}

AGGREGATION_TASK_EXCEPTIONS: tuple[type[Exception], ...] = (
    AppError,
    SQLAlchemyError,
    RuntimeError,
    LookupError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
)


class CapacityAggregationTaskRunner:
    """数据库大小统计聚合任务 runner."""

    @staticmethod
    def list_active_instances() -> list[Instance]:
        return AggregationTasksReadService().list_active_instances()

    @staticmethod
    def select_periods(
        requested: Sequence[str] | None,
        logger: structlog.BoundLogger,
        allowed_periods: Sequence[str],
    ) -> list[str]:
        allowed = list(allowed_periods)
        if not allowed:
            return []

        if requested is None:
            return allowed.copy()

        normalized: list[str] = []
        unknown: list[str] = []
        seen: set[str] = set()
        for item in requested:
            key = (item or "").strip().lower()
            if not key:
                continue
            if key in allowed_periods:
                if key not in seen:
                    normalized.append(key)
                    seen.add(key)
            else:
                unknown.append(item)

        if unknown:
            logger.warning(
                "忽略未知聚合周期",
                module="aggregation_sync",
                unknown_periods=unknown,
            )

        ordered = [period for period in allowed if period in normalized]
        return ordered if ordered else allowed.copy()

    @staticmethod
    def has_aggregation_for_period(period_type: str, period_start: date) -> bool:
        return AggregationTasksReadService.has_aggregation_for_period(period_type=period_type, period_start=period_start)

    def filter_periods_already_aggregated(
        self,
        *,
        service: AggregationService,
        selected_periods: Sequence[str],
        logger: structlog.BoundLogger,
    ) -> list[str]:
        skipped: dict[str, str] = {}
        remaining: list[str] = []

        for period_type in selected_periods:
            period_start, _ = service.period_calculator.get_last_period(period_type)
            if self.has_aggregation_for_period(period_type, period_start):
                skipped[period_type] = period_start.isoformat()
                continue
            remaining.append(period_type)

        if skipped:
            logger.info(
                "检测到历史周期已聚合,本次跳过执行",
                module="aggregation_sync",
                skipped_periods=skipped,
            )

        return remaining

    @staticmethod
    def build_skip_response(message: str) -> dict[str, Any]:
        return {
            "status": STATUS_SKIPPED,
            "message": message,
            "metrics": {
                "aggregations_created": 0,
                "processed_instances": 0,
            },
            "periods_executed": [],
        }

    @staticmethod
    def start_instance_sync(record_id: int) -> None:
        sync_session_service.start_instance_sync(record_id)

    @staticmethod
    def complete_instance_sync(
        record_id: int,
        *,
        success: bool,
        aggregated_count: int,
        details: dict[str, Any],
        error_message: str | None,
    ) -> None:
        if success:
            stats = SyncItemStats(items_synced=int(aggregated_count or 0))
            sync_session_service.complete_instance_sync(
                record_id,
                stats=stats,
                sync_details=details,
            )
            return
        sync_session_service.fail_instance_sync(
            record_id,
            error_message=error_message or "聚合失败",
            sync_details=details,
        )

    @staticmethod
    def fail_instance_sync(record_id: int, error_message: str) -> None:
        sync_session_service.fail_instance_sync(record_id, error_message=error_message)

    @staticmethod
    def init_aggregation_session(
        *,
        manual_run: bool,
        created_by: int | None,
        active_instances: Sequence[Instance],
        selected_periods: Sequence[str],
        logger: structlog.BoundLogger,
    ) -> tuple[SyncSession, dict[int, SyncInstanceRecord]]:
        if manual_run:
            sync_type = SyncOperationType.MANUAL_TASK.value
        else:
            created_by = None
            sync_type = SyncOperationType.SCHEDULED_TASK.value

        session = sync_session_service.create_session(
            sync_type=sync_type,
            sync_category=SyncCategory.AGGREGATION.value,
            created_by=created_by,
        )

        logger.info(
            "聚合同步会话已创建",
            module="aggregation_sync",
            session_id=session.session_id,
            instance_count=len(active_instances),
            manual_run=manual_run,
            created_by=created_by,
            periods=selected_periods,
        )

        instance_ids = [inst.id for inst in active_instances]
        records = sync_session_service.add_instance_records(
            session.session_id,
            instance_ids,
            sync_category=SyncCategory.AGGREGATION.value,
        )
        session.total_instances = len(active_instances)
        records_by_instance = {record.instance_id: record for record in records}
        return session, records_by_instance

    @staticmethod
    def _extract_processed_records(result: dict[str, Any] | None) -> int:
        if not result:
            return 0
        return int(result.get("processed_records") or 0)

    @staticmethod
    def _extract_error_message(result: dict[str, Any] | None) -> str:
        if not result:
            return "无返回结果"
        errors = result.get("errors")
        if isinstance(errors, list) and errors:
            return "; ".join(str(err) for err in errors)
        return str(result.get("message") or "未知错误")

    def _normalize_period_results(
        self,
        instance: Instance,
        selected_periods: Sequence[str],
        period_results: dict[str, Any] | None,
        logger: structlog.BoundLogger,
    ) -> tuple[dict[str, dict[str, Any]], list[str], int]:
        filtered_period_results: dict[str, dict[str, Any]] = {}
        instance_errors: list[str] = []
        aggregated_count = 0

        for period_name in selected_periods:
            result = period_results.get(period_name) if period_results else None
            if result is None:
                result = {
                    "status": STATUS_FAILED,
                    "processed_records": 0,
                    "message": "聚合服务未返回结果",
                    "errors": ["聚合服务未返回结果"],
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                    "period_type": period_name,
                }
            filtered_period_results[period_name] = result

            status = str(result.get("status") or STATUS_FAILED).lower()
            if status == STATUS_COMPLETED:
                logger.info(
                    "实例聚合完成",
                    module="aggregation_sync",
                    period=period_name,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    processed_records=self._extract_processed_records(result),
                    message=result.get("message"),
                )
            elif status == STATUS_SKIPPED:
                logger.info(
                    "实例聚合跳过",
                    module="aggregation_sync",
                    period=period_name,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    message=result.get("message"),
                )
            else:
                error_msg = self._extract_error_message(result)
                instance_errors.append(f"{period_name}: {error_msg}")
                logger.error(
                    "实例聚合失败",
                    module="aggregation_sync",
                    period=period_name,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    error=error_msg,
                    errors=result.get("errors"),
                )

            aggregated_count += self._extract_processed_records(result)

        return filtered_period_results, instance_errors, aggregated_count

    def calculate_instance_aggregation(
        self,
        *,
        service: AggregationService,
        instance: Instance,
        selected_periods: Sequence[str],
        logger: structlog.BoundLogger,
    ) -> tuple[dict[str, Any], bool, int]:
        try:
            summary = service.calculate_instance_aggregations(
                instance.id,
                periods=list(selected_periods),
                use_current_periods=PREVIOUS_PERIOD_OVERRIDES,
            )
            period_results = summary.get("periods", {}) or {}
        except AGGREGATION_TASK_EXCEPTIONS as period_exc:  # pragma: no cover
            logger.exception(
                "实例聚合执行异常",
                module="aggregation_sync",
                instance_id=instance.id,
                instance_name=instance.name,
                error=str(period_exc),
            )
            period_results = {
                period_name: {
                    "status": STATUS_FAILED,
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                    "period_type": period_name,
                    "message": f"{period_name} 聚合执行异常: {period_exc}",
                    "errors": [str(period_exc)],
                    "error": str(period_exc),
                }
                for period_name in selected_periods
            }

        filtered_period_results, instance_errors, aggregated_count = self._normalize_period_results(
            instance,
            selected_periods,
            period_results,
            logger,
        )

        details: dict[str, Any] = {
            "aggregations_created": aggregated_count,
            "aggregation_count": aggregated_count,
            "periods": filtered_period_results,
            "errors": instance_errors,
            "instance_id": instance.id,
            "instance_name": instance.name,
        }

        success = not instance_errors
        return details, success, aggregated_count

    def summarize_database_periods(
        self,
        *,
        service: AggregationService,
        selected_periods: Sequence[str],
        logger: structlog.BoundLogger,
    ) -> tuple[list[dict[str, Any]], int]:
        period_summaries: list[dict[str, Any]] = []
        total_database_aggregations = 0

        for period_name in selected_periods:
            db_result = service.calculate_database_size_aggregations(
                period_name,
                use_current_periods=PREVIOUS_PERIOD_OVERRIDES,
            )
            status = str(db_result.get("status") or STATUS_FAILED).lower()
            if status == STATUS_COMPLETED:
                logger.info(
                    "数据库级聚合完成",
                    module="aggregation_sync",
                    period=period_name,
                    processed_records=db_result.get("processed_records", 0),
                    processed_instances=db_result.get("processed_instances"),
                )
            elif status == STATUS_SKIPPED:
                logger.info(
                    "数据库级聚合跳过",
                    module="aggregation_sync",
                    period=period_name,
                    message=db_result.get("message"),
                )
            else:
                logger.error(
                    "数据库级聚合失败",
                    module="aggregation_sync",
                    period=period_name,
                    error=db_result.get("error"),
                    errors=db_result.get("errors"),
                )
            db_result.setdefault("period_type", period_name)
            period_summaries.append(db_result)
            total_database_aggregations += self._extract_processed_records(db_result)

        return period_summaries, total_database_aggregations

