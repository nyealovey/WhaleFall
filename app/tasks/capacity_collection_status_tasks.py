"""容量采集状态/配置入口."""

from __future__ import annotations

from typing import Any

from app import create_app
from app.services.capacity.capacity_collection_status_service import CapacityCollectionStatusService
from app.services.capacity.capacity_collection_task_runner import CAPACITY_TASK_EXCEPTIONS
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


def get_collection_status() -> dict[str, Any]:
    """获取数据库大小采集状态."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            status = CapacityCollectionStatusService().get_status(today=time_utils.now_china().date())
            return {
                "success": True,
                "total_records": status.total_records,
                "today_records": status.today_records,
                "latest_collection": status.latest_collection.isoformat() if status.latest_collection else None,
                "collection_enabled": bool(app.config.get("COLLECT_DB_SIZE_ENABLED", True)),
            }
        except CAPACITY_TASK_EXCEPTIONS as exc:
            sync_logger = get_sync_logger()
            sync_logger.exception(
                "获取容量采集状态失败",
                module="capacity_sync",
                error=str(exc),
            )
            return {
                "success": False,
                "message": f"获取状态失败: {exc!s}",
                "error": str(exc),
            }


def validate_collection_config() -> dict[str, Any]:
    """验证数据库大小采集配置."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            config_checks = {
                "COLLECT_DB_SIZE_ENABLED": bool(app.config.get("COLLECT_DB_SIZE_ENABLED", True)),
                "DB_SIZE_COLLECTION_INTERVAL": int(app.config.get("DB_SIZE_COLLECTION_INTERVAL", 24)),
                "DB_SIZE_COLLECTION_TIMEOUT": int(app.config.get("DB_SIZE_COLLECTION_TIMEOUT", 300)),
            }
        except CAPACITY_TASK_EXCEPTIONS as exc:
            sync_logger = get_sync_logger()
            sync_logger.exception(
                "容量采集配置验证失败",
                module="capacity_sync",
                error=str(exc),
            )
            return {
                "success": False,
                "message": f"配置验证失败: {exc!s}",
                "error": str(exc),
            }
        else:
            return {
                "success": True,
                "config": config_checks,
                "service_available": True,
                "message": "配置验证通过",
            }
