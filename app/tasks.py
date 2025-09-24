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
                
                # 找到对应的记录
                record = next((r for r in records if r.instance_id == instance.id), None)
                if not record:
                    task_logger.warning(f"未找到实例 {instance.name} 的同步记录，跳过")
                    continue
                
                try:
                    # 开始实例同步 - 将状态从pending改为running
                    sync_session_service.start_instance_sync(record.id)
                    
                    # 使用统一的账户同步服务，与"同步所有账户"相同的逻辑
                    result = account_sync_service.sync_accounts(
                        instance, sync_type="scheduled_task", session_id=session.session_id
                    )
                    
                    if result["success"]:
                        # 完成实例同步
                        sync_session_service.complete_instance_sync(
                            record.id,
                            accounts_synced=result.get("synced_count", 0),
                            accounts_created=result.get("added_count", 0),
                            accounts_updated=result.get("modified_count", 0),
                            accounts_deleted=result.get("removed_count", 0),
                            sync_details=result.get("details", {}),
                        )
                        task_logger.info(f"实例同步成功: {instance.name}")
                    else:
                        task_logger.error(f"实例同步失败: {instance.name}", error=result.get("error", "未知错误"))
                        # 标记为失败
                        sync_session_service.fail_instance_sync(record.id, result.get("error", "同步失败"))
                        
                except Exception as e:
                    task_logger.error(f"触发实例同步时发生意外错误: {instance.name}", error=str(e))
                    # 标记为失败
                    sync_session_service.fail_instance_sync(record.id, str(e))

            # 5. 任务结束 - 检查所有实例状态
            task_logger.info("所有实例同步任务已触发，检查最终状态...")
            
            # 等待一小段时间让所有实例完成
            import time
            time.sleep(2)
            
            # 检查最终状态
            final_records = sync_session_service.get_session_records(session.session_id)
            pending_count = len([r for r in final_records if r.status == "pending"])
            running_count = len([r for r in final_records if r.status == "running"])
            completed_count = len([r for r in final_records if r.status == "completed"])
            failed_count = len([r for r in final_records if r.status == "failed"])
            
            task_logger.info(
                f"最终状态统计 - 总计: {len(final_records)}, "
                f"待处理: {pending_count}, 运行中: {running_count}, "
                f"已完成: {completed_count}, 已失败: {failed_count}"
            )
            
            # 强制更新会话统计和状态
            sync_session_service._update_session_statistics(session.session_id)
            
            # 重新获取会话对象并手动更新状态
            session = sync_session_service.get_session_by_id(session.session_id)
            if session:
                # 直接调用会话的update_statistics方法，这会更新最终状态
                session.update_statistics(succeeded_instances=completed_count, failed_instances=failed_count)
                db.session.commit()
                
                task_logger.info(
                    f"会话状态已更新为: {session.status}, "
                    f"成功: {session.successful_instances}, 失败: {session.failed_instances}"
                )
            
            task_logger.info("请在同步会话页面查看最终结果。")

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
