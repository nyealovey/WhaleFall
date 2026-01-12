"""日志与临时文件清理任务."""

from contextlib import suppress
from datetime import timedelta
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.services.logging.log_cleanup_service import LogCleanupService
from app.utils.structlog_config import get_task_logger
from app.utils.time_utils import time_utils

LOG_CLEANUP_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SQLAlchemyError,
    OSError,
    RuntimeError,
    ValueError,
)


def cleanup_old_logs() -> None:
    """清理旧日志任务 - 清理30天前的日志和临时文件.

    删除 30 天前的统一日志、同步会话记录、同步实例记录,
    并清理临时文件目录中的过期文件.

    Returns:
        None

    Raises:
        Exception: 当清理任务执行失败时抛出.

    """
    task_logger = get_task_logger()

    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            cutoff_date = time_utils.now() - timedelta(days=30)
            cleanup_service = LogCleanupService()
            outcome = cleanup_service.cleanup_before(cutoff_date)

            cleaned_files = _cleanup_temp_files()

            deleted_accounts_sync_data = 0
            deleted_change_logs = 0

            db.session.commit()

            task_logger.info(
                "定时任务清理完成",
                module="task",
                task_name="cleanup_old_logs",
                deleted_logs=outcome.deleted_logs,
                cleaned_files=cleaned_files,
                deleted_sync_sessions=outcome.deleted_sync_sessions,
                deleted_sync_records=outcome.deleted_sync_records,
                deleted_accounts_sync_data=deleted_accounts_sync_data,
                deleted_change_logs=deleted_change_logs,
            )

        except LOG_CLEANUP_EXCEPTIONS as exc:
            db.session.rollback()
            task_logger.exception(
                "定时任务清理失败",
                module="task",
                task_name="cleanup_old_logs",
                error=str(exc),
            )
            raise


def _cleanup_temp_files() -> int:
    """清理临时文件.

    扫描日志目录和导出目录,删除 .tmp、.temp、.log.old 等临时文件.

    Returns:
        清理的文件数量.

    """
    cleaned_count = 0

    try:
        base_dir = Path.cwd() / "userdata"
        directories = [
            (base_dir / "log", (".tmp", ".temp", ".log.old")),
            (base_dir / "exports", (".tmp", ".temp")),
        ]
        for directory, suffixes in directories:
            if not directory.exists():
                continue
            for entry in directory.iterdir():
                if not entry.is_file():
                    continue
                if any(entry.name.endswith(suffix) for suffix in suffixes):
                    with suppress(OSError):
                        entry.unlink()
                        cleaned_count += 1

    except OSError as exc:
        get_task_logger().warning(f"清理临时文件时出错: {exc}")

    return cleaned_count
