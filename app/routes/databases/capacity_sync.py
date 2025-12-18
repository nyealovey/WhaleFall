"""数据库域:容量同步 API 路由.

专注于数据同步功能,不包含统计功能.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response

from app.errors import ConflictError, DatabaseError, NotFoundError
from app.models.instance import Instance
from app.services.aggregation.aggregation_service import AggregationService
from app.services.database_sync import CapacitySyncCoordinator
from app.utils.decorators import require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import log_with_context, safe_route_call
from app.utils.structlog_config import log_info, log_warning

# 创建蓝图
databases_capacity_bp = Blueprint("databases_capacity", __name__)

COLLECTOR_EXCEPTIONS: tuple[type[Exception], ...] = (
    DatabaseError,
    RuntimeError,
    ValueError,
    OSError,
    ConnectionError,
)


def _get_instance(instance_id: int) -> Instance:
    """获取实例或抛出错误.

    Args:
        instance_id: 实例 ID.

    Returns:
        实例对象.

    Raises:
        NotFoundError: 当实例不存在时抛出.

    """
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance is None:
        msg = "实例不存在"
        raise NotFoundError(msg)
    return instance


def _collect_instance_capacity(instance: Instance) -> dict[str, Any]:
    """采集实例容量信息.

    连接数据库,同步数据库列表,采集大小信息并保存.

    Args:
        instance: 实例对象.

    Returns:
        包含采集结果的字典:
        - success: 是否成功
        - databases: 数据库列表
        - database_count: 数据库数量
        - total_size_mb: 总大小(MB)
        - saved_count: 保存的记录数
        - instance_stat_updated: 实例统计是否更新
        - inventory: 数据库清单同步结果
        - message: 结果消息

    """
    collector = CapacitySyncCoordinator(instance)

    if not collector.connect():
        return {
            "success": False,
            "message": f"无法连接到实例 {instance.name}",
        }

    try:
        try:
            inventory_result = collector.synchronize_database_inventory()
        except COLLECTOR_EXCEPTIONS as inventory_error:
            log_with_context(
                "error",
                "同步数据库列表失败",
                module="databases_capacity",
                action="synchronize_database_inventory",
                context={"instance_id": instance.id, "instance_name": instance.name},
                extra={"error_message": str(inventory_error), "exc_info": True},
            )
            return {
                "success": False,
                "message": f"同步数据库列表失败: {inventory_error}",
            }

        active_databases = set(inventory_result.get("active_databases", []))

        if not active_databases:
            return {
                "success": True,
                "databases": [],
                "database_count": 0,
                "total_size_mb": 0,
                "saved_count": 0,
                "instance_stat_updated": False,
                "inventory": inventory_result,
                "message": "未发现活跃数据库,已仅同步数据库列表",
            }

        databases_data = collector.collect_capacity(list(active_databases))
        if not databases_data:
            return {
                "success": False,
                "message": "未采集到任何数据库大小数据",
                "inventory": inventory_result,
            }

        database_count = len(databases_data)
        total_size_mb = sum(db.get("size_mb", 0) for db in databases_data)

        try:
            saved_count = collector.save_database_stats(databases_data)
        except COLLECTOR_EXCEPTIONS as exc:
            log_with_context(
                "error",
                "保存数据库容量数据失败",
                module="databases_capacity",
                action="save_collected_data",
                context={"instance_id": instance.id, "instance_name": instance.name},
                extra={"error_message": str(exc), "exc_info": True},
            )
            return {
                "success": False,
                "message": f"采集成功但保存数据失败: {exc}",
                "error": str(exc),
            }

        instance_stat_updated = collector.update_instance_total_size()

        try:
            aggregation_service = AggregationService()
            aggregation_service.calculate_daily_database_aggregations_for_instance(instance.id)
            aggregation_service.calculate_daily_aggregations_for_instance(instance.id)
        except COLLECTOR_EXCEPTIONS as exc:
            log_warning(
                "容量聚合刷新失败",
                module="databases_capacity",
                instance_id=instance.id,
                instance_name=instance.name,
                error=str(exc),
            )

        return {
            "success": True,
            "databases": databases_data,
            "database_count": database_count,
            "total_size_mb": total_size_mb,
            "saved_count": saved_count,
            "instance_stat_updated": instance_stat_updated,
            "inventory": inventory_result,
            "message": f"成功采集并保存 {database_count} 个数据库的容量信息",
        }
    finally:
        collector.disconnect()


@databases_capacity_bp.route("/api/instances/<int:instance_id>/sync-capacity", methods=["POST"])
@view_required(permission="instance_management.instance_list.sync_capacity")
@require_csrf
def sync_instance_capacity(instance_id: int) -> tuple[Response, int]:
    """同步指定实例的容量信息.

    采集数据库大小信息并保存到统计表,同时触发聚合计算.

    Args:
        instance_id: 实例 ID.

    Returns:
        JSON 响应,包含容量同步结果、数据库数量和总大小.

    Raises:
        NotFoundError: 当实例不存在时抛出.
        ConflictError: 当同步失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        instance = _get_instance(instance_id)
        log_info(
            "用户操作: 开始同步容量",
            module="databases_capacity",
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
                module="databases_capacity",
                instance_id=instance.id,
                instance_name=instance.name,
                action="同步容量成功",
                user_action=True,
            )
            normalized_result = dict(result)
            normalized_result.pop("success", None)
            normalized_result.setdefault("status", "completed")
            return jsonify_unified_success(
                data={"result": normalized_result},
                message=f"实例 {instance.name} 的容量同步任务已成功完成",
            )

        log_warning(
            "同步实例容量失败",
            module="databases_capacity",
            instance_id=instance.id,
            instance_name=instance.name,
            action="同步容量失败",
            user_action=True,
            result=result,
        )
        error_message = (result or {}).get("message") or "实例容量同步失败"
        raise ConflictError(error_message)

    return safe_route_call(
        _execute,
        module="databases_capacity",
        action="sync_instance_capacity",
        public_error="同步实例容量失败",
        expected_exceptions=(NotFoundError, ConflictError),
        context={"instance_id": instance_id},
    )
