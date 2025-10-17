"""
鲸落遗留定时任务定义
从 app/tasks.py 迁移过来的任务函数
"""

import os
from datetime import datetime, timedelta

from app import create_app, db
from app.constants.sync_constants import SyncOperationType, SyncCategory
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
                task_name="cleanup_old_logs",
                deleted_logs=deleted_logs,
                cleaned_files=cleaned_files,
                deleted_sync_sessions=deleted_sync_sessions,
                deleted_sync_records=deleted_sync_records,
                deleted_account_sync_data=deleted_account_sync_data,
                deleted_change_logs=deleted_change_logs,
            )

        except Exception as e:
            db.session.rollback()
            task_logger.error(
                "定时任务清理失败",
                module="task",
                task_name="cleanup_old_logs",
                error=str(e),
                exc_info=True,
            )
            raise


def sync_accounts(**kwargs):
    """同步账户任务 - 同步所有实例的账户信息"""
    sync_logger = get_sync_logger()
    
    app = create_app()
    with app.app_context():
        try:
            # 获取所有启用的实例
            instances = Instance.query.filter_by(is_active=True).all()
            
            if not instances:
                sync_logger.info("没有找到启用的数据库实例")
                return
            
            sync_logger.info(f"开始同步 {len(instances)} 个实例的账户信息")
            
            total_synced = 0
            total_failed = 0
            
            # 创建同步会话
            session = sync_session_service.create_session(
                sync_type=SyncOperationType.SCHEDULED_TASK.value,
                sync_category=SyncCategory.ACCOUNT.value,
                created_by=None  # 定时任务没有创建者
            )
            
            # 添加实例记录
            instance_ids = [inst.id for inst in instances]
            records = sync_session_service.add_instance_records(session.session_id, instance_ids)
            session.total_instances = len(instances)
            
            for i, instance in enumerate(instances):
                try:
                    # 找到对应的记录
                    record = records[i] if i < len(records) else None
                    if not record:
                        continue
                    
                    # 开始实例同步
                    sync_session_service.start_instance_sync(record.id)
                    
                    # 执行同步
                    result = account_sync_service.sync_accounts(
                        instance, 
                        sync_type=SyncOperationType.SCHEDULED_TASK.value, 
                        session_id=session.session_id
                    )
                    
                    if result.get("success", False):
                        total_synced += 1
                        
                        # 完成实例同步
                        sync_session_service.complete_instance_sync(
                            record.id,
                            items_synced=result.get("synced_count", 0),
                            items_created=result.get("added_count", 0),
                            items_updated=result.get("modified_count", 0),
                            items_deleted=result.get("removed_count", 0),
                            sync_details=result.get("details", {})
                        )
                        
                        sync_logger.info(
                            f"实例 {instance.name} 同步成功",
                            instance_id=instance.id,
                            session_id=session.session_id,
                            synced_count=result.get("synced_count", 0)
                        )
                    else:
                        total_failed += 1
                        
                        # 标记实例同步失败
                        sync_session_service.fail_instance_sync(
                            record.id, 
                            result.get("error", "未知错误")
                        )
                        
                        sync_logger.error(
                            f"实例 {instance.name} 同步失败",
                            instance_id=instance.id,
                            session_id=session.session_id,
                            error=result.get("error", "未知错误")
                        )
                        
                except Exception as e:
                    total_failed += 1
                    
                    # 标记实例同步失败
                    if 'record' in locals() and record:
                        sync_session_service.fail_instance_sync(record.id, str(e))
                    
                    sync_logger.error(
                        f"实例 {instance.name} 同步异常",
                        instance_id=instance.id,
                        error=str(e),
                        exc_info=True
                    )
            
            # 更新会话状态
            session.successful_instances = total_synced
            session.failed_instances = total_failed
            session.status = "completed" if total_failed == 0 else "failed"
            session.completed_at = now()
            db.session.commit()
            
            sync_logger.info(
                "账户同步任务完成",
                session_id=session.session_id,
                total_instances=len(instances),
                total_synced=total_synced,
                total_failed=total_failed
            )
            
        except Exception as e:
            # 更新会话状态为失败
            if 'session' in locals() and session:
                session.status = "failed"
                session.completed_at = now()
                session.failed_instances = len(instances)
                db.session.commit()
            
            sync_logger.error(
                "账户同步任务失败",
                error=str(e),
                exc_info=True
            )
            raise


def _cleanup_temp_files() -> int:
    """清理临时文件"""
    cleaned_count = 0
    
    try:
        # 清理日志目录中的临时文件
        log_dir = os.path.join(os.getcwd(), "userdata", "log")
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                if filename.endswith(('.tmp', '.temp', '.log.old')):
                    file_path = os.path.join(log_dir, filename)
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except OSError:
                        pass
        
        # 清理导出目录中的临时文件
        export_dir = os.path.join(os.getcwd(), "userdata", "exports")
        if os.path.exists(export_dir):
            for filename in os.listdir(export_dir):
                if filename.endswith(('.tmp', '.temp')):
                    file_path = os.path.join(export_dir, filename)
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except OSError:
                        pass
                        
    except Exception as e:
        get_task_logger().warning(f"清理临时文件时出错: {e}")
    
    return cleaned_count
