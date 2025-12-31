"""数据库大小采集定时任务.

负责每日自动采集所有数据库实例的大小信息.
"""

from dataclasses import dataclass
from typing import Any, cast

import structlog
from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.errors import AppError
from app.models.instance import Instance
from app.models.instance_size_stat import InstanceSizeStat
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.services.aggregation.aggregation_service import AggregationService
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.services.database_sync import CapacitySyncCoordinator
from app.services.sync_session_service import SyncItemStats, sync_session_service
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils

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
    """构造失败响应."""
    base: dict[str, object] = {"success": False, "message": message}
    if extra:
        base.update(extra)
    return base


def _build_success(message: str, payload: dict[str, object]) -> dict[str, object]:
    """构造成功响应."""
    base: dict[str, object] = {"success": True, "message": message}
    base.update(payload)
    return base


def _to_int(value: object) -> int:
    """将未知类型安全转换为整数,失败时返回 0."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _no_active_instances_result() -> dict[str, object]:
    return {
        "success": True,
        "message": "没有活跃的数据库实例需要同步",
        "instances_processed": 0,
        "total_size_mb": 0,
    }


def _create_capacity_session(active_instances: list[Instance]) -> tuple[SyncSession, list[SyncInstanceRecord]]:
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


def _sync_inventory_for_instance(
    collector: CapacitySyncCoordinator,
    record: SyncInstanceRecord,
    session: SyncSession,
    instance: Instance,
    sync_logger: structlog.BoundLogger,
) -> tuple[dict[str, object], bool]:
    """同步库存,更新记录并返回 inventory 结果和是否跳过后续."""
    sync_logger.info(
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
        sync_logger.warning(
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


def _collect_and_save_capacity(
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


def _load_active_instance(instance_id: int) -> Instance:
    """加载并校验实例是否可用."""
    instance = Instance.query.get(instance_id)
    if not instance:
        error_msg = f"实例 {instance_id} 不存在"
        raise AppError(error_msg)
    if not instance.is_active:
        error_msg = f"实例 {instance_id} 未激活"
        raise AppError(error_msg)
    return instance


def _sync_inventory_for_single_instance(
    collector: CapacitySyncCoordinator,
    instance: Instance,
    logger: structlog.BoundLogger,
) -> tuple[dict[str, object], set[str]]:
    """同步单实例库存并返回活跃数据库集合."""
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
        error_msg = f"同步数据库列表失败: {inventory_error}"
        raise AppError(error_msg) from inventory_error

    active_databases = set(inventory_result.get("active_databases", []))
    return inventory_result, active_databases


def _save_instance_sizes(
    collector: CapacitySyncCoordinator,
    instance: Instance,
    inventory_result: dict[str, object],
    active_databases: set[str],
    logger: structlog.BoundLogger,
) -> dict[str, object]:
    """采集并保存实例容量数据."""
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
            {
                "error": str(save_error),
                "inventory": inventory_result,
            },
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


def _refresh_instance_aggregations(instance_id: int, logger: structlog.BoundLogger) -> None:
    """刷新实例相关的日聚合."""
    try:
        aggregation_service = AggregationService()
        aggregation_service.calculate_daily_database_aggregations_for_instance(instance_id)
        aggregation_service.calculate_daily_aggregations_for_instance(instance_id)
    except CAPACITY_TASK_EXCEPTIONS as agg_exc:  # pragma: no cover - 防御性日志
        logger.exception(
            "实例容量聚合刷新失败",
            module="capacity_sync",
            instance_id=instance_id,
            error=str(agg_exc),
        )


def _process_capacity_instance(
    session: SyncSession,
    record: SyncInstanceRecord,
    instance: Instance,
    sync_logger: structlog.BoundLogger,
) -> tuple[dict[str, object], CapacitySyncTotals]:
    """处理单实例容量同步,返回结果及增量统计."""
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

        sync_logger.info(
            "同步数据库列表",
            module="capacity_sync",
            session_id=session.session_id,
            instance_id=instance.id,
            instance_name=instance.name,
        )
        inventory_payload, skip_capacity = _sync_inventory_for_instance(
            collector,
            record,
            session,
            instance,
            sync_logger,
        )
        db.session.commit()
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
        result, success = _collect_and_save_capacity(
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


def _run_capacity_session(
    session: SyncSession,
    active_instances: list[Instance],
    records: list[SyncInstanceRecord],
    sync_logger: structlog.BoundLogger,
) -> tuple[CapacitySyncTotals, list[dict[str, object]]]:
    """执行容量会话的实例循环,返回累计统计与明细."""
    totals = CapacitySyncTotals()
    results: list[dict[str, object]] = []

    for instance, record in zip(active_instances, records, strict=False):
        sync_session_service.start_instance_sync(record.id)
        db.session.commit()
        try:
            payload, delta = _process_capacity_instance(session, record, instance, sync_logger)
        except Exception as exc:  # pragma: no cover - 兜底避免会话卡死
            db.session.rollback()
            error_msg = f"实例同步异常: {exc!s}"
            sync_logger.exception(
                "实例同步异常(未分类)",
                module="capacity_sync",
                session_id=session.session_id,
                instance_id=instance.id,
                instance_name=instance.name,
                error=str(exc),
            )
            sync_session_service.fail_instance_sync(record.id, error_msg)
            db.session.commit()
            payload = {
                "instance_id": instance.id,
                "instance_name": instance.name,
                "success": False,
                "error": str(exc),
            }
            delta = CapacitySyncTotals(total_failed=1)
        else:
            db.session.commit()

        totals.total_synced += delta.total_synced
        totals.total_failed += delta.total_failed
        totals.total_collected_size_mb += delta.total_collected_size_mb
        results.append(payload)

    return totals, results


def collect_database_sizes() -> dict[str, Any]:
    """容量同步定时任务.

    每天凌晨3点执行,同步所有活跃实例的数据库容量信息.
    创建同步会话,遍历所有活跃实例,采集数据库大小并保存.

    Returns:
        包含同步结果的字典,包括成功/失败实例数、总容量等信息.

    """
    # 创建Flask应用上下文,确保数据库操作正常
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        active_instances: list[Instance] = []
        session_obj: SyncSession | None = None
        records: list[SyncInstanceRecord] = []

        try:
            sync_logger.info("开始容量同步任务", module="capacity_sync")

            active_instances = Instance.query.filter_by(is_active=True).all()
            if not active_instances:
                sync_logger.warning("没有找到活跃的数据库实例", module="capacity_sync")
                return _no_active_instances_result()

            sync_logger.info(
                "找到活跃实例,开始容量同步",
                module="capacity_sync",
                instance_count=len(active_instances),
            )

            session_obj, records = _create_capacity_session(active_instances)
            db.session.commit()
            totals, results = _run_capacity_session(session_obj, active_instances, records, sync_logger)

            session_obj.successful_instances = totals.total_synced
            session_obj.failed_instances = totals.total_failed
            session_obj.status = "completed" if totals.total_failed == 0 else "failed"
            session_obj.completed_at = time_utils.now()
            db.session.commit()

            message = f"容量同步完成: 成功 {totals.total_synced} 个,失败 {totals.total_failed} 个"
            result = {
                "success": totals.total_failed == 0,
                "message": message,
                "instances_processed": totals.total_synced,
                "total_size_mb": totals.total_collected_size_mb,
                "session_id": session_obj.session_id,
                "details": results,
            }

            sync_logger.info(
                "容量同步任务完成",
                module="capacity_sync",
                session_id=session_obj.session_id,
                total_instances=len(active_instances),
                successful_instances=totals.total_synced,
                failed_instances=totals.total_failed,
                total_size_mb=totals.total_collected_size_mb,
            )

        except CAPACITY_TASK_EXCEPTIONS as exc:
            sync_logger.exception(
                "容量同步任务执行失败",
                module="capacity_sync",
                error=str(exc),
            )

            if session_obj is not None:
                session_obj.status = "failed"
                session_obj.completed_at = time_utils.now()
                session_obj.failed_instances = len(active_instances)
                db.session.commit()

            return {
                "success": False,
                "message": f"容量同步任务执行失败: {exc!s}",
                "error": str(exc),
            }
        except Exception as exc:  # pragma: no cover - 兜底避免会话卡死
            sync_logger.exception(
                "容量同步任务执行失败(未分类)",
                module="capacity_sync",
                error=str(exc),
            )

            if session_obj is not None:
                session_obj.status = "failed"
                session_obj.completed_at = time_utils.now()
                session_obj.failed_instances = len(active_instances)
                db.session.commit()

            return {
                "success": False,
                "message": f"容量同步任务执行失败: {exc!s}",
                "error": str(exc),
            }
        else:
            return result


def collect_specific_instance_database_sizes(instance_id: int) -> dict[str, Any]:
    """采集指定实例的数据库大小信息.

    连接到指定实例,同步数据库清单,采集容量数据并保存.
    完成后自动触发当日聚合计算.

    Args:
        instance_id: 实例ID.

    Returns:
        采集结果字典,包含成功状态、数据库数量、总容量等信息.

    """
    # 创建Flask应用上下文
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        sync_logger.info(
            "开始采集实例数据库大小",
            module="capacity_sync",
            instance_id=instance_id,
        )
        try:
            instance = _load_active_instance(instance_id)
            collector = CapacitySyncCoordinator(instance)
            if not collector.connect():
                return _build_failure(f"无法连接到实例 {instance.name}")

            try:
                inventory_result, active_databases = _sync_inventory_for_single_instance(
                    collector,
                    instance,
                    sync_logger,
                )
                db.session.commit()

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

                result = _save_instance_sizes(
                    collector,
                    instance,
                    inventory_result,
                    active_databases,
                    sync_logger,
                )
                if result["success"]:
                    db.session.commit()
                    _refresh_instance_aggregations(instance.id, sync_logger)
                    db.session.commit()
                return result
            finally:
                collector.disconnect()
        except CAPACITY_TASK_EXCEPTIONS as exc:
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
    """采集指定类型数据库的大小信息.

    Args:
        db_type: 数据库类型(mysql/sqlserver/postgresql/oracle).

    Returns:
        Dict[str, Any]: 采集结果及统计.

    """
    # 创建Flask应用上下文
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        try:
            sync_logger.info(
                "开始按照数据库类型采集容量",
                module="capacity_sync",
                db_type=db_type,
            )

            # 获取指定类型的活跃实例
            instances = Instance.query.filter_by(
                db_type=db_type,
                is_active=True,
            ).all()

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
            errors = []

            for instance in instances:
                try:
                    result = collect_specific_instance_database_sizes(instance.id)
                    if result["success"]:
                        total_processed += 1
                        total_size_mb += result.get("total_size_mb", 0)
                    else:
                        errors.append(f"实例 {instance.name}: {result['message']}")
                except CAPACITY_TASK_EXCEPTIONS as exc:
                    errors.append(f"实例 {instance.name}: {exc!s}")

        except CAPACITY_TASK_EXCEPTIONS as exc:
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


def get_collection_status() -> dict[str, Any]:
    """获取数据库大小采集状态.

    Returns:
        Dict[str, Any]: 采集状态信息

    """
    # 创建Flask应用上下文
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            # 统计采集数据
            total_stats = InstanceSizeStat.query.count()
            recent_stats = InstanceSizeStat.query.filter(
                InstanceSizeStat.created_at >= time_utils.now_china().date(),
            ).count()

            # 获取最新采集时间
            latest_stat = InstanceSizeStat.query.order_by(
                InstanceSizeStat.created_at.desc(),
            ).first()

            latest_time = latest_stat.created_at if latest_stat else None

            return {
                "success": True,
                "total_records": total_stats,
                "today_records": recent_stats,
                "latest_collection": latest_time.isoformat() if latest_time else None,
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
    """验证数据库大小采集配置.

    Returns:
        Dict[str, Any]: 配置验证结果

    """
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
