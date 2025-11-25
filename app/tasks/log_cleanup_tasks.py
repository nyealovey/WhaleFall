"""
日志与临时文件清理任务
"""

import os
from datetime import timedelta

from app import create_app, db
from app.models.unified_log import UnifiedLog
from app.utils.structlog_config import get_task_logger
from app.utils.time_utils import time_utils


def cleanup_old_logs() -> None:
    """清理旧日志任务 - 清理30天前的日志和临时文件。

    删除 30 天前的统一日志、同步会话记录、同步实例记录，
    并清理临时文件目录中的过期文件。

    Returns:
        None

    Raises:
        Exception: 当清理任务执行失败时抛出。
    """
    task_logger = get_task_logger()

    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            cutoff_date = time_utils.now() - timedelta(days=30)
            deleted_logs = UnifiedLog.query.filter(UnifiedLog.timestamp < cutoff_date).delete()

            cleaned_files = _cleanup_temp_files()

            from app.models.sync_instance_record import SyncInstanceRecord
            from app.models.sync_session import SyncSession

            deleted_sync_sessions = SyncSession.query.filter(SyncSession.created_at < cutoff_date).delete()
            deleted_sync_records = SyncInstanceRecord.query.filter(SyncInstanceRecord.created_at < cutoff_date).delete()

            deleted_account_sync_data = 0
            deleted_change_logs = 0

            db.session.commit()

            task_logger.info(
                "定时任务清理完成",
                module="task",
                task_name="cleanup_old_logs",
                deleted_logs=deleted_logs,
                cleaned_files=cleaned_files,
                deleted_sync_sessions=deleted_sync_sessions,
                deleted_sync_records=deleted_sync_records,
                deleted_account_sync_data=deleted_account_sync_data,
                deleted_change_logs=deleted_change_logs,
            )

        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            task_logger.error(
                "定时任务清理失败",
                module="task",
                task_name="cleanup_old_logs",
                error=str(exc),
                exc_info=True,
            )
            raise


def _cleanup_temp_files() -> int:
    """清理临时文件。

    扫描日志目录和导出目录，删除 .tmp、.temp、.log.old 等临时文件。

    Returns:
        清理的文件数量。
    """
    cleaned_count = 0

    try:
        log_dir = os.path.join(os.getcwd(), "userdata", "log")
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                if filename.endswith((".tmp", ".temp", ".log.old")):
                    file_path = os.path.join(log_dir, filename)
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except OSError:
                        pass

        export_dir = os.path.join(os.getcwd(), "userdata", "exports")
        if os.path.exists(export_dir):
            for filename in os.listdir(export_dir):
                if filename.endswith((".tmp", ".temp")):
                    file_path = os.path.join(export_dir, filename)
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except OSError:
                        pass

    except Exception as exc:  # noqa: BLE001
        get_task_logger().warning(f"清理临时文件时出错: {exc}")

    return cleaned_count
