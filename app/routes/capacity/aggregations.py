"""Capacity 域：聚合统计路由"""

from typing import Any, Callable

from flask import Blueprint, Response, request
from flask_login import current_user, login_required

from app import db
from app.errors import SystemError, ValidationError as AppValidationError
from app.constants import SyncStatus
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.models.instance import Instance
from app.services.aggregation.aggregation_service import AggregationService
from app.services.aggregation.results import AggregationStatus
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils

# 创建蓝图
capacity_aggregations_bp = Blueprint('capacity_aggregations', __name__)

# 聚合模块专注于核心聚合功能，不包含页面路由

# 核心聚合功能API
def _normalize_task_result(result: dict | None, *, context: str) -> dict:
    """标准化异步任务返回结果。

    Args:
        result: 任务执行返回的字典。
        context: 当前任务场景描述，便于日志输出。

    Returns:
        处理后的结果字典，将 status 字段统一为小写。

    Raises:
        SystemError: 当 result 为空或包含失败状态时抛出。
    """
    if not result:
        raise SystemError(f"{context}任务返回为空")
    status = (result.get("status") or "completed").lower()
    if status == SyncStatus.FAILED:
        raise SystemError(result.get("message") or f"{context}执行失败")
    normalized = dict(result)
    normalized["status"] = status
    return normalized

@capacity_aggregations_bp.route('/api/aggregations/current', methods=['POST'])
@login_required
@view_required
@require_csrf
def aggregate_current() -> Response:
    """手动触发当前周期数据聚合。

    Returns:
        Response: 包含聚合结果的 JSON 响应。
    """
    session = None
    records_by_instance: dict[int, Any] = {}
    started_record_ids: set[int] = set()
    finalized_record_ids: set[int] = set()

    try:
        payload = request.get_json(silent=True) or {}
        requested_period_type = (payload.get("period_type") or "daily").lower()
        period_type = "daily"
        scope = (payload.get("scope") or "all").lower()
        valid_scopes = {"instance", "database", "all"}
        if scope not in valid_scopes:
            raise AppValidationError("scope 参数仅支持 instance、database 或 all")

        if requested_period_type != period_type:
            log_info(
                "手动聚合请求的周期已被强制替换为日周期",
                module="aggregations",
                requested_period=requested_period_type,
                enforced_period=period_type,
            )

        # 当前周期聚合（按请求周期，含今日），并接入同步会话中心
        service = AggregationService()
        start_date, end_date = service.period_calculator.get_current_period(period_type)

        active_instances = Instance.query.filter_by(is_active=True).all()
        created_by = current_user.id if current_user.is_authenticated else None

        session = sync_session_service.create_session(
            sync_type=SyncOperationType.MANUAL_TASK.value,
            sync_category=SyncCategory.AGGREGATION.value,
            created_by=created_by,
        )
        session.total_instances = len(active_instances)
        db.session.add(session)
        db.session.commit()

        records = sync_session_service.add_instance_records(
            session.session_id,
            [inst.id for inst in active_instances],
            sync_category=SyncCategory.AGGREGATION.value,
        )
        records_by_instance = {record.instance_id: record for record in records}

        def _start_callback(instance: Instance) -> None:
            record = records_by_instance.get(instance.id)
            if not record or record.id in started_record_ids:
                return
            if sync_session_service.start_instance_sync(record.id):
                started_record_ids.add(record.id)

        def _complete_callback(instance: Instance, payload: dict[str, Any]) -> None:
            record = records_by_instance.get(instance.id)
            if not record:
                return
            if record.id not in started_record_ids:
                if sync_session_service.start_instance_sync(record.id):
                    started_record_ids.add(record.id)
            status = (payload.get("status") or AggregationStatus.FAILED.value).lower()
            processed = int(payload.get("processed_records") or 0)
            details = {
                "period_type": period_type,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "aggregation_result": payload,
                "aggregation_count": processed,
                "scope": scope,
            }
            if status == AggregationStatus.FAILED.value:
                error_message = payload.get("error") or payload.get("message") or "聚合失败"
                sync_session_service.fail_instance_sync(record.id, error_message, sync_details=details)
            else:
                sync_session_service.complete_instance_sync(
                    record.id,
                    items_synced=processed,
                    sync_details=details,
                )
            finalized_record_ids.add(record.id)

        def _error_callback(instance: Instance, payload: dict[str, Any]) -> None:
            record = records_by_instance.get(instance.id)
            if not record:
                return
            if record.id not in started_record_ids:
                if sync_session_service.start_instance_sync(record.id):
                    started_record_ids.add(record.id)
            error_message = payload.get("error") or payload.get("message") or "聚合失败"
            details = {
                "period_type": period_type,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "aggregation_result": payload,
                "aggregation_count": 0,
                "scope": scope,
            }
            sync_session_service.fail_instance_sync(record.id, error_message, sync_details=details)
            finalized_record_ids.add(record.id)

        progress_callbacks: dict[str, dict[str, Callable[..., None]]] = {}
        if scope in {"database", "all"}:
            progress_callbacks["database"] = {
                "on_start": _start_callback,
                "on_complete": _complete_callback,
                "on_error": _error_callback,
            }
        if scope in {"instance", "all"}:
            progress_callbacks["instance"] = {
                "on_start": _start_callback,
                "on_complete": _complete_callback,
                "on_error": _error_callback,
            }

        try:
            raw_result = service.aggregate_current_period(
                period_type=period_type,
                scope=scope,
                progress_callbacks=progress_callbacks,
            )
        except Exception as exc:
            for record in records_by_instance.values():
                if record.id not in finalized_record_ids:
                    sync_session_service.fail_instance_sync(
                        record.id,
                        error_message=f"当前周期聚合异常: {exc}",
                        sync_details={
                            "period_type": period_type,
                            "period_start": start_date.isoformat(),
                            "period_end": end_date.isoformat(),
                            "aggregation_result": {"status": AggregationStatus.FAILED.value, "error": str(exc)},
                            "scope": scope,
                        },
                    )
            current_session = sync_session_service.get_session_by_id(session.session_id)
            if current_session:
                current_session.status = "failed"
                current_session.completed_at = time_utils.now()
                db.session.add(current_session)
                db.session.commit()
            raise

        # 如果没有活跃实例，直接把会话标记为完成
        if session.total_instances == 0:
            refreshed_session = sync_session_service.get_session_by_id(session.session_id)
            if refreshed_session:
                refreshed_session.status = "completed"
                refreshed_session.completed_at = time_utils.now()
                db.session.add(refreshed_session)
                db.session.commit()

        if records_by_instance and len(finalized_record_ids) < len(records_by_instance):
            for record in records_by_instance.values():
                if record.id in finalized_record_ids:
                    continue
                sync_session_service.fail_instance_sync(
                    record.id,
                    error_message="聚合结果缺失",
                    sync_details={
                        "period_type": period_type,
                        "period_start": start_date.isoformat(),
                        "period_end": end_date.isoformat(),
                        "aggregation_result": {"status": "unknown"},
                        "aggregation_count": 0,
                        "scope": scope,
                    },
                )

        refreshed_session = sync_session_service.get_session_by_id(session.session_id)
        if refreshed_session:
            raw_result.setdefault("session", refreshed_session.to_dict())
        else:
            raw_result.setdefault("session", {"session_id": session.session_id})

        result = _normalize_task_result(raw_result, context=f"{period_type} 当前周期聚合")
        result["scope"] = scope
        result["requested_period_type"] = requested_period_type
        result["effective_period_type"] = period_type

        session_info = result.get("session") or {}
        log_info(
            "当前周期数据聚合任务已触发",
            module="aggregations",
            period_type=period_type,
            session_id=session_info.get("session_id"),
        )

        return jsonify_unified_success(
            data={'result': result},
            message='已仅聚合今日数据',
        )

    except AppValidationError:
        raise
    except Exception as exc:
        session_id = None
        if session is not None:
            session_id = getattr(session, "session_id", None)
        log_error(
            "触发当前周期数据聚合失败",
            module="aggregations",
            error=str(exc),
            session_id=session_id,
        )
        raise SystemError("触发当前周期数据聚合失败") from exc
