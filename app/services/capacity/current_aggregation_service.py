"""容量统计: 手动触发当前周期聚合 Service.

职责:
- 路由层只做参数解析与安全封装
- 本模块负责聚合执行编排、会话/记录写入与结果整理
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from flask_login import current_user

from app import db
from app.core.constants import SyncStatus
from app.core.constants.sync_constants import SyncCategory, SyncOperationType
from app.core.exceptions import SystemError as AppSystemError, ValidationError
from app.core.types.capacity_aggregations import CurrentAggregationRequest
from app.models.instance import Instance
from app.repositories.instances_repository import InstancesRepository
from app.services.aggregation.aggregation_service import AggregationService
from app.services.aggregation.results import AggregationStatus
from app.services.sync_session_service import SyncItemStats, sync_session_service
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from app.models.sync_instance_record import SyncInstanceRecord
    from app.models.sync_session import SyncSession


def _normalize_task_result(result: dict | None, *, context: str) -> dict:
    """标准化异步任务返回结果."""
    if not result:
        msg = f"{context}任务返回为空"
        raise AppSystemError(msg)
    status = (result.get("status") or "completed").lower()
    if status == SyncStatus.FAILED:
        raise AppSystemError(result.get("message") or f"{context}执行失败")
    normalized = dict(result)
    normalized["status"] = status
    return normalized


def _validate_scope(scope: str) -> str:
    """校验聚合范围参数."""
    valid_scopes = {"instance", "database", "all"}
    if scope not in valid_scopes:
        msg = "scope 参数仅支持 instance、database 或 all"
        raise ValidationError(msg)
    return scope


@dataclass(slots=True)
class AggregationMeta:
    """聚合上下文元信息."""

    period_type: str
    scope: str
    start_date: datetime
    end_date: datetime
    created_by: int | None


@dataclass(slots=True)
class AggregationRunState:
    """聚合执行过程的上下文状态."""

    session: SyncSession
    records_by_instance: dict[int, SyncInstanceRecord]
    period_type: str
    scope: str
    start_date: datetime
    end_date: datetime
    started_ids: set[int]
    finalized_ids: set[int]


class CurrentAggregationService:
    """手动触发当前周期聚合服务."""

    def aggregate_current(self, request: CurrentAggregationRequest) -> dict[str, Any]:
        """执行当前周期聚合."""
        period_type = "daily"
        scope = _validate_scope((request.scope or "all").lower())

        requested_period_type = (request.requested_period_type or "daily").lower()
        if requested_period_type != period_type:
            log_info(
                "手动聚合请求的周期已被强制替换为日周期",
                module="aggregations",
                requested_period=requested_period_type,
                enforced_period=period_type,
            )

        service = AggregationService()
        start_date_date, end_date_date = service.period_calculator.get_current_period(period_type)
        start_date = time_utils.to_china(start_date_date.isoformat()) or time_utils.now()
        end_date = time_utils.to_china(end_date_date.isoformat()) or time_utils.now()
        active_instances = InstancesRepository.list_active_instances()
        created_by = current_user.id if current_user.is_authenticated else None
        meta = AggregationMeta(
            period_type=period_type,
            scope=scope,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by,
        )
        state = self._create_run_state(active_instances, meta)
        progress_callbacks = self._build_progress_callbacks(state)

        try:
            raw_result = service.aggregate_current_period(
                period_type=period_type,
                scope=scope,
                progress_callbacks=progress_callbacks,
            )
        except Exception as exc:  # pragma: no cover - 聚合异常路径
            self._handle_aggregation_failure(state, exc)
            raise

        self._complete_empty_session(state)
        self._finalize_missing_records(state)
        raw_result = self._attach_session_snapshot(raw_result, state.session.session_id)

        result = _normalize_task_result(raw_result, context=f"{period_type} 当前周期聚合")
        result["scope"] = scope
        result["requested_period_type"] = requested_period_type
        result["effective_period_type"] = period_type
        return result

    def _create_run_state(self, instances: list[Instance], meta: AggregationMeta) -> AggregationRunState:
        session = sync_session_service.create_session(
            sync_type=SyncOperationType.MANUAL_TASK.value,
            sync_category=SyncCategory.AGGREGATION.value,
            created_by=meta.created_by,
        )
        with db.session.begin_nested():
            session.total_instances = len(instances)
            db.session.flush()

        records = sync_session_service.add_instance_records(
            session.session_id,
            [inst.id for inst in instances],
            sync_category=SyncCategory.AGGREGATION.value,
        )
        records_by_instance = {record.instance_id: record for record in records}
        return AggregationRunState(
            session=session,
            records_by_instance=records_by_instance,
            period_type=meta.period_type,
            scope=meta.scope,
            start_date=meta.start_date,
            end_date=meta.end_date,
            started_ids=set(),
            finalized_ids=set(),
        )

    def _build_progress_callbacks(
        self,
        state: AggregationRunState,
    ) -> dict[str, dict[str, Callable[..., None]]]:
        callbacks: dict[str, dict[str, Callable[..., None]]] = {}
        callback_group = self._create_callback_group(state)
        if state.scope in {"database", "all"}:
            callbacks["database"] = callback_group
        if state.scope in {"instance", "all"}:
            callbacks["instance"] = callback_group
        return callbacks

    def _create_callback_group(
        self,
        state: AggregationRunState,
    ) -> dict[str, Callable[..., None]]:
        def _ensure_started(record: SyncInstanceRecord) -> None:
            if record.id in state.started_ids:
                return
            sync_session_service.start_instance_sync(record.id)
            state.started_ids.add(record.id)

        def _on_start(instance: Instance) -> None:
            record = state.records_by_instance.get(instance.id)
            if record:
                _ensure_started(record)

        def _on_complete(instance: Instance, payload: dict[str, Any]) -> None:
            record = state.records_by_instance.get(instance.id)
            if not record:
                return
            _ensure_started(record)
            self._handle_instance_result(record, payload, state)

        def _on_error(instance: Instance, payload: dict[str, Any]) -> None:
            record = state.records_by_instance.get(instance.id)
            if not record:
                return
            _ensure_started(record)
            self._handle_instance_error(record, payload, state)

        return {
            "on_start": _on_start,
            "on_complete": _on_complete,
            "on_error": _on_error,
        }

    def _handle_instance_result(
        self,
        record: SyncInstanceRecord,
        payload: dict[str, Any],
        state: AggregationRunState,
    ) -> None:
        status = (payload.get("status") or AggregationStatus.FAILED.value).lower()
        processed_value = payload.get("processed_records")
        processed = int(processed_value) if processed_value is not None else 0
        details = {
            "period_type": state.period_type,
            "period_start": state.start_date.isoformat(),
            "period_end": state.end_date.isoformat(),
            "aggregation_result": payload,
            "aggregation_count": processed,
            "scope": state.scope,
        }
        if status == AggregationStatus.FAILED.value:
            error_message = payload.get("message") or "聚合失败"
            sync_session_service.fail_instance_sync(record.id, error_message, sync_details=details)
        else:
            sync_session_service.complete_instance_sync(
                record.id,
                stats=SyncItemStats(items_synced=processed),
                sync_details=details,
            )
        state.finalized_ids.add(record.id)

    def _handle_instance_error(
        self,
        record: SyncInstanceRecord,
        payload: dict[str, Any],
        state: AggregationRunState,
    ) -> None:
        error_message = payload.get("message") or "聚合失败"
        details = {
            "period_type": state.period_type,
            "period_start": state.start_date.isoformat(),
            "period_end": state.end_date.isoformat(),
            "aggregation_result": payload,
            "aggregation_count": 0,
            "scope": state.scope,
        }
        sync_session_service.fail_instance_sync(record.id, error_message, sync_details=details)
        state.finalized_ids.add(record.id)

    def _handle_aggregation_failure(self, state: AggregationRunState, exc: Exception) -> None:
        error_message = f"当前周期聚合异常: {exc}"
        for record in state.records_by_instance.values():
            if record.id in state.finalized_ids:
                continue
            sync_session_service.fail_instance_sync(
                record.id,
                error_message=error_message,
                sync_details={
                    "period_type": state.period_type,
                    "period_start": state.start_date.isoformat(),
                    "period_end": state.end_date.isoformat(),
                    "aggregation_result": {"status": AggregationStatus.FAILED.value, "error": str(exc)},
                    "scope": state.scope,
                },
            )

        current_session = sync_session_service.get_session_by_id(state.session.session_id)
        if current_session:
            with db.session.begin_nested():
                current_session.status = "failed"
                current_session.completed_at = time_utils.now()
                db.session.flush()

    def _complete_empty_session(self, state: AggregationRunState) -> None:
        if state.session.total_instances != 0:
            return
        refreshed_session = sync_session_service.get_session_by_id(state.session.session_id)
        if refreshed_session:
            with db.session.begin_nested():
                refreshed_session.status = "completed"
                refreshed_session.completed_at = time_utils.now()
                db.session.flush()

    def _finalize_missing_records(self, state: AggregationRunState) -> None:
        records = state.records_by_instance
        if not records or len(state.finalized_ids) >= len(records):
            return
        for record in records.values():
            if record.id in state.finalized_ids:
                continue
            sync_session_service.fail_instance_sync(
                record.id,
                error_message="聚合结果缺失",
                sync_details={
                    "period_type": state.period_type,
                    "period_start": state.start_date.isoformat(),
                    "period_end": state.end_date.isoformat(),
                    "aggregation_result": {"status": "unknown"},
                    "aggregation_count": 0,
                    "scope": state.scope,
                },
            )

    def _attach_session_snapshot(self, raw_result: dict[str, Any], session_id: str) -> dict[str, Any]:
        refreshed_session = sync_session_service.get_session_by_id(session_id)
        if refreshed_session:
            raw_result.setdefault("session", refreshed_session.to_dict())
        else:
            raw_result.setdefault("session", {"session_id": session_id})
        return raw_result
