"""分区管理定时任务.

负责清理数据库大小统计表的历史分区.
"""

from __future__ import annotations

from contextlib import suppress

from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.core.exceptions import AppError, DatabaseError
from app.services.partition_management_service import PartitionManagementService
from app.core.types.structures import JsonDict
from app.utils.response_utils import unified_error_response, unified_success_response
from app.utils.structlog_config import log_error, log_info

MODULE = "partition_tasks"
PARTITION_TASK_EXCEPTIONS: tuple[type[Exception], ...] = (
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


def cleanup_database_size_partitions() -> JsonDict:
    """清理数据库大小统计表的旧分区.

    每天凌晨 3 点执行,清理保留期外的分区,释放存储空间.
    保留期由配置项 DATABASE_SIZE_RETENTION_MONTHS 控制,默认 12 个月.

    Returns:
        包含清理结果的字典,包括截止日期和删除的分区列表.

    """
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        service = PartitionManagementService()
        try:
            retention_months = int(app.config.get("DATABASE_SIZE_RETENTION_MONTHS", 12))
            log_info(
                "开始清理旧分区",
                module=MODULE,
                retention_months=retention_months,
            )
            result = service.cleanup_old_partitions(retention_months=retention_months)
            db.session.commit()
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
            with suppress(Exception):
                db.session.rollback()
            app_error = _as_app_error(exc)
            log_error("旧分区清理任务失败", module=MODULE, exception=exc)
            payload, _ = unified_error_response(app_error)
            return payload
        else:
            return payload
