"""Capacity 域: 聚合统计路由."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from flask import Blueprint, Response, request
from flask_login import current_user, login_required

from app import db
from app.constants import SyncStatus
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.errors import SystemError as AppSystemError, ValidationError as AppValidationError
from app.models.instance import Instance
from app.services.aggregation.aggregation_service import AggregationService
from app.services.aggregation.results import AggregationStatus
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils


if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from app.models.sync_instance_record import SyncInstanceRecord
    from app.models.sync_session import SyncSession

# 创建蓝图
capacity_aggregations_bp = Blueprint("capacity_aggregations", __name__)

# 聚合模块专注于核心聚合功能, 不包含页面路由


# 核心聚合功能 API
def _normalize_task_result(result: dict | None, *, context: str) -> dict:
    """标准化异步任务返回结果.

    Args:
        result: 任务执行返回的字典.
        context: 当前任务场景描述, 便于日志输出.

    Returns:
        处理后的结果字典, 将 status 字段统一为小写.

    Raises:
        SystemError: 当 result 为空或包含失败状态时抛出.

    """
    if not result:
        msg = f"{context}任务返回为空"
        raise AppSystemError(msg)
    status = (result.get("status") or "completed").lower()
    if status == SyncStatus.FAILED:
        raise AppSystemError(result.get("message") or f"{context}执行失败")
    normalized = dict(result)
    normalized["status"] = status
    return normalized


@dataclass(slots=True)
class AggregationRequest:
    """手动聚合请求参数."""

    requested_period_type: str
    scope: str


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


def _parse_manual_aggregation_request(payload: dict[str, Any]) -> AggregationRequest:
    """解析手动聚合请求体."""
    requested_period_type = (payload.get("period_type") or "daily").lower()
    scope = (payload.get("scope") or "all").lower()
    return AggregationRequest(requested_period_type=requested_period_type, scope=scope)


def _validate_scope(scope: str) -> str:
    """校验聚合范围参数."""
    valid_scopes = {"instance", "database", "all"}
    if scope not in valid_scopes:
        msg = "scope 参数仅支持 instance、database 或 all"
        raise AppValidationError(msg)
    return scope


def _create_run_state(instances: list[Instance], meta: AggregationMeta) -> AggregationRunState:
    """创建聚合执行上下文并初始化同步会话."""
    session = sync_session_service.create_session(
        sync_type=SyncOperationType.MANUAL_TASK.value,
        sync_category=SyncCategory.AGGREGATION.value,
        created_by=meta.created_by,
    )
    session.total_instances = len(instances)
    db.session.add(session)
    db.session.commit()

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


def _build_progress_callbacks(state: AggregationRunState) -> dict[str, dict[str, Callable[..., None]]]:
    """构建进度回调,供聚合服务绑定."""
    callbacks: dict[str, dict[str, Callable[..., None]]] = {}
    callback_group = _create_callback_group(state)
    if state.scope in {"database", "all"}:
        callbacks["database"] = callback_group
    if state.scope in {"instance", "all"}:
        callbacks["instance"] = callback_group
    return callbacks


def _create_callback_group(state: AggregationRunState) -> dict[str, Callable[..., None]]:
    """生成绑定到数据库/实例聚合的回调集合."""

    def _ensure_started(record: SyncInstanceRecord) -> None:
        if record.id in state.started_ids:
            return
        if sync_session_service.start_instance_sync(record.id):
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
        _handle_instance_result(record, payload, state)

    def _on_error(instance: Instance, payload: dict[str, Any]) -> None:
        record = state.records_by_instance.get(instance.id)
        if not record:
            return
        _ensure_started(record)
        _handle_instance_error(record, payload, state)

    return {
        "on_start": _on_start,
        "on_complete": _on_complete,
        "on_error": _on_error,
    }


def _handle_instance_result(record: SyncInstanceRecord, payload: dict[str, Any], state: AggregationRunState) -> None:
    """根据回调结果更新同步记录状态."""
    status = (payload.get("status") or AggregationStatus.FAILED.value).lower()
    processed = int(payload.get("processed_records") or 0)
    details = {
        "period_type": state.period_type,
        "period_start": state.start_date.isoformat(),
        "period_end": state.end_date.isoformat(),
        "aggregation_result": payload,
        "aggregation_count": processed,
        "scope": state.scope,
    }
    if status == AggregationStatus.FAILED.value:
        error_message = payload.get("error") or payload.get("message") or "聚合失败"
        sync_session_service.fail_instance_sync(record.id, error_message, sync_details=details)
    else:
        sync_session_service.complete_instance_sync(record.id, items_synced=processed, sync_details=details)
    state.finalized_ids.add(record.id)


def _handle_instance_error(record: SyncInstanceRecord, payload: dict[str, Any], state: AggregationRunState) -> None:
    """处理聚合过程中抛出的错误."""
    error_message = payload.get("error") or payload.get("message") or "聚合失败"
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


def _handle_aggregation_failure(state: AggregationRunState, exc: Exception) -> None:
    """聚合失败时更新所有记录状态并标记会话失败."""
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
        current_session.status = "failed"
        current_session.completed_at = time_utils.now()
        db.session.add(current_session)
        db.session.commit()


def _complete_empty_session(state: AggregationRunState) -> None:
    """当无实例时直接完成会话."""
    if state.session.total_instances != 0:
        return
    refreshed_session = sync_session_service.get_session_by_id(state.session.session_id)
    if refreshed_session:
        refreshed_session.status = "completed"
        refreshed_session.completed_at = time_utils.now()
        db.session.add(refreshed_session)
        db.session.commit()


def _finalize_missing_records(state: AggregationRunState) -> None:
    """补齐未完成的同步记录,避免遗漏."""
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


def _attach_session_snapshot(raw_result: dict[str, Any], session_id: int) -> dict[str, Any]:
    """为聚合结果补充最新会话信息."""
    refreshed_session = sync_session_service.get_session_by_id(str(session_id))
    if refreshed_session:
        raw_result.setdefault("session", refreshed_session.to_dict())
    else:
        raw_result.setdefault("session", {"session_id": session_id})
    return raw_result


@capacity_aggregations_bp.route("/api/aggregations/current", methods=["POST"])
@login_required
@view_required
@require_csrf
def aggregate_current() -> tuple[Response, int]:
    """手动触发当前周期数据聚合.

    Returns:
        Response: 包含聚合结果的 JSON 响应.

    """
    payload = request.get_json(silent=True) or {}
    aggregation_request = _parse_manual_aggregation_request(payload)
    context_snapshot = {
        "requested_period_type": aggregation_request.requested_period_type,
        "scope": aggregation_request.scope,
        "payload_keys": list(payload.keys()),
    }

    def _execute() -> tuple[Response, int]:
        period_type = "daily"
        scope = _validate_scope(aggregation_request.scope)
        if aggregation_request.requested_period_type != period_type:
            log_info(
                "手动聚合请求的周期已被强制替换为日周期",
                module="aggregations",
                requested_period=aggregation_request.requested_period_type,
                enforced_period=period_type,
            )

        service = AggregationService()
        start_date_date, end_date_date = service.period_calculator.get_current_period(period_type)
        start_date = time_utils.to_china(start_date_date.isoformat()) or time_utils.now()
        end_date = time_utils.to_china(end_date_date.isoformat()) or time_utils.now()
        active_instances = Instance.query.filter_by(is_active=True).all()
        created_by = current_user.id if current_user.is_authenticated else None
        meta = AggregationMeta(
            period_type=period_type,
            scope=scope,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by,
        )
        state = _create_run_state(active_instances, meta)
        progress_callbacks = _build_progress_callbacks(state)

        try:
            raw_result = service.aggregate_current_period(
                period_type=period_type,
                scope=scope,
                progress_callbacks=progress_callbacks,
            )
        except Exception as exc:  # pragma: no cover - 聚合异常路径
            _handle_aggregation_failure(state, exc)
            raise

        _complete_empty_session(state)
        _finalize_missing_records(state)
        raw_result = _attach_session_snapshot(raw_result, int(state.session.session_id))

        result = _normalize_task_result(raw_result, context=f"{period_type} 当前周期聚合")
        result["scope"] = scope
        result["requested_period_type"] = aggregation_request.requested_period_type
        result["effective_period_type"] = period_type

        session_info = result.get("session") or {}
        log_info(
            "当前周期数据聚合任务已触发",
            module="aggregations",
            period_type=period_type,
            session_id=session_info.get("session_id"),
        )

        return jsonify_unified_success(
            data={"result": result},
            message="已仅聚合今日数据",
        )

    return safe_route_call(
        _execute,
        module="capacity_aggregations",
        action="aggregate_current",
        public_error="触发当前周期数据聚合失败",
        expected_exceptions=(AppValidationError,),
        context=context_snapshot,
    )
