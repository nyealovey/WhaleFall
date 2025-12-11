"""数据库大小采集定时任务
负责每日自动采集所有数据库实例的大小信息.
"""

from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.config import Config
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.errors import AppError
from app.models.instance import Instance
from app.models.instance_size_stat import InstanceSizeStat
from app.services.aggregation.aggregation_service import AggregationService
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.services.database_sync import DatabaseSizeCollectorService
from app.services.sync_session_service import sync_session_service
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils

CAPACITY_TASK_EXCEPTIONS: tuple[type[BaseException], ...] = (
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

        try:
            sync_logger.info("开始容量同步任务", module="capacity_sync")

            # 获取所有活跃的实例
            active_instances = Instance.query.filter_by(is_active=True).all()

            if not active_instances:
                sync_logger.warning("没有找到活跃的数据库实例", module="capacity_sync")
                return {
                    "success": True,
                    "message": "没有活跃的数据库实例需要同步",
                    "instances_processed": 0,
                    "total_size_mb": 0,
                }

            sync_logger.info(
                "找到活跃实例,开始容量同步",
                module="capacity_sync",
                instance_count=len(active_instances),
            )

            # 创建同步会话
            session = sync_session_service.create_session(
                sync_type=SyncOperationType.SCHEDULED_TASK.value,
                sync_category=SyncCategory.CAPACITY.value,
                created_by=None,  # 定时任务没有创建者
            )

            sync_logger.info(
                "创建容量同步会话",
                module="capacity_sync",
                session_id=session.session_id,
                instance_count=len(active_instances),
            )

            # 添加实例记录
            instance_ids = [inst.id for inst in active_instances]
            records = sync_session_service.add_instance_records(
                session.session_id, instance_ids, sync_category=SyncCategory.CAPACITY.value
            )
            session.total_instances = len(active_instances)

            total_synced = 0
            total_failed = 0
            total_collected_size_mb = 0
            results = []

            for i, instance in enumerate(active_instances):
                # 找到对应的记录
                record = records[i] if i < len(records) else None
                if not record:
                    continue

                try:
                    # 开始实例同步
                    sync_session_service.start_instance_sync(record.id)

                    sync_logger.info(
                        "开始同步实例",
                        module="capacity_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        instance_name=instance.name,
                    )

                    # 调用数据库大小采集服务
                    collector = DatabaseSizeCollectorService(instance)

                    try:
                        # 建立连接
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
                            total_failed += 1
                            results.append(
                                {
                                    "instance_id": instance.id,
                                    "instance_name": instance.name,
                                    "success": False,
                                    "error": error_msg,
                                }
                            )
                            continue

                        try:
                            inventory_result = collector.synchronize_database_inventory()
                        except CAPACITY_TASK_EXCEPTIONS as inventory_error:
                            error_msg = f"同步数据库列表失败: {inventory_error}"
                            sync_logger.exception(
                                "同步数据库列表失败",
                                module="capacity_sync",
                                session_id=session.session_id,
                                instance_id=instance.id,
                                instance_name=instance.name,
                                error=str(inventory_error),
                            )
                            sync_session_service.fail_instance_sync(record.id, error_msg)
                            total_failed += 1
                            results.append(
                                {
                                    "instance_id": instance.id,
                                    "instance_name": instance.name,
                                    "success": False,
                                    "error": error_msg,
                                }
                            )
                            continue

                        active_databases = set(inventory_result.get("active_databases", []))

                        if not active_databases:
                            sync_session_service.complete_instance_sync(
                                record.id,
                                items_synced=0,
                                items_created=inventory_result.get("created", 0),
                                items_updated=inventory_result.get("refreshed", 0)
                                + inventory_result.get("reactivated", 0),
                                items_deleted=inventory_result.get("deactivated", 0),
                                sync_details={
                                    "total_size_mb": 0,
                                    "database_count": 0,
                                    "saved_count": 0,
                                    "databases": [],
                                    "inventory": inventory_result,
                                },
                            )

                            total_synced += 1
                            results.append(
                                {
                                    "instance_id": instance.id,
                                    "instance_name": instance.name,
                                    "success": True,
                                    "size_mb": 0,
                                    "database_count": 0,
                                    "saved_count": 0,
                                    "databases": [],
                                    "inventory": inventory_result,
                                    "message": "未发现活跃数据库,已仅同步数据库列表",
                                }
                            )
                            continue

                        # 采集数据库大小
                        try:
                            databases_data = collector.collect_database_sizes(active_databases)
                        except CAPACITY_TASK_EXCEPTIONS as exc:
                            error_msg = f"采集数据库大小失败: {exc!s}"
                            sync_logger.exception(
                                "采集数据库大小失败",
                                module="capacity_sync",
                                session_id=session.session_id,
                                instance_id=instance.id,
                                instance_name=instance.name,
                                error=str(exc),
                            )
                            sync_session_service.fail_instance_sync(record.id, error_msg)
                            total_failed += 1
                            results.append(
                                {
                                    "instance_id": instance.id,
                                    "instance_name": instance.name,
                                    "success": False,
                                    "error": error_msg,
                                }
                            )
                            continue

                        if not databases_data:
                            error_msg = "未采集到任何数据库大小数据"
                            sync_logger.error(
                                "实例容量同步失败",
                                module="capacity_sync",
                                session_id=session.session_id,
                                instance_id=instance.id,
                                instance_name=instance.name,
                                error=error_msg,
                            )
                            sync_session_service.fail_instance_sync(record.id, error_msg)
                            total_failed += 1
                            results.append(
                                {
                                    "instance_id": instance.id,
                                    "instance_name": instance.name,
                                    "success": False,
                                    "error": error_msg,
                                }
                            )
                            continue

                        # 计算总大小和数据库数量
                        database_count = len(databases_data)
                        instance_total_size_mb = sum(db.get("size_mb", 0) for db in databases_data)

                        # 保存数据库大小数据到数据库
                        saved_count = collector.save_collected_data(databases_data)

                        # 更新实例大小统计
                        collector.update_instance_total_size()

                        # 更新同步记录 - 容量同步使用数据库数量作为同步数量
                        sync_session_service.complete_instance_sync(
                            record.id,
                            items_synced=database_count,
                            items_created=inventory_result.get("created", 0),
                            items_updated=inventory_result.get("refreshed", 0) + inventory_result.get("reactivated", 0),
                            items_deleted=inventory_result.get("deactivated", 0),
                            sync_details={
                                "total_size_mb": instance_total_size_mb,
                                "database_count": database_count,
                                "saved_count": saved_count,
                                "databases": databases_data,
                                "inventory": inventory_result,
                            },
                        )

                        total_synced += 1
                        total_collected_size_mb += instance_total_size_mb

                        sync_logger.info(
                            "实例容量同步成功",
                            module="capacity_sync",
                            session_id=session.session_id,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            size_mb=instance_total_size_mb,
                            database_count=database_count,
                            saved_count=saved_count,
                        )

                        results.append(
                            {
                                "instance_id": instance.id,
                                "instance_name": instance.name,
                                "success": True,
                                "size_mb": instance_total_size_mb,
                                "database_count": database_count,
                                "saved_count": saved_count,
                                "databases": databases_data,
                                "inventory": inventory_result,
                            }
                        )
                    finally:
                        collector.disconnect()

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
                    total_failed += 1
                    results.append(
                        {
                            "instance_id": instance.id,
                            "instance_name": instance.name,
                            "success": False,
                            "error": str(exc),
                        }
                    )

            # 更新会话状态
            session.successful_instances = total_synced
            session.failed_instances = total_failed
            session.status = "completed" if total_failed == 0 else "failed"
            session.completed_at = time_utils.now()
            db.session.commit()

            result = {
                "success": total_failed == 0,
                "message": f"容量同步完成: 成功 {total_synced} 个,失败 {total_failed} 个",
                "instances_processed": total_synced,
                "total_size_mb": total_collected_size_mb,
                "session_id": session.session_id,
                "details": results,
            }

            sync_logger.info(
                "容量同步任务完成",
                module="capacity_sync",
                session_id=session.session_id,
                total_instances=len(active_instances),
                successful_instances=total_synced,
                failed_instances=total_failed,
                total_size_mb=total_collected_size_mb,
            )

            return result

        except CAPACITY_TASK_EXCEPTIONS as exc:
            sync_logger.exception(
                "容量同步任务执行失败",
                module="capacity_sync",
                error=str(exc),
            )

            # 更新会话状态为失败
            if "session" in locals() and session:
                session.status = "failed"
                session.completed_at = time_utils.now()
                session.failed_instances = len(active_instances) if "active_instances" in locals() else 0
                db.session.commit()

            return {
                "success": False,
                "message": f"容量同步任务执行失败: {exc!s}",
                "error": str(exc),
            }


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
        try:
            sync_logger = get_sync_logger()
            sync_logger.info(
                "开始采集实例数据库大小",
                module="capacity_sync",
                instance_id=instance_id,
            )

            # 获取实例信息
            instance = Instance.query.get(instance_id)
            if not instance:
                return {
                    "success": False,
                    "message": f"实例 {instance_id} 不存在",
                }

            if not instance.is_active:
                return {
                    "success": False,
                    "message": f"实例 {instance_id} 未激活",
                }

            # 创建采集服务
            collector = DatabaseSizeCollectorService(instance)

            # 建立连接
            if not collector.connect():
                return {
                    "success": False,
                    "message": f"无法连接到实例 {instance.name}",
                }

            try:
                try:
                    inventory_result = collector.synchronize_database_inventory()
                except CAPACITY_TASK_EXCEPTIONS as inventory_error:
                    sync_logger.exception(
                        "同步数据库列表失败",
                        module="capacity_sync",
                        instance_id=instance.id,
                        instance_name=instance.name,
                        error=str(inventory_error),
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

                # 采集数据库大小
                databases_data = collector.collect_database_sizes(active_databases)

                if databases_data and len(databases_data) > 0:
                    # 计算总大小和数据库数量
                    database_count = len(databases_data)
                    total_size_mb = sum(db.get("size_mb", 0) for db in databases_data)

                    try:
                        saved_count = collector.save_collected_data(databases_data)
                    except CAPACITY_TASK_EXCEPTIONS as save_error:
                        sync_logger.exception(
                            "保存实例容量数据失败",
                            module="capacity_sync",
                            instance_id=instance.id,
                            instance_name=instance.name,
                            error=str(save_error),
                        )
                        return {
                            "success": False,
                            "message": f"采集成功但保存数据失败: {save_error}",
                            "error": str(save_error),
                            "inventory": inventory_result,
                        }

                    instance_stat_updated = collector.update_instance_total_size()
                    if not instance_stat_updated:
                        sync_logger.warning(
                            "实例容量统计更新失败",
                            module="capacity_sync",
                            instance_id=instance.id,
                            instance_name=instance.name,
                        )

                    # 更新统计聚合,确保图表与报表同步最新容量
                    try:
                        aggregation_service = AggregationService()
                        aggregation_service.calculate_daily_database_aggregations_for_instance(instance.id)
                        aggregation_service.calculate_daily_aggregations_for_instance(instance.id)
                    except CAPACITY_TASK_EXCEPTIONS as agg_exc:  # pragma: no cover - 防御性日志
                        sync_logger.exception(
                            "实例容量聚合刷新失败",
                            module="capacity_sync",
                            instance_id=instance.id,
                            instance_name=instance.name,
                            error=str(agg_exc),
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
                return {
                    "success": False,
                    "message": "未采集到任何数据库大小数据",
                    "inventory": inventory_result,
                }
            finally:
                # 确保关闭连接
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

            return {
                "success": True,
                "message": f"{db_type} 类型数据库大小采集完成",
                "instances_processed": total_processed,
                "total_size_mb": total_size_mb,
                "errors": errors,
            }

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
                "collection_enabled": getattr(Config, "COLLECT_DB_SIZE_ENABLED", True),
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
    try:
        # 检查配置项
        config_checks = {
            "COLLECT_DB_SIZE_ENABLED": getattr(Config, "COLLECT_DB_SIZE_ENABLED", True),
            "DB_SIZE_COLLECTION_INTERVAL": getattr(Config, "DB_SIZE_COLLECTION_INTERVAL", 24),
            "DB_SIZE_COLLECTION_TIMEOUT": getattr(Config, "DB_SIZE_COLLECTION_TIMEOUT", 300),
        }

        # 检查服务可用性
        DatabaseSizeCollectorService()

        return {
            "success": True,
            "config": config_checks,
            "service_available": True,
            "message": "配置验证通过",
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
