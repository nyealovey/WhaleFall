"""分区管理定时任务

负责自动创建、清理和监控数据库大小统计表的分区.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.exc import SQLAlchemyError

from app.config import Config
from app.errors import AppError, DatabaseError
from app.services.partition_management_service import PartitionManagementService
from app.services.statistics.partition_statistics_service import PartitionStatisticsService
from app.utils.response_utils import unified_error_response, unified_success_response
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import time_utils

MODULE = "partition_tasks"
PARTITION_TASK_EXCEPTIONS: tuple[type[BaseException], ...] = (
    AppError,
    DatabaseError,
    SQLAlchemyError,
    RuntimeError,
    LookupError,
    ValueError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def _as_app_error(error: Exception) -> AppError:
    """确保返回 AppError 实例,便于统一错误上下文.

    Args:
        error: 捕获到的任意异常.

    Returns:
        AppError: 若已是 AppError 则原样返回,否则包装为 DatabaseError.

    """
    return error if isinstance(error, AppError) else DatabaseError(message=str(error))


def create_database_size_partitions() -> dict[str, object]:
    """创建数据库大小统计表的分区.

    每天凌晨 2 点执行,创建未来 3 个月的分区,确保数据有足够的存储空间.

    Returns:
        包含分区创建结果的字典,包括处理的月份数和创建的分区列表.

    """
    management_service = PartitionManagementService()
    try:
        months_ahead = 3
        log_info("开始创建数据库大小统计表分区", module=MODULE, months_ahead=months_ahead)
        result = management_service.create_future_partitions(months_ahead=months_ahead)
        log_info(
            "分区创建任务完成",
            module=MODULE,
            processed_months=result.get("months_processed"),
        )
        payload, _ = unified_success_response(
            data=result,
            message="分区创建任务已完成",
        )
    except PARTITION_TASK_EXCEPTIONS as exc:
        app_error = _as_app_error(exc)
        log_error("分区创建任务失败", module=MODULE, exception=exc)
        payload, _ = unified_error_response(app_error)
        return payload
    else:
        return payload


def cleanup_database_size_partitions() -> dict[str, object]:
    """清理数据库大小统计表的旧分区.

    每天凌晨 3 点执行,清理保留期外的分区,释放存储空间.
    保留期由配置项 DATABASE_SIZE_RETENTION_MONTHS 控制,默认 12 个月.

    Returns:
        包含清理结果的字典,包括截止日期和删除的分区列表.

    """
    service = PartitionManagementService()
    try:
        retention_months = getattr(Config, "DATABASE_SIZE_RETENTION_MONTHS", 12)
        log_info(
            "开始清理旧分区",
            module=MODULE,
            retention_months=retention_months,
        )
        result = service.cleanup_old_partitions(retention_months=retention_months)
        log_info(
            "旧分区清理完成",
            module=MODULE,
            cutoff_date=result.get("cutoff_date"),
            dropped=len(result.get("dropped", [])),
        )
        payload, _ = unified_success_response(
            data=result,
            message="旧分区清理任务已完成",
        )
    except PARTITION_TASK_EXCEPTIONS as exc:
        app_error = _as_app_error(exc)
        log_error("旧分区清理任务失败", module=MODULE, exception=exc)
        payload, _ = unified_error_response(app_error)
        return payload
    else:
        return payload


def monitor_partition_health() -> dict[str, object]:
    """监控分区健康状态.

    每小时执行一次,检查分区状态和容量.如果发现下个月的分区不存在,
    会自动尝试创建.

    Returns:
        包含分区健康状态的字典,包括分区数量、总大小、记录数等信息.

    """
    management_service = PartitionManagementService()
    stats_service = PartitionStatisticsService()
    try:
        log_info("开始监控分区健康状态", module=MODULE)
        partition_info = stats_service.get_partition_info()
        stats = stats_service.get_partition_statistics()

        current_date = time_utils.now().date()
        next_month = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
        next_partition_name = f"database_size_stats_{time_utils.format_china_time(next_month, '%Y_%m')}"
        partitions = partition_info["partitions"]
        exists = any(part["name"] == next_partition_name for part in partitions)

        auto_creation: dict[str, object] | None = None
        if not exists:
            log_warning(
                "下个月分区不存在,尝试自动创建",
                module=MODULE,
                partition_name=next_partition_name,
            )
            try:
                creation_result = management_service.create_partition(next_month)
                auto_creation = {"created": True, "result": creation_result}
                log_info(
                    "自动创建下个月分区成功",
                    module=MODULE,
                    partition_name=next_partition_name,
                )
            except DatabaseError as exc:
                auto_creation = {"created": False, "message": exc.message, "extra": getattr(exc, "extra", {})}
                log_warning(
                    "自动创建下个月分区失败",
                    module=MODULE,
                    partition_name=next_partition_name,
                    error=exc.message,
                )

        payload, _ = unified_success_response(
            data={
                "partition_count": stats["total_partitions"],
                "total_size": stats["total_size"],
                "total_records": stats["total_records"],
                "auto_creation": auto_creation,
            },
            message="分区健康监控完成",
        )
    except PARTITION_TASK_EXCEPTIONS as exc:
        app_error = _as_app_error(exc)
        log_error("分区健康监控任务失败", module=MODULE, exception=exc)
        payload, _ = unified_error_response(app_error)
        return payload
    else:
        return payload


def get_partition_management_status() -> dict[str, object]:
    """获取分区管理状态,用于 API 接口和监控页面.

    Returns:
        字典包含健康状态、分区数量与缺失分区列表.

    Raises:
        AppError: 当查询分区信息失败时抛出.

    """
    stats_service = PartitionStatisticsService()
    try:
        partition_info = stats_service.get_partition_info()
        stats = stats_service.get_partition_statistics()

        partitions = partition_info["partitions"]
        current_date = time_utils.now().date()

        required_partitions: list[str] = []
        for offset in range(3):
            month_date = (current_date.replace(day=1) + timedelta(days=offset * 32)).replace(day=1)
            required_partitions.append(f"database_size_stats_{time_utils.format_china_time(month_date, '%Y_%m')}")

        existing_partitions = {partition["name"] for partition in partitions}
        missing_partitions = [name for name in required_partitions if name not in existing_partitions]

        status = "healthy" if not missing_partitions else "warning"
        return {
            "status": status,
            "total_partitions": stats["total_partitions"],
            "total_size": stats["total_size"],
            "total_records": stats["total_records"],
            "missing_partitions": missing_partitions,
            "partitions": partitions,
        }
    except PARTITION_TASK_EXCEPTIONS as exc:
        app_error = _as_app_error(exc)
        log_error("获取分区管理状态失败", module=MODULE, exception=exc)
        raise app_error from exc
