"""账户同步服务，两阶段协调入口。"""

from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4

from app import db
from app.constants.sync_constants import SyncOperationType
from app.models import Instance
from app.services.account_sync.coordinator import AccountSyncCoordinator
from app.services.sync_session_service import sync_session_service
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


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
        # 协调器按需创建

    def sync_accounts(
        self,
        instance: Instance,
        sync_type: str = SyncOperationType.MANUAL_SINGLE.value,
        session_id: str | None = None,
        created_by: int | None = None,
    ) -> dict[str, Any]:
        """
        统一账户同步入口

        Args:
            instance: 数据库实例
            sync_type: 同步操作方式 ('manual_single', 'manual_batch', 'manual_task', 'scheduled_task')
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

            # 根据同步操作方式决定是否需要会话管理
            if sync_type == SyncOperationType.MANUAL_SINGLE.value:
                # 单实例同步不需要会话
                return self._sync_single_instance(instance)
            elif sync_type in [SyncOperationType.MANUAL_BATCH.value, SyncOperationType.MANUAL_TASK.value, SyncOperationType.SCHEDULED_TASK.value]:
                if session_id:
                    # 已有会话ID的批量同步
                    return self._sync_with_existing_session(instance, session_id)
                else:
                    # 批量同步操作方式需要会话管理
                    return self._sync_with_session(instance, sync_type, created_by)
            else:
                # 未知同步操作方式，默认使用单实例同步
                return self._sync_single_instance(instance)

        except Exception as e:
            # 分类异常处理，提供更详细的错误信息
            error_type = type(e).__name__
            if "JSON" in error_type or "serialization" in str(e).lower():
                error_msg = f"权限数据序列化失败: {str(e)}"
            elif "Connection" in error_type or "timeout" in str(e).lower():
                error_msg = f"数据库连接问题: {str(e)}"
            elif "Permission" in error_type or "access" in str(e).lower():
                error_msg = f"数据库权限不足: {str(e)}"
            else:
                error_msg = f"同步失败: {str(e)}"

            self.sync_logger.error(
                "同步过程发生异常",
                module="account_sync_unified",
                instance_name=instance.name,
                db_type=instance.db_type,
                sync_type=sync_type,
                error_type=error_type,
                error=str(e),
            )
            return {
                "success": False,
                "error": error_msg,
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
        temp_session_id = str(uuid4())
        try:
            with AccountSyncCoordinator(instance) as coordinator:
                summary = coordinator.sync_all(session_id=temp_session_id)
            result = self._build_result(summary)
            instance.last_connected = time_utils.now()
            db.session.commit()
            self.sync_logger.info(
                "单实例同步完成",
                module="account_sync_unified",
                instance_name=instance.name,
                inventory=summary.get("inventory", {}),
                collection=summary.get("collection", {}),
            )
            result["details"] = summary
            return result
        except Exception as exc:  # noqa: BLE001
            self.sync_logger.error(
                "单实例同步失败",
                module="account_sync_unified",
                instance_name=instance.name,
                error=str(exc),
                exc_info=True,
            )
            return {"success": False, "error": f"同步失败: {str(exc)}"}

    def _sync_with_session(self, instance: Instance, sync_type: str, created_by: int | None) -> dict[str, Any]:
        """
        带会话管理的同步 - 用于批量同步
        """
        try:
            # 创建同步会话
            session = sync_session_service.create_session(
                sync_type=sync_type, sync_category="account", created_by=created_by
            )

            # 添加实例记录
            records = sync_session_service.add_instance_records(session.session_id, [instance.id])

            if not records:
                return {"success": False, "error": "创建实例记录失败"}

            record = records[0]

            # 开始实例同步
            sync_session_service.start_instance_sync(record.id)

            # 执行实际同步
            result = self._sync_with_existing_session(instance, session.session_id)

            # 更新实例同步状态
            if result["success"]:
                details = result.get("details", {})
                inventory = details.get("inventory", {})
                collection = details.get("collection", {})
                sync_session_service.complete_instance_sync(
                    record.id,
                    items_synced=collection.get("processed_records", 0)
                    if collection.get("status") != "skipped"
                    else 0,
                    items_created=inventory.get("created", 0),
                    items_updated=collection.get("updated", 0),
                    items_deleted=inventory.get("deactivated", 0),
                    sync_details=details,
                )
            else:
                sync_session_service.fail_instance_sync(
                    record.id, error_message=result.get("error", "同步失败"), sync_details=result.get("details", {})
                )

            return result

        except Exception as e:
            self.sync_logger.error(
                "会话同步失败",
                module="account_sync_unified",
                instance_name=instance.name,
                sync_type=sync_type,
                error=str(e),
            )
            return {"success": False, "error": f"会话同步失败: {str(e)}"}

    def _sync_with_existing_session(self, instance: Instance, session_id: str) -> dict[str, Any]:
        """
        使用现有会话ID进行同步
        """
        try:
            with AccountSyncCoordinator(instance) as coordinator:
                summary = coordinator.sync_all(session_id=session_id)
            result = self._build_result(summary)
            result["details"] = summary
            instance.last_connected = time_utils.now()
            db.session.commit()
            return result
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            self.sync_logger.error(
                "现有会话同步失败",
                module="account_sync_unified",
                instance_name=instance.name,
                session_id=session_id,
                error=str(exc),
                exc_info=True,
            )
            return {"success": False, "error": f"同步失败: {str(exc)}"}

    def _build_result(self, summary: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        inventory = summary.get("inventory", {})
        collection = summary.get("collection", {})

        added = inventory.get("created", 0)
        reactivated = inventory.get("reactivated", 0)
        removed = inventory.get("deactivated", 0)
        updated = collection.get("updated", 0)
        created = collection.get("created", 0)
        processed_records = collection.get("processed_records", created + updated)
        if collection.get("status") == "skipped":
            processed_records = 0

        # 构建详细的成功消息
        message_parts = []
        if processed_records > 0:
            message_parts.append(f"同步 {processed_records} 个账户")
        if added + reactivated > 0:
            message_parts.append(f"新增 {added + reactivated} 个")
        if updated > 0:
            message_parts.append(f"更新 {updated} 个")
        if removed > 0:
            message_parts.append(f"移除 {removed} 个")
        
        message = "、".join(message_parts) if message_parts else "账户同步完成"

        return {
            "success": True,
            "message": message,
            "synced_count": processed_records,
            "added_count": added + reactivated,
            "modified_count": updated,
            "removed_count": removed,
        }


# 创建服务实例
account_sync_service = AccountSyncService()
