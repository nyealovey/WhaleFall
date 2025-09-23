"""
鲸落定时任务定义
"""

import os
from datetime import datetime, timedelta

from app import create_app, db
from app.models.account_change_log import AccountChangeLog
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.unified_log import UnifiedLog
from app.models.user import User
from app.models.instance import Instance
from app.services.account_sync_service import account_sync_service
from app.services.sync_session_service import sync_session_service
from app.utils.structlog_config import get_sync_logger, get_task_logger
from app.utils.time_utils import time_utils


def cleanup_old_logs() -> None:
    """清理旧日志任务 - 清理30天前的日志和临时文件"""
    task_logger = get_task_logger()

    app = create_app()
    with app.app_context():
        try:
            # 删除30天前的日志
            cutoff_date = time_utils.now() - timedelta(days=30)
            deleted_logs = UnifiedLog.query.filter(UnifiedLog.timestamp < cutoff_date).delete()

            # 清理临时文件
            cleaned_files = _cleanup_temp_files()

            # 清理旧的同步记录（保留最近30天） - 使用新的同步会话模型
            from app.models.sync_instance_record import SyncInstanceRecord
            from app.models.sync_session import SyncSession

            deleted_sync_sessions = SyncSession.query.filter(SyncSession.created_at < cutoff_date).delete()
            deleted_sync_records = SyncInstanceRecord.query.filter(SyncInstanceRecord.created_at < cutoff_date).delete()

            # 注意：不清理账户同步数据表和账户变更日志，保留所有历史记录用于审计
            deleted_account_sync_data = 0
            deleted_change_logs = 0

            db.session.commit()

            # 记录操作日志
            task_logger.info(
                "定时任务清理完成",
                module="task",
                operation_type="TASK_CLEANUP_COMPLETE",
                deleted_logs=deleted_logs,
                deleted_sync_sessions=deleted_sync_sessions,
                deleted_sync_records=deleted_sync_records,
                deleted_account_sync_data=deleted_account_sync_data,
                deleted_change_logs=deleted_change_logs,
                cleaned_temp_files=cleaned_files,
                cutoff_date=cutoff_date.isoformat(),
                note="账户变更日志已保留用于审计",
            )

            task_logger.info(
                "定时任务清理完成",
                module="scheduler",
                deleted_logs=deleted_logs,
                deleted_sync_sessions=deleted_sync_sessions,
                deleted_sync_records=deleted_sync_records,
                deleted_account_sync_data=deleted_account_sync_data,
                deleted_change_logs=deleted_change_logs,
                cleaned_temp_files=cleaned_files,
                note="账户变更日志已保留用于审计",
            )

            return f"清理完成：{deleted_logs} 条日志，{deleted_sync_sessions} 条同步会话，{deleted_sync_records} 条同步记录，{deleted_account_sync_data} 条账户同步数据，{cleaned_files} 个临时文件（账户变更日志已保留用于审计）"

        except Exception as e:
            task_logger.error("定时任务清理失败", module="scheduler", exception=e)
            db.session.rollback()
            return f"清理失败: {str(e)}"


def _cleanup_temp_files():
    """清理临时文件"""
    task_logger = get_task_logger()

    try:
        temp_dirs = [
            "userdata/temp",
            "userdata/exports",
            "userdata/logs",
            "userdata/dynamic_tasks",
        ]

        cleaned_files = 0
        cutoff_time = datetime.now() - timedelta(days=7)  # 清理7天前的临时文件

        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path):
                        # 删除7天前的临时文件
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_mtime < cutoff_time:
                            os.remove(file_path)
                            cleaned_files += 1
                            task_logger.info("删除临时文件", module="task", file_path=file_path)

        return cleaned_files

    except Exception as e:
        task_logger.error("清理临时文件失败", module="task", exception=e)
        return 0


def sync_accounts(**kwargs):
    """
    APScheduler 定时任务 - 同步所有活跃实例的账户
    """
    app = create_app()
    with app.app_context():
        task_logger = get_sync_logger()
        task_logger.info("开始执行定时账户同步任务...")
        session = None
        try:
            # 1. 获取所有活跃实例（使用Instance.get_active_instances()方法）
            instances = Instance.get_active_instances()
            total_instances = len(instances)

            # 2. 创建同步会话并立即设置总实例数
            session = sync_session_service.create_session(
                sync_type="scheduled_task", sync_category="account"
            )
            session.total_instances = total_instances
            
            # 如果没有实例，直接将会话标记为完成
            if total_instances == 0:
                task_logger.info("没有找到需要同步的活跃实例，任务结束。")
                session.status = "completed"
                session.completed_at = time_utils.now()
                db.session.commit()
                return

            db.session.commit()
            
            # 3. 添加实例记录
            records = sync_session_service.add_instance_records(
                session.session_id, [instance.id for instance in instances]
            )
            if not records:
                task_logger.error("为所有实例创建同步记录失败。")
                session.status = "failed"
                session.completed_at = time_utils.now()
                db.session.commit()
                return

            # 4. 遍历实例并触发同步
            task_logger.info(f"共找到 {total_instances} 个活跃实例，开始逐个同步。")

            for instance in instances:
                task_logger.info(f"开始同步实例: {instance.name} (ID: {instance.id})")
                try:
                    # 使用带有会话的同步服务，它将处理每个实例的状态更新
                    account_sync_service.sync_instance_with_session(
                        instance_id=instance.id, session_id=session.session_id
                    )
                except Exception as e:
                    task_logger.error(f"触发实例同步时发生意外错误: {instance.name}", error=str(e))
                    # 尝试将此实例标记为失败
                    record = sync_session_service.get_record_by_instance_and_session(instance.id, session.session_id)
                    if record:
                        sync_session_service.fail_instance_sync(record.id, str(e))

            # 5. 任务结束
            # 会话的最终状态将由最后一个完成的实例同步操作在 `sync_session_service` 中更新
            task_logger.info(
                "所有实例同步任务已触发。请在同步会话页面查看最终结果。"
            )

        except Exception as e:
            task_logger.error(f"执行定时账户同步任务时发生严重错误: {str(e)}")
            if session:
                session.status = "failed"
                session.completed_at = time_utils.now()
                db.session.commit()


def health_check() -> None:
    """健康检查任务"""
    task_logger = get_task_logger()

    app = create_app()
    with app.app_context():
        try:
            # 检查数据库连接
            db.session.execute("SELECT 1")

            # 检查关键表
            user_count = User.query.count()
            account_count = CurrentAccountSyncData.query.filter_by(is_deleted=False).count()
            log_count = UnifiedLog.query.count()
            sync_data_count = CurrentAccountSyncData.query.count()
            change_log_count = AccountChangeLog.query.count()

            health_data = {
                "timestamp": datetime.now().isoformat(),
                "status": "healthy",
                "database": "connected",
                "users": user_count,
                "accounts": account_count,
                "logs": log_count,
                "sync_data": sync_data_count,
                "change_logs": change_log_count,
            }

            task_logger.info("健康检查完成", module="task", health_data=health_data)
            return health_data

        except Exception as e:
            task_logger.error("健康检查失败", module="task", exception=e)
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "unhealthy",
                "error": str(e),
            }


def cleanup_temp_files() -> None:
    """清理临时文件任务"""
    task_logger = get_task_logger()

    app = create_app()
    with app.app_context():
        try:
            temp_dirs = ["userdata/temp", "userdata/exports", "userdata/logs"]

            cleaned_files = 0
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for file in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, file)
                        if os.path.isfile(file_path):
                            # 删除7天前的临时文件
                            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
                            if file_age.days > 7:
                                os.remove(file_path)
                                cleaned_files += 1

            task_logger.info("临时文件清理完成", module="task", cleaned_files=cleaned_files)
            return f"清理了 {cleaned_files} 个临时文件"

        except Exception as e:
            task_logger.error("清理临时文件失败", module="task", exception=e)
            return f"清理临时文件失败: {str(e)}"
