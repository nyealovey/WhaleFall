"""聚合统计路由"""

from datetime import datetime

from flask import Blueprint, Response, request
from flask_login import login_required
from sqlalchemy import and_, desc, func, or_

from app import db
from app.errors import SystemError, ValidationError as AppValidationError
from app.constants import SyncStatus
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.services.aggregation.database_size_aggregation_service import DatabaseSizeAggregationService
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

        service = DatabaseSizeAggregationService()

        if instance_id is not None:
            try:
                instance_id = int(instance_id)
            except (TypeError, ValueError) as exc:
                raise AppValidationError("实例ID必须为整数") from exc

            if period_type in valid_periods:
                func_map = {
                    'daily': service.calculate_daily_aggregations_for_instance,
                    'weekly': service.calculate_weekly_aggregations_for_instance,
                    'monthly': service.calculate_monthly_aggregations_for_instance,
                    'quarterly': service.calculate_quarterly_aggregations_for_instance,
                }
                raw_result = func_map[period_type](instance_id)
            else:
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

        service = DatabaseSizeAggregationService()
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

@aggregations_bp.route('/api/aggregate-today', methods=['POST'])
@login_required
@view_required
@require_csrf
def aggregate_today() -> Response:
    """
    手动触发今日数据聚合
    
    Returns:
        JSON: 聚合结果
    """
    try:
        # 触发今日数据聚合（只执行日聚合）
        service = DatabaseSizeAggregationService()
        raw_result = service.calculate_daily_aggregations()
        result = _normalize_task_result(raw_result, context="今日聚合")

        log_info("今日数据聚合任务已触发", module="aggregations")

        return jsonify_unified_success(
            data={'result': result},
            message='今日数据聚合任务已触发',
        )

    except Exception as exc:
        log_error("触发今日数据聚合失败", module="aggregations", error=str(exc))
        raise SystemError("触发今日数据聚合失败") from exc

@aggregations_bp.route('/api/aggregate/status', methods=['GET'])
@login_required
@view_required
def get_aggregation_status_api() -> Response:
    """获取聚合状态信息"""
    try:
        status = task_get_aggregation_status()
        payload = {
            'status': status,
            'timestamp': time_utils.now().isoformat(),
        }

        log_info("获取聚合状态成功", module="aggregations", status_summary=status)
        return jsonify_unified_success(data=payload, message="聚合状态获取成功")

    except Exception as exc:
        log_error("获取聚合状态失败", module="aggregations", error=str(exc))
        raise SystemError("获取聚合状态失败") from exc
