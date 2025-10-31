"""
存储同步 API 路由
专注于数据同步功能，不包含统计功能
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, Response, render_template, request
from flask_login import login_required

from app.constants.system_constants import SuccessMessages
from app.constants import SyncStatus, TaskStatus
from app.errors import NotFoundError, SystemError
from app.models.instance import Instance
from app.services.aggregation.database_size_aggregation_service import DatabaseSizeAggregationService
from app.services.capacity_sync_adapters.capacity_sync_service import DatabaseSizeCollectorService
from app.utils.decorators import require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info, log_warning

# 创建蓝图
storage_sync_bp = Blueprint('storage_sync', __name__)


def _get_instance(instance_id: int) -> Instance:
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance is None:
        raise NotFoundError("实例不存在")
    return instance


def _collect_instance_capacity(instance: Instance) -> Dict[str, Any]:
    collector = DatabaseSizeCollectorService(instance)

    if not collector.connect():
        return {
            'success': False,
            'message': f'无法连接到实例 {instance.name}',
        }

    try:
        databases_data = collector.collect_database_sizes()
        if not databases_data:
            return {
                'success': False,
                'message': '未采集到任何数据库大小数据',
            }

        database_count = len(databases_data)
        total_size_mb = sum(db.get('size_mb', 0) for db in databases_data)

        try:
            saved_count = collector.save_collected_data(databases_data)
        except Exception as exc:  # noqa: BLE001
            log_error(
                "保存数据库容量数据失败",
                module="storage_sync",
                instance_id=instance.id,
                instance_name=instance.name,
                error=str(exc),
                exc_info=True,
            )
            return {
                'success': False,
                'message': f'采集成功但保存数据失败: {exc}',
                'error': str(exc),
            }

        instance_stat_updated = collector.update_instance_total_size()

        try:
            aggregation_service = DatabaseSizeAggregationService()
            aggregation_service.calculate_daily_database_aggregations_for_instance(instance.id)
            aggregation_service.calculate_daily_aggregations_for_instance(instance.id)
        except Exception as exc:  # noqa: BLE001
            log_warning(
                "容量聚合刷新失败",
                module="storage_sync",
                instance_id=instance.id,
                instance_name=instance.name,
                error=str(exc),
            )

        return {
            'success': True,
            'databases': databases_data,
            'database_count': database_count,
            'total_size_mb': total_size_mb,
            'saved_count': saved_count,
            'instance_stat_updated': instance_stat_updated,
            'message': f'成功采集并保存 {database_count} 个数据库的容量信息',
        }
    finally:
        collector.disconnect()

@storage_sync_bp.route("/api/instances/<int:instance_id>/sync-capacity", methods=["POST"])
@view_required("instance_management.instance_list.sync_capacity")
@require_csrf
def sync_instance_capacity(instance_id: int) -> Response:
    """
    同步指定实例的容量信息

    Args:
        instance_id (int): 实例ID

    Returns:
        json: 同步结果
    """
    try:
        instance = _get_instance(instance_id)
        log_info(
            "用户操作: 开始同步容量",
            module="storage_sync",
            operation="sync_capacity",
            instance_id=instance.id,
            instance_name=instance.name,
            action="开始同步容量",
            user_action=True,
        )

        result = _collect_instance_capacity(instance)

        if result and result.get("success"):
            log_info(
                "同步实例容量成功",
                module="storage_sync",
                instance_id=instance.id,
                instance_name=instance.name,
                action="同步容量成功",
                user_action=True,
            )
            normalized_result = dict(result)
            normalized_result.pop("success", None)
            normalized_result.setdefault("status", "completed")
            return jsonify_unified_success(
                data={'result': normalized_result},
                message=f'实例 {instance.name} 的容量同步任务已成功完成',
            )

        log_warning(
            "同步实例容量失败",
            module="storage_sync",
            instance_id=instance.id,
            instance_name=instance.name,
            action="同步容量失败",
            user_action=True,
            result=result,
        )
        error_message = result.get("message") or result.get("error") or "实例容量同步失败"
        raise SystemError(error_message)
        
    except NotFoundError:
        raise
    except Exception as exc:
        log_error(
            "同步实例容量失败",
            module="storage_sync",
            instance_id=instance_id,
            error=str(exc),
        )
        raise SystemError("同步实例容量失败") from exc
