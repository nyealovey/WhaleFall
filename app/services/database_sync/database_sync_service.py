"""
数据库容量同步服务

该模块提供与历史版本兼容的 `DatabaseSizeCollectorService`，内部委托
`app.services.database_sync` 中的协调器与适配器完成工作。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.models.instance import Instance
from .coordinator import CapacitySyncCoordinator
from app.utils.structlog_config import get_system_logger


class DatabaseSizeCollectorService:
    """数据库容量采集服务（兼容包装器）。"""

    def __init__(self, instance: Instance) -> None:
        self.instance = instance
        self.logger = get_system_logger()
        self._coordinator = CapacitySyncCoordinator(instance)

    def __enter__(self) -> "DatabaseSizeCollectorService":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: D401
        self.disconnect()

    # --------------------------------------------------------------------- #
    # 连接管理
    # --------------------------------------------------------------------- #
    def connect(self) -> bool:
        return self._coordinator.connect()

    def disconnect(self) -> None:
        self._coordinator.disconnect()

    # --------------------------------------------------------------------- #
    # 库存同步
    # --------------------------------------------------------------------- #
    def fetch_databases_metadata(self) -> List[dict]:
        return self._coordinator.fetch_inventory()

    def sync_instance_databases(self, metadata: Iterable[dict]) -> dict:
        return self._coordinator.sync_instance_databases(metadata)

    def synchronize_database_inventory(self) -> dict:
        return self._coordinator.synchronize_inventory()

    # --------------------------------------------------------------------- #
    # 容量采集
    # --------------------------------------------------------------------- #
    def collect_database_sizes(
        self,
        target_databases: Optional[Sequence[str]] = None,
    ) -> List[dict]:
        return self._coordinator.collect_capacity(target_databases)

    # --------------------------------------------------------------------- #
    # 数据持久化
    # --------------------------------------------------------------------- #
    def save_collected_data(self, data: Iterable[dict]) -> int:
        return self._coordinator.save_database_stats(data)

    def save_instance_size_stat(self, data: Iterable[dict]) -> bool:
        return self._coordinator.save_instance_stats(data)

    def update_instance_total_size(self) -> bool:
        return self._coordinator.update_instance_total_size()

    # --------------------------------------------------------------------- #
    # 综合流程
    # --------------------------------------------------------------------- #
    def collect_and_save(self) -> int:
        return self._coordinator.collect_and_save()


def collect_all_instances_database_sizes() -> Dict[str, Any]:
    """
    采集所有活跃实例的数据库容量数据。

    Returns:
        Dict[str, Any]: 采集结果统计
    """
    from app.models.instance import Instance

    logger = get_system_logger()
    logger.info("开始采集所有实例的数据库容量数据...")

    instances = Instance.query.filter_by(is_active=True).all()
    if not instances:
        logger.warning("没有找到活跃的数据库实例")
        return {
            "status": "success",
            "total_instances": 0,
            "processed_instances": 0,
            "total_records": 0,
            "errors": [],
        }

    results: Dict[str, Any] = {
        "status": "success",
        "total_instances": len(instances),
        "processed_instances": 0,
        "total_records": 0,
        "errors": [],
    }

    for instance in instances:
        try:
            logger.info(
                "开始采集实例数据库容量",
                instance=instance.name,
                db_type=instance.db_type,
            )
            with DatabaseSizeCollectorService(instance) as collector:
                saved_count = collector.collect_and_save()
                results["processed_instances"] += 1
                results["total_records"] += saved_count
                logger.info(
                    "实例容量采集完成",
                    instance=instance.name,
                    saved_count=saved_count,
                )
        except Exception as exc:  # noqa: BLE001
            error_msg = f"实例 {instance.name} 采集失败: {exc}"
            logger.error(
                "capacity_collection_failed",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            results["errors"].append(error_msg)

    if results["errors"]:
        results["status"] = "partial_success"

    logger.info(
        "数据库容量采集完成",
        processed_instances=results["processed_instances"],
        total_instances=results["total_instances"],
        total_records=results["total_records"],
    )
    return results
