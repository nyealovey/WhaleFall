"""鲸落 - 同步会话服务.

管理同步会话和实例记录的业务逻辑.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, cast

from app import db
from app.core.constants import SyncSessionStatus, SyncStatus
from app.core.exceptions import NotFoundError, ValidationError
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.repositories.sync_sessions_repository import SyncSessionsRepository
from app.schemas.internal_contracts.sync_details_v1 import normalize_sync_details_v1
from app.utils.structlog_config import get_sync_logger, get_system_logger
from app.utils.time_utils import time_utils


@dataclass(slots=True)
class SyncItemStats:
    """同步项统计."""

    items_synced: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_deleted: int = 0


class SyncSessionService:
    """同步会话服务.

    管理批量同步会话和实例记录的业务逻辑,包括会话创建、实例记录管理、
    同步状态更新和统计信息维护.

    Attributes:
        system_logger: 系统日志记录器.
        sync_logger: 同步日志记录器.

    """

    def __init__(self, repository: SyncSessionsRepository | None = None) -> None:
        """初始化同步会话服务,准备系统与同步日志记录器."""
        self.system_logger = get_system_logger()
        self.sync_logger = get_sync_logger()
        self._repository = repository or SyncSessionsRepository()

    def _clean_sync_details(self, sync_details: dict[str, Any] | None) -> dict[str, Any] | None:
        """清理同步详情中的 datetime 对象,确保 JSON 可序列化.

        递归遍历同步详情字典,将所有 datetime 和 date 对象转换为 ISO 8601 格式字符串.

        Args:
            sync_details: 原始同步详情字典,可能包含 datetime 对象.

        Returns:
            清理后的同步详情字典,所有 datetime 对象已转换为字符串.
            如果输入为 None,则返回 None.

        """
        if sync_details is None:
            return None

        normalized = normalize_sync_details_v1(sync_details)
        if normalized is None:
            return None

        def clean_value(value: object) -> object:
            if isinstance(value, (datetime, date)):
                return value.isoformat()
            if isinstance(value, dict):
                return {k: clean_value(v) for k, v in value.items()}
            if isinstance(value, list):
                return [clean_value(item) for item in value]
            return value

        return cast("dict[str, Any]", clean_value(normalized))

    def create_session(
        self,
        sync_type: str,
        sync_category: str = "account",
        created_by: int | None = None,
    ) -> SyncSession:
        """创建同步会话.

        创建新的同步会话记录,并记录日志.

        Args:
            sync_type: 同步操作方式,可选值: 'manual_single'(手动单个), 'manual_batch'(手动批量),
                'manual_task'(手动任务), 'scheduled_task'(定时任务).
            sync_category: 同步分类,可选值: 'account'(账户), 'capacity'(容量), 'config'(配置),
                'aggregation'(聚合), 'other'(其他). 默认: 'account'.
            created_by: 创建用户 ID,可选.

        Returns:
            创建的同步会话对象.

        Raises:
            Exception: 当数据库操作失败时抛出.

        """
        try:
            session = SyncSession(sync_type=sync_type, sync_category=sync_category, created_by=created_by)
            with db.session.begin_nested():
                self._repository.add_session(session)
        except Exception as exc:
            self.sync_logger.exception(
                "创建同步会话失败",
                module="sync_session",
                sync_type=sync_type,
                sync_category=sync_category,
                error=str(exc),
            )
            raise
        else:
            self.sync_logger.info(
                "创建同步会话",
                module="sync_session",
                session_id=session.session_id,
                sync_type=sync_type,
                sync_category=sync_category,
                created_by=created_by,
            )

            return session

    def add_instance_records(
        self,
        session_id: str,
        instance_ids: list[int],
        sync_category: str = "account",
    ) -> list[SyncInstanceRecord]:
        """为会话添加实例记录.

        根据实例 ID 列表批量创建实例同步记录,并关联到指定会话.

        Args:
            session_id: 会话 ID.
            instance_ids: 实例 ID 列表.
            sync_category: 同步分类,可选值:'account'、'capacity'、'config'、
                'aggregation'、'other',默认为 'account'.

        Returns:
            创建的实例记录列表.

        Raises:
            Exception: 当数据库操作失败时抛出.

        """
        instances = self._repository.list_instances_by_ids(instance_ids)
        instance_dict = {inst.id: inst for inst in instances}
        missing_instance_ids = sorted(set(instance_ids) - set(instance_dict))
        if missing_instance_ids:
            raise ValidationError(
                "存在无效的 instance_id",
                extra={"missing_instance_ids": missing_instance_ids},
            )

        records: list[SyncInstanceRecord] = []
        try:
            with db.session.begin_nested():
                for instance_id in instance_ids:
                    instance = instance_dict[instance_id]
                    record = SyncInstanceRecord(
                        session_id=session_id,
                        instance_id=instance_id,
                        instance_name=instance.name,
                        sync_category=sync_category,  # 使用传入的同步分类
                    )
                    records.append(record)

                self._repository.add_records(records)
        except Exception as exc:
            self.sync_logger.exception(
                "添加实例记录失败",
                module="sync_session",
                session_id=session_id,
                sync_category=sync_category,
                error=str(exc),
            )
            raise

        self.sync_logger.info(
            "添加实例记录",
            module="sync_session",
            session_id=session_id,
            instance_count=len(records),
            sync_category=sync_category,
        )

        return records

    def start_instance_sync(self, record_id: int) -> None:
        """开始实例同步.

        将实例记录状态标记为同步中,并记录开始时间.

        Args:
            record_id: 实例记录 ID.

        """
        record = self._repository.get_record_by_id(record_id)
        if not record:
            raise NotFoundError("实例同步记录不存在", extra={"record_id": record_id})

        try:
            with db.session.begin_nested():
                record.start_sync()
                self._repository.flush()
        except Exception as exc:
            self.sync_logger.exception(
                "开始实例同步失败",
                module="sync_session",
                record_id=record_id,
                error=str(exc),
            )
            raise
        else:
            self.sync_logger.info(
                "开始实例同步",
                module="sync_session",
                session_id=record.session_id,
                instance_id=record.instance_id,
                instance_name=record.instance_name,
            )

            return

    def complete_instance_sync(
        self,
        record_id: int,
        *,
        stats: SyncItemStats,
        sync_details: dict[str, Any] | None = None,
    ) -> None:
        """完成实例同步.

        将实例记录标记为完成状态,记录同步统计信息,并更新会话统计.

        Args:
            record_id: 实例记录 ID.
            stats: 同步统计对象(必填).
            sync_details: 同步详情字典,可选.

        """
        record = self._repository.get_record_by_id(record_id)
        if not record:
            raise NotFoundError("实例同步记录不存在", extra={"record_id": record_id})

        items_synced = stats.items_synced
        items_created = stats.items_created
        items_updated = stats.items_updated
        items_deleted = stats.items_deleted

        try:
            with db.session.begin_nested():
                record.complete_sync(
                    items_synced=items_synced,
                    items_created=items_created,
                    items_updated=items_updated,
                    items_deleted=items_deleted,
                    sync_details=self._clean_sync_details(sync_details),
                )
                self._repository.flush()

                # 更新会话统计
                self._update_session_statistics(record.session_id)
                self._repository.flush()
        except Exception as exc:
            self.sync_logger.exception(
                "完成实例同步失败",
                module="sync_session",
                record_id=record_id,
                error=str(exc),
            )
            raise
        else:
            self.sync_logger.info(
                "完成实例同步",
                module="sync_session",
                session_id=record.session_id,
                instance_id=record.instance_id,
                instance_name=record.instance_name,
                items_synced=items_synced,
                items_created=items_created,
                items_updated=items_updated,
                items_deleted=items_deleted,
            )

            return

    def fail_instance_sync(
        self,
        record_id: int,
        error_message: str,
        sync_details: dict[str, Any] | None = None,
    ) -> None:
        """标记实例同步失败.

        将实例记录标记为失败状态,记录错误信息,并更新会话统计.

        Args:
            record_id: 实例记录 ID.
            error_message: 错误信息描述.
            sync_details: 同步详情字典,可选.

        """
        record = self._repository.get_record_by_id(record_id)
        if not record:
            raise NotFoundError("实例同步记录不存在", extra={"record_id": record_id})

        try:
            with db.session.begin_nested():
                record.fail_sync(error_message=error_message, sync_details=self._clean_sync_details(sync_details))
                self._repository.flush()

                # 更新会话统计
                self._update_session_statistics(record.session_id)
                self._repository.flush()
        except Exception as exc:
            self.sync_logger.exception(
                "标记实例同步失败时出错",
                module="sync_session",
                record_id=record_id,
                error=str(exc),
            )
            raise
        else:
            self.sync_logger.error(
                "实例同步失败",
                module="sync_session",
                session_id=record.session_id,
                instance_id=record.instance_id,
                instance_name=record.instance_name,
                error_message=error_message,
            )

            return

    def _update_session_statistics(self, session_id: str) -> None:
        """更新会话统计信息.

        统计会话中成功和失败的实例数量,并更新会话对象.

        Args:
            session_id: 会话 ID.

        Returns:
            None: 统计更新完成后返回.

        Raises:
            Exception: 当数据库操作失败时抛出.

        """
        try:
            session = self._repository.lock_session_by_session_id(session_id)
            succeeded_instances = self._repository.count_records_by_status(
                session_id=session_id,
                status=SyncStatus.COMPLETED,
            )
            failed_instances = self._repository.count_records_by_status(
                session_id=session_id,
                status=SyncStatus.FAILED,
            )

            session.update_statistics(
                succeeded_instances=succeeded_instances,
                failed_instances=failed_instances,
            )
            self._repository.flush()
        except Exception as exc:
            self.sync_logger.exception(
                "更新会话统计失败",
                module="sync_session",
                session_id=session_id,
                error=str(exc),
            )
            raise

    def get_session_records(self, session_id: str) -> list[SyncInstanceRecord]:
        """获取会话的所有实例记录.

        Args:
            session_id: 会话 ID.

        Returns:
            实例记录列表.

        """
        try:
            return self._repository.list_records_by_session(session_id)
        except Exception as e:
            self.sync_logger.exception(
                "获取会话记录失败",
                module="sync_session",
                session_id=session_id,
                error=str(e),
            )
            raise

    def get_session_by_id(self, session_id: str) -> SyncSession | None:
        """根据 ID 获取会话.

        Args:
            session_id: 会话 ID.

        Returns:
            会话对象,不存在时返回 None; 查询失败时抛出异常.

        """
        try:
            return self._repository.get_session_by_session_id(session_id)
        except Exception as e:
            self.sync_logger.exception(
                "获取会话失败",
                module="sync_session",
                session_id=session_id,
                error=str(e),
            )
            raise

    def get_sessions_by_type(self, sync_type: str, limit: int = 50) -> list[SyncSession]:
        """根据类型获取会话列表.

        Args:
            sync_type: 同步类型,如 'manual_single'、'manual_batch'.
            limit: 限制数量,默认为 50.

        Returns:
            会话列表,查询失败时返回空列表.

        """
        try:
            return self._repository.list_sessions_by_type(sync_type, limit=limit)
        except Exception as e:
            self.sync_logger.exception(
                "获取类型会话列表失败",
                module="sync_session",
                action="get_sessions_by_type",
                sync_type=sync_type,
                fallback=True,
                fallback_reason="sync_sessions_list_by_type_failed",
                error=str(e),
            )
            return []

    def get_sessions_by_category(self, sync_category: str, limit: int = 50) -> list[SyncSession]:
        """根据分类获取会话列表.

        Args:
            sync_category: 同步分类,如 'account'、'capacity'.
            limit: 限制数量,默认为 50.

        Returns:
            会话列表,查询失败时返回空列表.

        """
        try:
            return self._repository.list_sessions_by_category(sync_category, limit=limit)
        except Exception as e:
            self.sync_logger.exception(
                "获取分类会话列表失败",
                module="sync_session",
                action="get_sessions_by_category",
                sync_category=sync_category,
                fallback=True,
                fallback_reason="sync_sessions_list_by_category_failed",
                error=str(e),
            )
            return []

    def get_recent_sessions(self, limit: int = 20) -> list[SyncSession]:
        """获取最近的会话列表.

        按创建时间降序返回会话列表.

        Args:
            limit: 限制数量,默认为 20.

        Returns:
            会话列表,查询失败时返回空列表.

        """
        try:
            return self._repository.list_recent_sessions(limit)
        except Exception as e:
            self.sync_logger.exception(
                "获取最近会话列表失败",
                module="sync_session",
                action="get_recent_sessions",
                limit=limit,
                fallback=True,
                fallback_reason="sync_sessions_list_recent_failed",
                error=str(e),
            )
            return []

    def cancel_session(self, session_id: str) -> bool:
        """取消会话.

        将运行中的会话标记为已取消状态.

        Args:
            session_id: 会话 ID.

        Returns:
            成功返回 True; 会话不存在/非 RUNNING 返回 False; DB 异常抛出.

        """
        session = self._repository.get_session_by_session_id(session_id)
        if not session:
            return False
        if session.status != SyncSessionStatus.RUNNING:
            return False

        try:
            with db.session.begin_nested():
                session.status = SyncSessionStatus.CANCELLED
                session.completed_at = time_utils.now()
                session.updated_at = time_utils.now()
                self._repository.flush()

            self.sync_logger.info("取消同步会话", module="sync_session", session_id=session_id)
        except Exception as exc:
            self.sync_logger.exception(
                "取消同步会话失败",
                module="sync_session",
                session_id=session_id,
                error=str(exc),
            )
            raise
        else:
            return True


# 创建全局服务实例
sync_session_service = SyncSessionService()
