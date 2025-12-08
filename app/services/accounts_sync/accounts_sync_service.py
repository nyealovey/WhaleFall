"""账户同步服务,两阶段协调入口.."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from app import db
from app.constants.sync_constants import SyncOperationType
from app.services.accounts_sync.coordinator import AccountSyncCoordinator
from app.services.sync_session_service import sync_session_service
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.models import Instance


class AccountSyncService:
    """账户同步服务 - 统一入口..

    提供账户同步的统一入口,支持四种同步类型:
    - MANUAL_SINGLE: 手动单实例同步(无会话)
    - MANUAL_BATCH: 手动批量同步(有会话)
    - MANUAL_TASK: 手动任务同步(有会话)
    - SCHEDULED_TASK: 定时任务同步(有会话)

    Attributes:
        sync_logger: 同步日志记录器.

    """

    def __init__(self) -> None:
        """初始化账户同步服务.."""
        self.sync_logger = get_sync_logger()
        # 协调器按需创建

    def sync_accounts(
        self,
        instance: Instance,
        sync_type: str = SyncOperationType.MANUAL_SINGLE.value,
        session_id: str | None = None,
        created_by: int | None = None,
    ) -> dict[str, Any]:
        """统一账户同步入口..

        根据同步类型执行相应的同步流程,支持单实例同步和批量同步.

        Args:
            instance: 数据库实例对象.
            sync_type: 同步操作方式,可选值:'manual_single'、'manual_batch'、
                'manual_task'、'scheduled_task',默认为 'manual_single'.
            session_id: 同步会话 ID,批量同步时需要提供.
            created_by: 创建者用户 ID,手动同步时需要提供.

        Returns:
            同步结果字典,格式如下:
            {
                'success': True,
                'message': '同步 100 个账户、新增 10 个、更新 5 个',
                'synced_count': 100,
                'added_count': 10,
                'modified_count': 5,
                'removed_count': 2,
                'details': {...}  # 详细的同步信息
            }
            失败时返回:
            {
                'success': False,
                'error': '错误信息',
                'synced_count': 0,
                'added_count': 0,
                'modified_count': 0,
                'removed_count': 0
            }

        """
        try:
            self.sync_logger.info(
                "开始账户同步",
                module="accounts_sync",
                phase="start",
                operation="sync_accounts",
                instance_id=instance.id,
                instance_name=instance.name,
                db_type=instance.db_type,
                sync_type=sync_type,
                session_id=session_id,
            )

            # 根据同步操作方式决定是否需要会话管理
            if sync_type == SyncOperationType.MANUAL_SINGLE.value:
                # 单实例同步不需要会话
                return self._sync_single_instance(instance)
            if sync_type in [SyncOperationType.MANUAL_BATCH.value, SyncOperationType.MANUAL_TASK.value, SyncOperationType.SCHEDULED_TASK.value]:
                if session_id:
                    # 已有会话ID的批量同步
                    return self._sync_with_existing_session(instance, session_id, sync_type=sync_type)
                # 批量同步操作方式需要会话管理
                return self._sync_with_session(instance, sync_type, created_by)
            # 未知同步操作方式,默认使用单实例同步
            return self._sync_single_instance(instance)

        except Exception as e:
            # 分类异常处理,提供更详细的错误信息
            error_type = type(e).__name__
            if "JSON" in error_type or "serialization" in str(e).lower():
                error_msg = f"权限数据序列化失败: {e!s}"
            elif "Connection" in error_type or "timeout" in str(e).lower():
                error_msg = f"数据库连接问题: {e!s}"
            elif "Permission" in error_type or "access" in str(e).lower():
                error_msg = f"数据库权限不足: {e!s}"
            else:
                error_msg = f"同步失败: {e!s}"

            self.sync_logger.exception(
                "同步过程发生异常",
                module="accounts_sync",
                phase="error",
                operation="sync_accounts",
                instance_id=instance.id,
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
        """单实例同步 - 无会话管理..

        用于实例页面的直接同步调用,不创建持久化会话记录.
        使用临时会话 ID 进行同步,完成后更新实例的最后连接时间.

        Args:
            instance: 数据库实例对象.

        Returns:
            同步结果字典,格式与 sync_accounts 方法相同.

        Raises:
            Exception: 同步过程中的任何异常都会被捕获并转换为错误结果.

        """
        temp_session_id = str(uuid4())
        try:
            with AccountSyncCoordinator(instance) as coordinator:
                summary = coordinator.sync_all(session_id=temp_session_id)
            result = self._build_result(summary)
            instance.last_connected = time_utils.now()
            db.session.commit()
            result["details"] = summary
            self._emit_completion_log(
                instance=instance,
                session_id=temp_session_id,
                sync_type=SyncOperationType.MANUAL_SINGLE.value,
                result=result,
            )
            return result
        except Exception as exc:
            self.sync_logger.error(
                "单实例同步失败",
                module="accounts_sync",
                phase="error",
                operation="sync_accounts",
                instance_id=instance.id,
                instance_name=instance.name,
                session_id=temp_session_id,
                error=str(exc),
                exc_info=True,
            )
            failure_result = {"success": False, "error": f"同步失败: {exc!s}"}
            self._emit_completion_log(
                instance=instance,
                session_id=temp_session_id,
                sync_type=SyncOperationType.MANUAL_SINGLE.value,
                result=failure_result,
            )
            return failure_result

    def _sync_with_session(self, instance: Instance, sync_type: str, created_by: int | None) -> dict[str, Any]:
        """带会话管理的同步 - 用于批量同步..

        创建新的同步会话,执行同步并记录结果.会话记录会持久化到数据库,
        用于追踪批量同步的进度和结果.

        Args:
            instance: 数据库实例对象.
            sync_type: 同步操作方式,如 'manual_batch'、'scheduled_task'.
            created_by: 创建者用户 ID,手动同步时必须提供.

        Returns:
            同步结果字典,格式与 sync_accounts 方法相同.

        Raises:
            Exception: 会话创建或同步过程中的异常会被捕获并转换为错误结果.

        """
        try:
            # 创建同步会话
            session = sync_session_service.create_session(
                sync_type=sync_type, sync_category="account", created_by=created_by,
            )

            # 添加实例记录
            records = sync_session_service.add_instance_records(session.session_id, [instance.id])

            if not records:
                return {"success": False, "error": "创建实例记录失败"}

            record = records[0]

            # 开始实例同步
            sync_session_service.start_instance_sync(record.id)

            # 执行实际同步
            result = self._sync_with_existing_session(instance, session.session_id, sync_type=sync_type)

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
                    record.id, error_message=result.get("error", "同步失败"), sync_details=result.get("details", {}),
                )

            return result

        except Exception as e:
            self.sync_logger.exception(
                "会话同步失败",
                module="accounts_sync",
                phase="error",
                operation="sync_accounts",
                instance_name=instance.name,
                instance_id=instance.id,
                sync_type=sync_type,
                error=str(e),
            )
            failure_result = {"success": False, "error": f"会话同步失败: {e!s}"}
            self._emit_completion_log(
                instance=instance,
                session_id=session.session_id if "session" in locals() else None,
                sync_type=sync_type,
                result=failure_result,
            )
            return failure_result

    def _sync_with_existing_session(
        self,
        instance: Instance,
        session_id: str,
        *,
        sync_type: str | None = None,
    ) -> dict[str, Any]:
        """使用现有会话 ID 进行同步..

        在已有会话的上下文中执行同步操作,用于批量同步场景中的单个实例同步.

        Args:
            instance: 数据库实例对象.
            session_id: 已存在的会话 ID,用于关联同步记录.
            sync_type: 同步操作方式,可选,用于日志记录.

        Returns:
            同步结果字典,格式与 sync_accounts 方法相同.

        Raises:
            Exception: 同步过程中的异常会被捕获,数据库会回滚.

        """
        try:
            with AccountSyncCoordinator(instance) as coordinator:
                summary = coordinator.sync_all(session_id=session_id)
            result = self._build_result(summary)
            result["details"] = summary
            instance.last_connected = time_utils.now()
            db.session.commit()
            self._emit_completion_log(
                instance=instance,
                session_id=session_id,
                sync_type=sync_type or "session",
                result=result,
            )
            return result
        except Exception as exc:
            db.session.rollback()
            self.sync_logger.error(
                "现有会话同步失败",
                module="accounts_sync",
                phase="error",
                operation="sync_accounts",
                instance_name=instance.name,
                instance_id=instance.id,
                session_id=session_id,
                error=str(exc),
                exc_info=True,
            )
            failure_result = {"success": False, "error": f"同步失败: {exc!s}"}
            self._emit_completion_log(
                instance=instance,
                session_id=session_id,
                sync_type=sync_type or "session",
                result=failure_result,
            )
            return failure_result

    def _build_result(self, summary: dict[str, dict[str, int]]) -> dict[str, Any]:
        """构建同步结果字典..

        从同步汇总信息中提取关键指标,构建统一的结果格式.

        Args:
            summary: 同步汇总信息,包含 inventory 和 collection 两部分.

        Returns:
            格式化的同步结果字典.

        """
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

    def _emit_completion_log(
        self,
        *,
        instance: Instance,
        session_id: str | None,
        sync_type: str,
        result: dict[str, Any],
    ) -> None:
        """记录同步完成日志..

        根据同步结果记录成功或失败日志.

        Args:
            instance: 数据库实例对象.
            session_id: 会话 ID,可选.
            sync_type: 同步操作方式.
            result: 同步结果字典.

        Returns:
            None: 日志写入后立即返回.

        """
        message = result.get("message") or result.get("error") or "账户同步完成"
        log_kwargs: dict[str, Any] = {
                "module": "accounts_sync",
            "phase": "completed" if result.get("success", True) else "error",
            "operation": "sync_accounts",
            "instance_id": instance.id,
            "instance_name": instance.name,
            "session_id": session_id,
            "sync_type": sync_type,
            "synced_count": result.get("synced_count", 0),
            "added_count": result.get("added_count", 0),
            "modified_count": result.get("modified_count", 0),
            "removed_count": result.get("removed_count", 0),
            "message": message,
        }
        if result.get("success", True):
            self.sync_logger.info("实例账户同步完成", **log_kwargs)
        else:
            self.sync_logger.error("实例账户同步失败", **log_kwargs)


# 创建服务实例
accounts_sync_service = AccountSyncService()
