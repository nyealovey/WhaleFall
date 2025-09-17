"""
泰摸鱼吧 - 账户同步服务 (重构版)
统一入口处理所有类型的账户同步逻辑
"""

from typing import Any, Optional
from uuid import uuid4

from app import db
from app.models import Instance
from app.services.sync_data_manager import SyncDataManager
from app.services.sync_session_service import sync_session_service
from app.services.database_service import DatabaseService
from app.utils.structlog_config import get_sync_logger
from app.utils.timezone import now


class AccountSyncService:
    """
    账户同步服务 - 统一入口
    
    支持四种同步类型：
    - MANUAL_SINGLE: 手动单实例同步 (无会话)
    - MANUAL_BATCH: 手动批量同步 (有会话)
    - MANUAL_TASK: 手动任务同步 (有会话)
    - SCHEDULED_TASK: 定时任务同步 (有会话)
    """

    def __init__(self) -> None:
        self.sync_logger = get_sync_logger()
        self.sync_data_manager = SyncDataManager()
        self.database_service = DatabaseService()

    def sync_accounts(self, instance: Instance, sync_type: str = "manual_single", session_id: Optional[str] = None, created_by: Optional[int] = None) -> dict[str, Any]:
        """
        统一账户同步入口
        
        Args:
            instance: 数据库实例
            sync_type: 同步类型 ('manual_single', 'manual_batch', 'manual_task', 'scheduled_task')
            session_id: 同步会话ID（batch类型需要）
            created_by: 创建者ID（手动同步需要）
            
        Returns:
            Dict: 同步结果
        """
        try:
            self.sync_logger.info(
                "开始账户同步",
                module="account_sync_unified",
                instance_name=instance.name,
                db_type=instance.db_type,
                sync_type=sync_type,
                session_id=session_id,
            )

            # 根据同步类型决定是否需要会话管理
            needs_session = sync_type in ["manual_batch", "manual_task", "scheduled_task"]
            
            if needs_session and not session_id:
                # 批量同步类型需要会话管理
                return self._sync_with_session(instance, sync_type, created_by)
            elif sync_type == "manual_single":
                # 单实例同步不需要会话
                return self._sync_single_instance(instance)
            else:
                # 已有会话ID的批量同步
                return self._sync_with_existing_session(instance, session_id)
                
        except Exception as e:
            self.sync_logger.error(
                "同步过程发生异常",
                module="account_sync_unified",
                instance_name=instance.name,
                db_type=instance.db_type,
                sync_type=sync_type,
                error=str(e)
            )
            return {
                "success": False,
                "error": f"同步失败: {str(e)}",
                "synced_count": 0,
                "added_count": 0,
                "modified_count": 0,
                "removed_count": 0,
            }

    def _sync_single_instance(self, instance: Instance) -> dict[str, Any]:
        """
        单实例同步 - 无会话管理
        用于实例页面的直接同步调用
        """
        try:
            # 获取数据库连接
            conn = self.database_service.get_connection(instance)
            if not conn:
                return {"success": False, "error": "无法获取数据库连接"}

            # 更新数据库版本信息
            self._update_database_version(instance, conn)

            # 生成临时会话ID用于日志追踪
            temp_session_id = str(uuid4())

            # 执行同步
            result = self.sync_data_manager.sync_accounts(
                instance=instance,
                connection=conn,
                session_id=temp_session_id
            )

            # 关闭连接
            self.database_service.close_connection(instance)
            
            # 更新实例最后连接时间
            instance.last_connected_at = now()
            db.session.commit()

            self.sync_logger.info(
                "单实例同步完成",
                module="account_sync_unified",
                instance_name=instance.name,
                synced_count=result.get("synced_count", 0),
                added_count=result.get("added_count", 0),
                modified_count=result.get("modified_count", 0),
                removed_count=result.get("removed_count", 0),
            )

            return result

        except Exception as e:
            self.sync_logger.error(
                "单实例同步失败",
                module="account_sync_unified", 
                instance_name=instance.name,
                error=str(e)
            )
            return {"success": False, "error": f"同步失败: {str(e)}"}

    def _sync_with_session(self, instance: Instance, sync_type: str, created_by: Optional[int]) -> dict[str, Any]:
        """
        带会话管理的同步 - 用于批量同步
        """
        try:
            # 创建同步会话
            session = sync_session_service.create_session(
                sync_type=sync_type,
                sync_category="account", 
                created_by=created_by
            )

            # 添加实例记录
            records = sync_session_service.add_instance_records(
                session.session_id, 
                [instance.id]
            )
            
            if not records:
                return {"success": False, "error": "创建实例记录失败"}

            record = records[0]
            
            # 开始实例同步
            sync_session_service.start_instance_sync(record.id)

            # 执行实际同步
            result = self._sync_with_existing_session(instance, session.session_id)

            # 更新实例同步状态
            if result["success"]:
                sync_session_service.complete_instance_sync(
                    record.id,
                    accounts_synced=result.get("synced_count", 0),
                    accounts_created=result.get("added_count", 0),
                    accounts_updated=result.get("modified_count", 0), 
                    accounts_deleted=result.get("removed_count", 0),
                    sync_details=result.get("details", {})
                )
            else:
                sync_session_service.fail_instance_sync(
                    record.id,
                    error_message=result.get("error", "同步失败"),
                    sync_details=result.get("details", {})
                )

            return result

        except Exception as e:
            self.sync_logger.error(
                "会话同步失败",
                module="account_sync_unified",
                instance_name=instance.name,
                sync_type=sync_type,
                error=str(e)
            )
            return {"success": False, "error": f"会话同步失败: {str(e)}"}

    def _sync_with_existing_session(self, instance: Instance, session_id: str) -> dict[str, Any]:
        """
        使用现有会话ID进行同步
        """
        try:
            # 获取数据库连接
            conn = self.database_service.get_connection(instance)
            if not conn:
                return {"success": False, "error": "无法获取数据库连接"}

            # 更新数据库版本信息
            self._update_database_version(instance, conn)

            # 执行同步
            result = self.sync_data_manager.sync_accounts(
                instance=instance,
                connection=conn,
                session_id=session_id
            )

            # 关闭连接
            self.database_service.close_connection(instance)

            # 更新实例最后连接时间
            instance.last_connected_at = now()
            db.session.commit()

            return result

        except Exception as e:
            self.sync_logger.error(
                "现有会话同步失败",
                module="account_sync_unified",
                instance_name=instance.name,
                session_id=session_id,
                error=str(e)
            )
            return {"success": False, "error": f"同步失败: {str(e)}"}

    def _update_database_version(self, instance: Instance, conn) -> None:
        """更新数据库版本信息"""
        try:
            version_info = self.database_service.get_database_version(instance, conn)
            if version_info and version_info != instance.database_version:
                from app.utils.version_parser import DatabaseVersionParser
                
                # 解析版本信息
                parsed = DatabaseVersionParser.parse_version(instance.db_type.lower(), version_info)
                
                # 更新实例的版本信息
                instance.database_version = parsed['original']
                instance.main_version = parsed['main_version']
                instance.detailed_version = parsed['detailed_version']
                
                db.session.commit()
                
                self.sync_logger.info(
                    "更新数据库版本",
                    module="account_sync_unified",
                    instance_name=instance.name,
                    version=version_info
                )
        except Exception as e:
            self.sync_logger.warning(
                "更新数据库版本失败",
                module="account_sync_unified",
                instance_name=instance.name,
                error=str(e)
            )


# 创建服务实例
account_sync_service = AccountSyncService()
