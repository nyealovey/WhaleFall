"""聚合统计路由"""

from datetime import datetime
from typing import Any, Callable

from flask import Blueprint, Response, request
from flask_login import current_user, login_required
from sqlalchemy import and_, desc, func, or_

from app import db
from app.errors import SystemError, ValidationError as AppValidationError
from app.constants import SyncStatus
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.services.aggregation.aggregation_service import AggregationService
from app.services.aggregation.results import AggregationStatus
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import time_utils

# 创建蓝图
aggregations_bp = Blueprint('aggregations', __name__)

# 聚合模块专注于核心聚合功能，不包含页面路由

# 核心聚合功能API
@aggregations_bp.route('/api/summary', methods=['GET'])
@login_required
@view_required
def get_aggregations_summary() -> Response:
    """
    获取统计聚合数据汇总统计
    
    Returns:
        JSON: 汇总统计信息
    """
    try:
        # 获取基本统计
        total_aggregations = DatabaseSizeAggregation.query.count()
        total_instances = Instance.query.filter_by(is_active=True).count()
        
        # 获取数据库数量统计
        total_databases = db.session.query(
            func.count(func.distinct(DatabaseSizeAggregation.database_name))
        ).scalar() or 0
        
        # 获取大小统计
        size_stats = db.session.query(
            func.sum(DatabaseSizeAggregation.avg_size_mb).label('total_size_mb'),
            func.avg(DatabaseSizeAggregation.avg_size_mb).label('avg_size_mb'),
            func.max(DatabaseSizeAggregation.avg_size_mb).label('max_size_mb')
        ).first()
        
        # 获取最近更新时间
        latest_aggregation = DatabaseSizeAggregation.query.order_by(
            desc(DatabaseSizeAggregation.calculated_at)
        ).first()
        
        payload = {
            'total_aggregations': total_aggregations,
            'total_instances': total_instances,
            'total_databases': total_databases,
            'total_size_mb': float(size_stats.total_size_mb) if size_stats.total_size_mb else 0,
            'avg_size_mb': float(size_stats.avg_size_mb) if size_stats.avg_size_mb else 0,
            'max_size_mb': float(size_stats.max_size_mb) if size_stats.max_size_mb else 0,
            'last_updated': latest_aggregation.calculated_at.isoformat() if latest_aggregation else None
        }

        log_info(
            "获取聚合汇总统计成功",
            module="aggregations",
            total_aggregations=total_aggregations,
            total_instances=total_instances,
            total_databases=total_databases,
        )

        return jsonify_unified_success(data=payload, message="聚合汇总统计获取成功")

    except Exception as exc:
        log_error("获取聚合汇总统计失败", module="aggregations", error=str(exc))
        raise SystemError("获取聚合汇总统计失败") from exc

def _normalize_task_result(result: dict | None, *, context: str) -> dict:
    if not result:
        raise SystemError(f"{context}任务返回为空")
    status = (result.get("status") or "completed").lower()
    if status == SyncStatus.FAILED:
        raise SystemError(result.get("message") or f"{context}执行失败")
    normalized = dict(result)
    normalized["status"] = status
    return normalized


@aggregations_bp.route('/api/manual_aggregate', methods=['POST'])
@login_required
@view_required
@require_csrf
def manual_aggregate() -> Response:
    """
    手动触发聚合计算
    
    Returns:
        JSON: 聚合结果
    """
    try:
        data = request.get_json() or {}
        instance_id = data.get('instance_id')
        period_type = (data.get('period_type') or 'all').lower()
        valid_periods = {'daily', 'weekly', 'monthly', 'quarterly'}
        scope = (data.get('scope') or 'instance').lower()
        valid_scopes = {'instance', 'database'}
        if scope not in valid_scopes:
            raise AppValidationError("scope 参数仅支持 instance 或 database")

        service = AggregationService()

        if instance_id is not None:
            try:
                instance_id = int(instance_id)
            except (TypeError, ValueError) as exc:
                raise AppValidationError("实例ID必须为整数") from exc

            if period_type in valid_periods:
                if scope == 'database':
                    func_map = {
                        'daily': service.calculate_daily_database_aggregations_for_instance,
                        'weekly': service.calculate_weekly_database_aggregations_for_instance,
                        'monthly': service.calculate_monthly_database_aggregations_for_instance,
                        'quarterly': service.calculate_quarterly_database_aggregations_for_instance,
                    }
                else:
                    func_map = {
                        'daily': service.calculate_daily_aggregations_for_instance,
                        'weekly': service.calculate_weekly_aggregations_for_instance,
                        'monthly': service.calculate_monthly_aggregations_for_instance,
                        'quarterly': service.calculate_quarterly_aggregations_for_instance,
                    }
                raw_result = func_map[period_type](instance_id)
            else:
                if scope == 'database':
                    raise AppValidationError("scope=database 时必须指定具体周期类型")
                raw_result = service.calculate_instance_aggregations(instance_id)
        else:
            period_map = {
                'daily': service.calculate_daily_aggregations,
                'weekly': service.calculate_weekly_aggregations,
                'monthly': service.calculate_monthly_aggregations,
                'quarterly': service.calculate_quarterly_aggregations,
            }
            if period_type in valid_periods:
                raw_result = period_map[period_type]()
            else:
                raw_result = service.calculate_all_aggregations()

        result = _normalize_task_result(raw_result, context="聚合计算")
        result["scope"] = scope

        log_info(
            "手动聚合任务已触发",
            module="aggregations",
            period_type=period_type,
            instance_id=instance_id,
        )

        return jsonify_unified_success(
            data={'result': result},
            message=result.get('message', '聚合计算任务已触发'),
        )

    except AppValidationError:
        raise
    except Exception as exc:
        log_error("手动触发聚合计算失败", module="aggregations", error=str(exc))
        raise SystemError("手动触发聚合计算失败") from exc

@aggregations_bp.route('/api/aggregate', methods=['POST'])
@login_required
@view_required
@require_csrf
def aggregate() -> Response:
    """
    手动触发统计聚合计算
    
    Returns:
        JSON: 聚合结果
    """
    try:
        data = request.get_json() or {}
        period_type = (data.get('period_type') or 'all').lower()
        valid_periods = {'daily', 'weekly', 'monthly', 'quarterly'}

        service = AggregationService()
        period_map = {
            'daily': service.calculate_daily_aggregations,
            'weekly': service.calculate_weekly_aggregations,
            'monthly': service.calculate_monthly_aggregations,
            'quarterly': service.calculate_quarterly_aggregations,
        }

        if period_type in valid_periods:
            raw_result = period_map[period_type]()
        else:
            raw_result = service.calculate_all_aggregations()

        result = _normalize_task_result(raw_result, context="统计聚合")

        log_info("统计聚合任务已触发", module="aggregations", period_type=period_type)

        return jsonify_unified_success(
            data={'result': result},
            message=result.get('message', '统计聚合计算任务已触发'),
        )

    except Exception as exc:
        log_error("触发统计聚合计算失败", module="aggregations", error=str(exc))
        raise SystemError("触发统计聚合计算失败") from exc

@aggregations_bp.route('/api/aggregate-current', methods=['POST'])
@login_required
@view_required
@require_csrf
def aggregate_current() -> Response:
    """
    手动触发当前周期数据聚合
    
    Returns:
        JSON: 聚合结果
    """
    session = None
    records_by_instance: dict[int, Any] = {}
    started_record_ids: set[int] = set()
    finalized_record_ids: set[int] = set()

    try:
        payload = request.get_json(silent=True) or {}
        period_type = (payload.get("period_type") or "daily").lower()
        scope = (payload.get("scope") or "all").lower()
        valid_scopes = {"instance", "database", "all"}
        if scope not in valid_scopes:
            raise AppValidationError("scope 参数仅支持 instance、database 或 all")

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

        session_info = result.get("session") or {}
        log_info(
            "当前周期数据聚合任务已触发",
            module="aggregations",
            period_type=period_type,
            session_id=session_info.get("session_id"),
        )

        return jsonify_unified_success(
            data={'result': result},
            message='当前周期数据聚合任务已触发',
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
