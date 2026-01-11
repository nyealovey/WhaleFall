"""容量采集任务 runner.

职责:
- 承载容量采集任务的重逻辑(库存同步、容量采集、结果组装).
- 不创建 Flask app context(由 tasks 层保证).
- 不做 `db.session.commit/rollback`(由写边界入口负责).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import structlog
from sqlalchemy.exc import SQLAlchemyError

from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.errors import AppError
from app.models.instance import Instance
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.services.aggregation.aggregation_service import AggregationService
from app.services.capacity.capacity_tasks_read_service import CapacityTasksReadService
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.services.database_sync import CapacitySyncCoordinator
from app.services.instances.instance_detail_read_service import InstanceDetailReadService
from app.services.sync_session_service import SyncItemStats, sync_session_service

CAPACITY_TASK_EXCEPTIONS: tuple[type[Exception], ...] = (
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


@dataclass(slots=True)
class CapacitySyncTotals:
    """容量同步累计统计."""

    total_synced: int = 0
    total_failed: int = 0
    total_collected_size_mb: int = 0


@dataclass(slots=True)
class CapacityContext:
    """容量同步上下文."""

    collector: CapacitySyncCoordinator
    record: SyncInstanceRecord
    instance: Instance
    session: SyncSession
    sync_logger: structlog.BoundLogger


def _build_failure(message: str, extra: dict[str, object] | None = None) -> dict[str, object]:
    base: dict[str, object] = {"success": False, "message": message}
    if extra:
        base.update(extra)
    return base


def _build_success(message: str, payload: dict[str, object]) -> dict[str, object]:
    base: dict[str, object] = {"success": True, "message": message}
    base.update(payload)
    return base


def _to_int(value: object) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


class CapacityCollectionTaskRunner:
    """容量采集任务 runner(供 tasks 层编排调用)."""

    def list_active_instances(self, *, db_type: str | None = None) -> list[Instance]:
        """获取活跃实例列表."""
        return CapacityTasksReadService().list_active_instances(db_type=db_type)

    @staticmethod
    def no_active_instances_result() -> dict[str, object]:
        return {
            "success": True,
            "message": "没有活跃的数据库实例需要同步",
            "instances_processed": 0,
            "total_size_mb": 0,
        }

    @staticmethod
    def start_instance_sync(record_id: int) -> None:
        sync_session_service.start_instance_sync(record_id)

    @staticmethod
    def fail_instance_sync(record_id: int, error_message: str) -> None:
        sync_session_service.fail_instance_sync(record_id, error_message)

    @staticmethod
    def create_capacity_session(active_instances: list[Instance]) -> tuple[SyncSession, list[SyncInstanceRecord]]:
        session = sync_session_service.create_session(
            sync_type=SyncOperationType.SCHEDULED_TASK.value,
            sync_category=SyncCategory.CAPACITY.value,
            created_by=None,
        )
        records = sync_session_service.add_instance_records(
            session.session_id,
            [inst.id for inst in active_instances],
            sync_category=SyncCategory.CAPACITY.value,
        )
        session.total_instances = len(active_instances)
        return session, records

    @staticmethod
    def _sync_inventory_for_instance(
        *,
        collector: CapacitySyncCoordinator,
        record: SyncInstanceRecord,
        session: SyncSession,
        instance: Instance,
        logger: structlog.BoundLogger,
    ) -> tuple[dict[str, object], bool]:
        logger.info(
            "同步数据库列表",
            module="capacity_sync",
            session_id=session.session_id,
            instance_id=instance.id,
            instance_name=instance.name,
        )
        inventory_result = collector.synchronize_inventory()
        sync_session_service.complete_instance_sync(
            record.id,
            stats=SyncItemStats(
                items_synced=_to_int(inventory_result.get("refreshed", 0)),
                items_created=_to_int(inventory_result.get("created", 0)),
                items_updated=_to_int(inventory_result.get("reactivated", 0)),
                items_deleted=_to_int(inventory_result.get("deactivated", 0)),
            ),
            sync_details={"inventory": inventory_result},
        )
        active_databases = set(inventory_result.get("active_databases", []))
        if not active_databases:
            logger.warning(
                "未发现活跃数据库,仅完成库存同步",
                module="capacity_sync",
                session_id=session.session_id,
                instance_id=instance.id,
                instance_name=instance.name,
            )
            empty_stats = SyncItemStats(
                items_synced=0,
                items_created=0,
                items_updated=0,
                items_deleted=inventory_result.get("deactivated", 0),
            )
            sync_session_service.complete_instance_sync(
                record.id,
                stats=empty_stats,
                sync_details={"inventory": inventory_result},
            )
            return {
                "instance_id": instance.id,
                "instance_name": instance.name,
                "success": True,
                "size_mb": 0,
                "database_count": 0,
                "saved_count": 0,
                "databases": [],
                "inventory": inventory_result,
                "message": "未发现活跃数据库,已仅同步数据库列表",
            }, True
        return {"inventory": inventory_result, "active_databases": active_databases}, False

    @staticmethod
    def _collect_and_save_capacity(
        *,
        context: CapacityContext,
        inventory_result: dict[str, object],
        active_databases: set[str],
    ) -> tuple[dict[str, object], bool]:
        databases_data = context.collector.collect_capacity(list(active_databases))
        if not databases_data:
            error_msg = "未采集到任何数据库大小数据"
            context.sync_logger.error(
                "实例容量同步失败",
                module="capacity_sync",
                session_id=context.session.session_id,
                instance_id=context.instance.id,
                instance_name=context.instance.name,
                error=error_msg,
            )
            sync_session_service.fail_instance_sync(context.record.id, error_msg)
            return {
                "instance_id": context.instance.id,
                "instance_name": context.instance.name,
                "success": False,
                "error": error_msg,
                "inventory": inventory_result,
            }, False

        database_count = len(databases_data)
        instance_total_size_mb = sum(db.get("size_mb", 0) for db in databases_data)
        saved_count = context.collector.save_database_stats(databases_data)
        context.collector.update_instance_total_size()
        sync_session_service.complete_instance_sync(
            context.record.id,
            stats=SyncItemStats(
                items_synced=database_count,
                items_created=_to_int(inventory_result.get("created", 0)),
                items_updated=_to_int(inventory_result.get("refreshed", 0))
                + _to_int(inventory_result.get("reactivated", 0)),
                items_deleted=_to_int(inventory_result.get("deactivated", 0)),
            ),
            sync_details={
                "total_size_mb": instance_total_size_mb,
                "database_count": database_count,
                "saved_count": saved_count,
                "databases": databases_data,
                "inventory": inventory_result,
            },
        )
        return {
            "instance_id": context.instance.id,
            "instance_name": context.instance.name,
            "success": True,
            "size_mb": instance_total_size_mb,
            "database_count": database_count,
            "saved_count": saved_count,
            "databases": databases_data,
            "inventory": inventory_result,
        }, True

    def process_capacity_instance(
        self,
        *,
        session: SyncSession,
        record: SyncInstanceRecord,
        instance: Instance,
        sync_logger: structlog.BoundLogger,
    ) -> tuple[dict[str, object], CapacitySyncTotals]:
        totals = CapacitySyncTotals()
        sync_logger.info(
            "开始实例容量同步",
            module="capacity_sync",
            session_id=session.session_id,
            instance_id=instance.id,
            instance_name=instance.name,
        )
        collector = CapacitySyncCoordinator(instance)
        context = CapacityContext(
            collector=collector,
            record=record,
            instance=instance,
            session=session,
            sync_logger=sync_logger,
        )
        try:
            if not collector.connect():
                error_msg = f"无法连接到实例 {instance.name}"
                sync_logger.error(
                    error_msg,
                    module="capacity_sync",
                    session_id=session.session_id,
                    instance_id=instance.id,
                    instance_name=instance.name,
                )
                sync_session_service.fail_instance_sync(record.id, error_msg)
                totals.total_failed += 1
                return {
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                    "success": False,
                    "error": error_msg,
                }, totals

            inventory_payload, skip_capacity = self._sync_inventory_for_instance(
                collector=collector,
                record=record,
                session=session,
                instance=instance,
                logger=sync_logger,
            )
            if skip_capacity:
                totals.total_synced += 1
                return inventory_payload, totals

            active_databases = cast(set[str], inventory_payload["active_databases"])
            inventory_result = cast(dict[str, object], inventory_payload["inventory"])

            sync_logger.info(
                "开始采集数据库大小",
                module="capacity_sync",
                session_id=session.session_id,
                instance_id=instance.id,
                instance_name=instance.name,
            )

            result, success = self._collect_and_save_capacity(
                context=context,
                inventory_result=inventory_result,
                active_databases=active_databases,
            )
            if success:
                totals.total_synced += 1
                totals.total_collected_size_mb += _to_int(result.get("size_mb", 0))
            else:
                totals.total_failed += 1
        except CAPACITY_TASK_EXCEPTIONS as exc:
            error_msg = f"实例同步异常: {exc!s}"
            sync_logger.exception(
                "实例同步异常",
                module="capacity_sync",
                session_id=session.session_id,
                instance_id=instance.id,
                instance_name=instance.name,
                error=str(exc),
            )
            sync_session_service.fail_instance_sync(record.id, error_msg)
            totals.total_failed += 1
            return {
                "instance_id": instance.id,
                "instance_name": instance.name,
                "success": False,
                "error": str(exc),
            }, totals
        else:
            return result, totals
        finally:
            collector.disconnect()

    @staticmethod
    def _load_active_instance(instance_id: int) -> Instance:
        instance = InstanceDetailReadService().get_instance_by_id(instance_id)
        if not instance:
            raise AppError(f"实例 {instance_id} 不存在")
        if not instance.is_active:
            raise AppError(f"实例 {instance_id} 未激活")
        return instance

    @staticmethod
    def _sync_inventory_for_single_instance(
        *,
        collector: CapacitySyncCoordinator,
        instance: Instance,
        logger: structlog.BoundLogger,
    ) -> tuple[dict[str, object], set[str]]:
        try:
            inventory_result = collector.synchronize_inventory()
        except CAPACITY_TASK_EXCEPTIONS as inventory_error:
            logger.exception(
                "同步数据库列表失败",
                module="capacity_sync",
                instance_id=instance.id,
                instance_name=instance.name,
                error=str(inventory_error),
            )
            raise AppError(f"同步数据库列表失败: {inventory_error}") from inventory_error

        active_databases = set(inventory_result.get("active_databases", []))
        return inventory_result, active_databases

    @staticmethod
    def _save_instance_sizes(
        *,
        collector: CapacitySyncCoordinator,
        instance: Instance,
        inventory_result: dict[str, object],
        active_databases: set[str],
        logger: structlog.BoundLogger,
    ) -> dict[str, object]:
        databases_data = collector.collect_capacity(list(active_databases))
        if not databases_data:
            return _build_failure("未采集到任何数据库大小数据", {"inventory": inventory_result})

        database_count = len(databases_data)
        total_size_mb = sum(db.get("size_mb", 0) for db in databases_data)

        try:
            saved_count = collector.save_database_stats(databases_data)
        except CAPACITY_TASK_EXCEPTIONS as save_error:
            logger.exception(
                "保存实例容量数据失败",
                module="capacity_sync",
                instance_id=instance.id,
                instance_name=instance.name,
                error=str(save_error),
            )
            return _build_failure(
                f"采集成功但保存数据失败: {save_error}",
                {"error": str(save_error), "inventory": inventory_result},
            )

        instance_stat_updated = collector.update_instance_total_size()
        if not instance_stat_updated:
            logger.warning(
                "实例容量统计更新失败",
                module="capacity_sync",
                instance_id=instance.id,
                instance_name=instance.name,
            )

        return _build_success(
            f"成功采集并保存 {database_count} 个数据库的容量信息",
            {
                "databases": databases_data,
                "database_count": database_count,
                "total_size_mb": total_size_mb,
                "saved_count": saved_count,
                "instance_stat_updated": instance_stat_updated,
                "inventory": inventory_result,
            },
        )

    @staticmethod
    def _refresh_instance_aggregations(instance_id: int, logger: structlog.BoundLogger) -> None:
        try:
            aggregation_service = AggregationService()
            aggregation_service.calculate_daily_database_aggregations_for_instance(instance_id)
            aggregation_service.calculate_daily_aggregations_for_instance(instance_id)
        except CAPACITY_TASK_EXCEPTIONS as agg_exc:  # pragma: no cover
            logger.exception(
                "实例容量聚合刷新失败",
                module="capacity_sync",
                instance_id=instance_id,
                error=str(agg_exc),
            )

    def collect_instance_database_sizes(
        self,
        *,
        instance_id: int,
        logger: structlog.BoundLogger,
    ) -> dict[str, object]:
        instance = self._load_active_instance(instance_id)
        collector = CapacitySyncCoordinator(instance)
        if not collector.connect():
            return _build_failure(f"无法连接到实例 {instance.name}")

        try:
            inventory_result, active_databases = self._sync_inventory_for_single_instance(
                collector=collector,
                instance=instance,
                logger=logger,
            )

            if not active_databases:
                return _build_success(
                    "未发现活跃数据库,已仅同步数据库列表",
                    {
                        "databases": [],
                        "database_count": 0,
                        "total_size_mb": 0,
                        "saved_count": 0,
                        "instance_stat_updated": False,
                        "inventory": inventory_result,
                    },
                )

            result = self._save_instance_sizes(
                collector=collector,
                instance=instance,
                inventory_result=inventory_result,
                active_databases=active_databases,
                logger=logger,
            )
            if bool(result.get("success")):
                self._refresh_instance_aggregations(instance.id, logger)
            return result
        finally:
            collector.disconnect()
