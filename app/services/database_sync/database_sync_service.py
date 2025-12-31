"""数据库容量同步服务.

暴露面向任务/路由的容量采集入口,直接委托 `CapacitySyncCoordinator`
执行连接、清单同步与容量采集。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.errors import AppError
from app.models.instance import Instance
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.utils.structlog_config import get_system_logger

from .coordinator import CapacitySyncCoordinator

DATABASE_SYNC_EXCEPTIONS: tuple[type[BaseException], ...] = (
    AppError,
    ConnectionAdapterError,
    SQLAlchemyError,
    RuntimeError,
    LookupError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def collect_all_instances_database_sizes() -> dict[str, Any]:
    """采集所有活跃实例的数据库容量数据.

    遍历所有活跃实例,依次执行容量采集和保存操作.

    Returns:
        采集结果统计字典,包含以下字段:
        {
            'status': 'success' 或 'partial_success',
            'total_instances': 总实例数,
            'processed_instances': 成功处理的实例数,
            'total_records': 保存的记录总数,
            'errors': 错误信息列表
        }

    """
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

    results: dict[str, Any] = {
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
            with CapacitySyncCoordinator(instance) as coordinator:
                saved_count = coordinator.collect_and_save()
                results["processed_instances"] += 1
                results["total_records"] += saved_count
                logger.info(
                    "实例容量采集完成",
                    instance=instance.name,
                    saved_count=saved_count,
                )
        except DATABASE_SYNC_EXCEPTIONS as exc:
            error_msg = f"实例 {instance.name} 采集失败: {exc}"
            logger.exception(
                "capacity_collection_failed",
                instance=instance.name,
                error=str(exc),
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
