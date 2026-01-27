"""Instance capacity sync actions service.

将 `POST /api/v1/instances/<id>/actions/sync-capacity` 的“动作编排”逻辑下沉到 service 层：
- 实例查询 + coordinator 调度
- inventory 同步 + 容量采集 + stats 保存
- 触发聚合（失败仅记录 warning，不影响主流程）

路由层仅负责鉴权/CSRF、调用 service 与封套响应。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import app.services.aggregation as aggregation_module
import app.services.database_sync as database_sync_module
from app.core.constants import HttpStatus
from app.core.exceptions import NotFoundError
from app.models.instance import Instance
from app.repositories.instances_repository import InstancesRepository
from app.utils.structlog_config import log_fallback


@dataclass(frozen=True, slots=True)
class InstanceCapacitySyncActionResult:
    """实例容量同步动作结果（供路由层决定封套与状态码）."""

    success: bool
    message: str
    result: dict[str, Any]
    http_status: int = 200
    message_key: str = "OPERATION_SUCCESS"
    extra: Mapping[str, Any] | None = None


class InstanceCapacitySyncActionsService:
    """实例容量同步动作编排服务."""

    @staticmethod
    def _get_instance(instance_id: int) -> Instance:
        instance = InstancesRepository.get_instance(instance_id)
        if instance is None:
            raise NotFoundError("实例不存在")
        return instance

    def sync_instance_capacity(self, *, instance_id: int) -> InstanceCapacitySyncActionResult:
        """同步指定实例的容量信息(包含 inventory + stats + 聚合触发)."""
        instance = self._get_instance(instance_id)

        coordinator = database_sync_module.CapacitySyncCoordinator(instance)
        if not coordinator.connect():
            return InstanceCapacitySyncActionResult(
                success=False,
                message=f"无法连接到实例 {instance.name}",
                result={},
                http_status=HttpStatus.CONFLICT,
                message_key="DATABASE_CONNECTION_ERROR",
                extra={"instance_id": instance.id},
            )

        try:
            inventory_result = coordinator.synchronize_inventory()
            active_databases = set(inventory_result.get("active_databases", []))

            if not active_databases:
                normalized: dict[str, Any] = {
                    "status": "completed",
                    "databases": [],
                    "database_count": 0,
                    "total_size_mb": 0,
                    "saved_count": 0,
                    "instance_stat_updated": False,
                    "inventory": inventory_result,
                    "message": "未发现活跃数据库,已仅同步数据库列表",
                }
                return InstanceCapacitySyncActionResult(
                    success=True,
                    message=f"实例 {instance.name} 的容量同步任务已成功完成",
                    result=normalized,
                )

            try:
                databases_data = coordinator.collect_capacity(list(active_databases))
            except (RuntimeError, ConnectionError, TimeoutError, OSError):
                return InstanceCapacitySyncActionResult(
                    success=False,
                    message="容量采集失败",
                    result={},
                    http_status=HttpStatus.CONFLICT,
                    message_key="SYNC_DATA_ERROR",
                    extra={"instance_id": instance.id},
                )

            if not databases_data:
                return InstanceCapacitySyncActionResult(
                    success=False,
                    message="未采集到任何数据库大小数据",
                    result={},
                    http_status=HttpStatus.CONFLICT,
                    message_key="SYNC_DATA_ERROR",
                    extra={"instance_id": instance.id},
                )

            database_count = len(databases_data)

            def _coalesce_int(value: Any) -> int:
                return int(value) if value is not None else 0

            total_size_mb = sum(_coalesce_int(db.get("size_mb")) for db in databases_data)
            saved_count = coordinator.save_database_stats(databases_data)
            instance_stat_updated = coordinator.update_instance_total_size()

            try:
                aggregation_service = aggregation_module.AggregationService()
                aggregation_service.calculate_daily_database_aggregations_for_instance(instance.id)
                aggregation_service.calculate_daily_aggregations_for_instance(instance.id)
            except Exception as exc:
                log_fallback(
                    "warning",
                    "容量同步后触发聚合失败",
                    module="databases_capacity",
                    action="sync_instance_capacity",
                    fallback_reason="aggregation_calculation_failed",
                    instance_id=instance.id,
                    exception=exc,
                )

            normalized = {
                "status": "completed",
                "databases": databases_data,
                "database_count": database_count,
                "total_size_mb": total_size_mb,
                "saved_count": saved_count,
                "instance_stat_updated": instance_stat_updated,
                "inventory": inventory_result,
                "message": f"成功采集并保存 {database_count} 个数据库的容量信息",
            }
            return InstanceCapacitySyncActionResult(
                success=True,
                message=f"实例 {instance.name} 的容量同步任务已成功完成",
                result=normalized,
            )
        finally:
            coordinator.disconnect()
