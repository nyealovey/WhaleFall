"""容量采集手动任务入口.

用于按实例/按 db_type 手动触发容量采集.
"""

from __future__ import annotations

from typing import Any

from app import create_app, db
from app.services.capacity.capacity_collection_task_runner import (
    CAPACITY_TASK_EXCEPTIONS,
    CapacityCollectionTaskRunner,
)
from app.utils.structlog_config import get_sync_logger


def collect_specific_instance_database_sizes(instance_id: int) -> dict[str, Any]:
    """采集指定实例的数据库大小信息."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        runner = CapacityCollectionTaskRunner()
        sync_logger.info(
            "开始采集实例数据库大小",
            module="capacity_sync",
            instance_id=instance_id,
        )
        try:
            result = runner.collect_instance_database_sizes(instance_id=instance_id, logger=sync_logger)
            db.session.commit()
            return dict(result)
        except CAPACITY_TASK_EXCEPTIONS as exc:
            db.session.rollback()
            sync_logger.exception(
                "采集实例数据库大小失败",
                module="capacity_sync",
                instance_id=instance_id,
                error=str(exc),
            )
            return {
                "success": False,
                "message": f"采集失败: {exc!s}",
                "error": str(exc),
            }


def collect_database_sizes_by_type(db_type: str) -> dict[str, Any]:
    """采集指定类型数据库的大小信息."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        runner = CapacityCollectionTaskRunner()
        try:
            sync_logger.info(
                "开始按照数据库类型采集容量",
                module="capacity_sync",
                db_type=db_type,
            )

            instances = runner.list_active_instances(db_type=db_type)
            if not instances:
                return {
                    "success": True,
                    "message": f"没有找到 {db_type} 类型的活跃实例",
                    "instances_processed": 0,
                }

            sync_logger.info(
                "找到活跃实例",
                module="capacity_sync",
                db_type=db_type,
                instance_count=len(instances),
            )

            total_processed = 0
            total_size_mb = 0
            errors: list[str] = []

            for instance in instances:
                try:
                    result = runner.collect_instance_database_sizes(instance_id=instance.id, logger=sync_logger)
                    db.session.commit()
                    if result.get("success"):
                        total_processed += 1
                        total_size_mb += int(result.get("total_size_mb") or 0)
                    else:
                        errors.append(f"实例 {instance.name}: {result.get('message')}")
                except CAPACITY_TASK_EXCEPTIONS as exc:
                    db.session.rollback()
                    errors.append(f"实例 {instance.name}: {exc!s}")

        except CAPACITY_TASK_EXCEPTIONS as exc:
            db.session.rollback()
            sync_logger.exception(
                "按类型采集数据库容量失败",
                module="capacity_sync",
                db_type=db_type,
                error=str(exc),
            )
            return {
                "success": False,
                "message": f"采集失败: {exc!s}",
                "error": str(exc),
            }
        else:
            return {
                "success": True,
                "message": f"{db_type} 类型数据库大小采集完成",
                "instances_processed": total_processed,
                "total_size_mb": total_size_mb,
                "errors": errors,
            }

