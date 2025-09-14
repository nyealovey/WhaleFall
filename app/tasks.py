"""
泰摸鱼吧定时任务定义
"""

import os
from datetime import datetime, timedelta

from app import create_app, db
from app.models.account_change_log import AccountChangeLog
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.log import Log
from app.models.user import User
from app.services.account_sync_service import account_sync_service
from app.utils.structlog_config import get_sync_logger, get_task_logger


def cleanup_old_logs():
    """清理旧日志任务 - 清理30天前的日志和临时文件"""
    task_logger = get_task_logger()

    app = create_app()
    with app.app_context():
        try:
            # 删除30天前的日志
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            deleted_logs = Log.query.filter(Log.created_at < cutoff_date).delete()

            # 清理临时文件
            cleaned_files = _cleanup_temp_files()

            # 清理旧的同步记录（保留最近30天） - 使用新的同步会话模型
            from app.models.sync_session import SyncSession

            deleted_sync = SyncSession.query.filter(SyncSession.created_at < cutoff_date).delete()

            # 清理旧的账户变更日志（保留最近30天）
            deleted_change_logs = AccountChangeLog.query.filter(AccountChangeLog.created_at < cutoff_date).delete()

            db.session.commit()

            # 记录操作日志
            task_logger.info(
                "定时任务清理完成",
                module="task",
                operation_type="TASK_CLEANUP_COMPLETE",
                deleted_logs=deleted_logs,
                deleted_sync_records=deleted_sync,
                deleted_change_logs=deleted_change_logs,
                cleaned_temp_files=cleaned_files,
                cutoff_date=cutoff_date.isoformat(),
            )

            task_logger.info(
                "定时任务清理完成",
                module="scheduler",
                deleted_logs=deleted_logs,
                deleted_sync_records=deleted_sync,
                deleted_change_logs=deleted_change_logs,
                cleaned_temp_files=cleaned_files,
            )

            return f"清理完成：{deleted_logs} 条日志，{deleted_sync} 条同步记录，{deleted_change_logs} 条变更日志，{cleaned_files} 个临时文件"

        except Exception as e:
            task_logger.error("定时任务清理失败", module="scheduler", exception=e)
            db.session.rollback()
            return f"清理失败: {e}"


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


def sync_accounts():
    """账户同步任务 - 同步所有数据库实例的账户（使用新的会话管理架构）"""
    from app.models.instance import Instance
    from app.services.sync_session_service import sync_session_service

    sync_logger = get_sync_logger()
    task_logger = get_task_logger()

    app = create_app()
    with app.app_context():
        try:
            # 获取所有活跃的数据库实例
            instances = Instance.query.filter_by(is_active=True).all()
            total_instances = len(instances)

            if not instances:
                sync_logger.warning("没有找到活跃的数据库实例", module="scheduler")
                return "没有找到活跃的数据库实例"

            # 创建同步会话
            session = sync_session_service.create_session(
                sync_type="scheduled",
                sync_category="account",
                created_by=None,  # 定时任务没有用户
            )

            sync_logger.info(
                "定时任务开始同步所有账户",
                module="scheduler",
                session_id=session.session_id,
                total_instances=total_instances,
            )

            # 添加实例记录
            instance_ids = [inst.id for inst in instances]
            records = sync_session_service.add_instance_records(session.session_id, instance_ids)

            success_count = 0
            failed_count = 0
            total_synced_count = 0
            total_added_count = 0
            total_removed_count = 0
            total_modified_count = 0
            results = []

            for instance in instances:
                # 找到对应的记录
                record = next((r for r in records if r.instance_id == instance.id), None)
                if not record:
                    continue

                try:
                    # 开始实例同步
                    sync_session_service.start_instance_sync(record.id)

                    sync_logger.info(
                        "开始同步实例",
                        module="scheduler",
                        session_id=session.session_id,
                        instance_name=instance.name,
                        db_type=instance.db_type,
                        instance_id=instance.id,
                    )

                    # 执行账户同步，使用task类型
                    result = account_sync_service.sync_accounts(
                        instance, sync_type="task", session_id=session.session_id
                    )

                    if result.get("success"):
                        success_count += 1
                        instance_sync_count = result.get("synced_count", 0)
                        total_synced_count += instance_sync_count
                        total_added_count += result.get("added_count", 0)
                        total_removed_count += result.get("removed_count", 0)
                        total_modified_count += result.get("modified_count", 0)

                        # 完成实例同步
                        sync_session_service.complete_instance_sync(
                            record.id,
                            accounts_synced=instance_sync_count,
                            accounts_created=result.get("added_count", 0),
                            accounts_updated=result.get("modified_count", 0),
                            accounts_deleted=result.get("removed_count", 0),
                            sync_details=result.get("details", {}),
                        )

                        sync_logger.info(
                            "实例同步完成",
                            module="scheduler",
                            session_id=session.session_id,
                            instance_name=instance.name,
                            instance_id=instance.id,
                            synced_count=instance_sync_count,
                        )

                        results.append(
                            {
                                "instance_name": instance.name,
                                "success": True,
                                "message": result.get("message", "同步成功"),
                                "synced_count": instance_sync_count,
                            }
                        )
                    else:
                        failed_count += 1
                        error_msg = result.get("message", result.get("error", "未知错误"))

                        # 标记实例同步失败
                        sync_session_service.fail_instance_sync(
                            record.id,
                            error_message=error_msg,
                            sync_details=result.get("details", {}),
                        )

                        sync_logger.warning(
                            "实例同步失败",
                            module="scheduler",
                            session_id=session.session_id,
                            instance_name=instance.name,
                            instance_id=instance.id,
                            error_msg=error_msg,
                        )

                        results.append(
                            {
                                "instance_name": instance.name,
                                "success": False,
                                "message": error_msg,
                                "synced_count": 0,
                            }
                        )

                except Exception as e:
                    failed_count += 1

                    # 标记实例同步失败
                    if record:
                        sync_session_service.fail_instance_sync(
                            record.id,
                            error_message=str(e),
                            sync_details={"exception": str(e)},
                        )

                    sync_logger.error(
                        "实例同步异常",
                        module="scheduler",
                        session_id=session.session_id,
                        instance_name=instance.name,
                        instance_id=instance.id,
                        exception=str(e),
                    )

                    results.append(
                        {
                            "instance_name": instance.name,
                            "success": False,
                            "message": f"同步异常: {str(e)}",
                            "synced_count": 0,
                        }
                    )

            # 记录操作日志
            task_logger.info(
                "定时任务账户同步完成",
                module="task",
                operation_type="TASK_SYNC_ACCOUNTS_COMPLETE",
                session_id=session.session_id,
                total_instances=total_instances,
                success_count=success_count,
                failed_count=failed_count,
                total_synced_count=total_synced_count,
                total_added_count=total_added_count,
                total_removed_count=total_removed_count,
                total_modified_count=total_modified_count,
                results=results,
            )

            # 同步会话记录已通过sync_session_service管理，无需额外创建记录

            sync_logger.info(
                "定时任务账户同步完成",
                module="scheduler",
                session_id=session.session_id,
                total_synced_count=total_synced_count,
                total_instances=total_instances,
            )

            return f"定时任务同步完成，成功 {success_count} 个实例，失败 {failed_count} 个实例，总共同步 {total_synced_count} 个账户"

        except Exception as e:
            sync_logger.error("定时任务账户同步失败", module="scheduler", exception=e)

            # 同步会话记录已通过sync_session_service管理，无需额外创建记录

            return f"定时任务同步失败: {e}"


def health_check():
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
            log_count = Log.query.count()
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


def cleanup_temp_files():
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
            return f"清理临时文件失败: {e}"
