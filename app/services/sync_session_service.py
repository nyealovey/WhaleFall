"""
鲸落 - 同步会话服务
管理同步会话和实例记录的业务逻辑
"""

from typing import Any
from datetime import date

from sqlalchemy import func

from app import db
from app.models.instance import Instance
from app.constants import SyncStatus
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.utils.structlog_config import get_sync_logger, get_system_logger
from app.utils.time_utils import time_utils


class SyncSessionService:
    """同步会话服务。

    管理批量同步会话和实例记录的业务逻辑，包括会话创建、实例记录管理、
    同步状态更新和统计信息维护。

    Attributes:
        system_logger: 系统日志记录器。
        sync_logger: 同步日志记录器。
    """

    def __init__(self):
        self.system_logger = get_system_logger()
        self.sync_logger = get_sync_logger()

    def _clean_sync_details(self, sync_details: dict[str, Any] | None) -> dict[str, Any] | None:
        """清理同步详情中的 datetime 对象，确保 JSON 可序列化。

        递归遍历同步详情字典，将所有 datetime 和 date 对象转换为 ISO 8601 格式字符串。

        Args:
            sync_details: 原始同步详情字典，可能包含 datetime 对象。

        Returns:
            清理后的同步详情字典，所有 datetime 对象已转换为字符串。
            如果输入为 None，则返回 None。
        """
        if not sync_details:
            return None
            
        def clean_value(value):
            if hasattr(value, 'isoformat'):  # datetime 或 date 对象
                return value.isoformat()
            elif isinstance(value, dict):
                return {k: clean_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [clean_value(item) for item in value]
            else:
                return value
        
        return clean_value(sync_details)

    def create_session(self, sync_type: str, sync_category: str = "account", created_by: int = None) -> SyncSession:
        """创建同步会话。

        创建新的同步会话记录，并记录日志。

        Args:
            sync_type: 同步操作方式，可选值：'manual_single'（手动单个）、
                'manual_batch'（手动批量）、'manual_task'（手动任务）、
                'scheduled_task'（定时任务）。
            sync_category: 同步分类，可选值：'account'（账户）、'capacity'（容量）、
                'config'（配置）、'aggregation'（聚合）、'other'（其他），默认为 'account'。
            created_by: 创建用户 ID，可选。

        Returns:
            创建的同步会话对象。

        Raises:
            Exception: 当数据库操作失败时抛出。
        """
        try:
            session = SyncSession(sync_type=sync_type, sync_category=sync_category, created_by=created_by)
            db.session.add(session)
            db.session.commit()

            self.sync_logger.info(
                "创建同步会话",
                module="sync_session",
                session_id=session.session_id,
                sync_type=sync_type,
                sync_category=sync_category,
                created_by=created_by,
            )

            return session
        except Exception as e:
            db.session.rollback()
            self.sync_logger.error(
                "创建同步会话失败",
                module="sync_session",
                sync_type=sync_type,
                sync_category=sync_category,
                error=str(e),
            )
            raise

    def add_instance_records(self, session_id: str, instance_ids: list[int], sync_category: str = "account") -> list[SyncInstanceRecord]:
        """为会话添加实例记录。

        根据实例 ID 列表批量创建实例同步记录，并关联到指定会话。

        Args:
            session_id: 会话 ID。
            instance_ids: 实例 ID 列表。
            sync_category: 同步分类，可选值：'account'、'capacity'、'config'、
                'aggregation'、'other'，默认为 'account'。

        Returns:
            创建的实例记录列表。

        Raises:
            Exception: 当数据库操作失败时抛出。
        """
        try:
            records = []
            instances = Instance.query.filter(Instance.id.in_(instance_ids)).all()
            instance_dict = {inst.id: inst for inst in instances}

            for instance_id in instance_ids:
                instance = instance_dict.get(instance_id)
                if instance:
                    record = SyncInstanceRecord(
                        session_id=session_id,
                        instance_id=instance_id,
                        instance_name=instance.name,
                        sync_category=sync_category,  # 使用传入的同步分类
                    )
                    db.session.add(record)
                    records.append(record)

            db.session.commit()

            self.sync_logger.info(
                "添加实例记录",
                module="sync_session",
                session_id=session_id,
                instance_count=len(records),
                sync_category=sync_category,
            )

            return records
        except Exception as e:
            db.session.rollback()
            self.sync_logger.error(
                "添加实例记录失败",
                module="sync_session",
                session_id=session_id,
                sync_category=sync_category,
                error=str(e),
            )
            raise

    def start_instance_sync(self, record_id: int) -> bool:
        """开始实例同步。

        将实例记录状态标记为同步中，并记录开始时间。

        Args:
            record_id: 实例记录 ID。

        Returns:
            成功返回 True，失败或记录不存在返回 False。
        """
        try:
            record = SyncInstanceRecord.query.get(record_id)
            if not record:
                return False

            record.start_sync()
            db.session.commit()

            self.sync_logger.info(
                "开始实例同步",
                module="sync_session",
                session_id=record.session_id,
                instance_id=record.instance_id,
                instance_name=record.instance_name,
            )

            return True
        except Exception as e:
            db.session.rollback()
            self.sync_logger.error(
                "开始实例同步失败",
                module="sync_session",
                record_id=record_id,
                error=str(e),
            )
            return False

    def complete_instance_sync(
        self,
        record_id: int,
        items_synced: int = 0,
        items_created: int = 0,
        items_updated: int = 0,
        items_deleted: int = 0,
        sync_details: dict[str, Any] = None,
    ) -> bool:
        """完成实例同步。

        将实例记录标记为完成状态，记录同步统计信息，并更新会话统计。

        Args:
            record_id: 实例记录 ID。
            items_synced: 同步的项目总数，默认为 0。
            items_created: 新增的项目数量，默认为 0。
            items_updated: 更新的项目数量，默认为 0。
            items_deleted: 删除的项目数量，默认为 0。
            sync_details: 同步详情字典，可选。

        Returns:
            成功返回 True，失败或记录不存在返回 False。
        """
        try:
            record = SyncInstanceRecord.query.get(record_id)
            if not record:
                return False

            record.complete_sync(
                items_synced=items_synced,
                items_created=items_created,
                items_updated=items_updated,
                items_deleted=items_deleted,
                sync_details=self._clean_sync_details(sync_details),
            )
            db.session.commit()

            # 更新会话统计
            self._update_session_statistics(record.session_id)

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

            return True
        except Exception as e:
            db.session.rollback()
            self.sync_logger.error(
                "完成实例同步失败",
                module="sync_session",
                record_id=record_id,
                error=str(e),
            )
            return False

    def fail_instance_sync(self, record_id: int, error_message: str, sync_details: dict[str, Any] = None) -> bool:
        """标记实例同步失败。

        将实例记录标记为失败状态，记录错误信息，并更新会话统计。

        Args:
            record_id: 实例记录 ID。
            error_message: 错误信息描述。
            sync_details: 同步详情字典，可选。

        Returns:
            成功返回 True，失败或记录不存在返回 False。
        """
        try:
            record = SyncInstanceRecord.query.get(record_id)
            if not record:
                return False

            record.fail_sync(error_message=error_message, sync_details=self._clean_sync_details(sync_details))
            db.session.commit()

            # 更新会话统计
            self._update_session_statistics(record.session_id)

            self.sync_logger.error(
                "实例同步失败",
                module="sync_session",
                session_id=record.session_id,
                instance_id=record.instance_id,
                instance_name=record.instance_name,
                error_message=error_message,
            )

            return True
        except Exception as e:
            db.session.rollback()
            self.sync_logger.error(
                "标记实例同步失败时出错",
                module="sync_session",
                record_id=record_id,
                error=str(e),
            )
            return False

    def _update_session_statistics(self, session_id: str) -> None:
        """更新会话统计信息。

        统计会话中成功和失败的实例数量，并更新会话对象。

        Args:
            session_id: 会话 ID。

        Returns:
            None: 统计更新完成后返回。

        Raises:
            Exception: 当数据库操作失败时抛出。
        """
        try:
            session = db.session.query(SyncSession).filter_by(session_id=session_id).with_for_update().one()
            
            succeeded_instances = (
                db.session.query(func.count(SyncInstanceRecord.id))
                .filter_by(session_id=session_id, status="completed")
                .scalar()
            )
            
            failed_instances = (
                db.session.query(func.count(SyncInstanceRecord.id))
                .filter_by(session_id=session_id, status="failed")
                .scalar()
            )

            session.update_statistics(
                succeeded_instances=succeeded_instances,
                failed_instances=failed_instances,
            )
            
            # 提交事务
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            self.sync_logger.error(
                "更新会话统计失败",
                module="sync_session",
                session_id=session_id,
                error=str(e),
            )
            raise

    def get_session_records(self, session_id: str) -> list[SyncInstanceRecord]:
        """获取会话的所有实例记录。

        Args:
            session_id: 会话 ID。

        Returns:
            实例记录列表，查询失败时返回空列表。
        """
        try:
            return SyncInstanceRecord.get_records_by_session(session_id)
        except Exception as e:
            self.sync_logger.error(
                "获取会话记录失败",
                module="sync_session",
                session_id=session_id,
                error=str(e),
            )
            return []

    def get_session_by_id(self, session_id: str) -> SyncSession | None:
        """根据 ID 获取会话。

        Args:
            session_id: 会话 ID。

        Returns:
            会话对象，不存在或查询失败时返回 None。
        """
        try:
            return SyncSession.query.filter_by(session_id=session_id).first()
        except Exception as e:
            self.sync_logger.error(
                "获取会话失败",
                module="sync_session",
                session_id=session_id,
                error=str(e),
            )
            return None

    def get_sessions_by_type(self, sync_type: str, limit: int = 50) -> list[SyncSession]:
        """根据类型获取会话列表。

        Args:
            sync_type: 同步类型，如 'manual_single'、'manual_batch'。
            limit: 限制数量，默认为 50。

        Returns:
            会话列表，查询失败时返回空列表。
        """
        try:
            return SyncSession.get_sessions_by_type(sync_type, limit)
        except Exception as e:
            self.sync_logger.error(
                "获取类型会话列表失败",
                module="sync_session",
                sync_type=sync_type,
                error=str(e),
            )
            return []

    def get_sessions_by_category(self, sync_category: str, limit: int = 50) -> list[SyncSession]:
        """根据分类获取会话列表。

        Args:
            sync_category: 同步分类，如 'account'、'capacity'。
            limit: 限制数量，默认为 50。

        Returns:
            会话列表，查询失败时返回空列表。
        """
        try:
            return SyncSession.get_sessions_by_category(sync_category, limit)
        except Exception as e:
            self.sync_logger.error(
                "获取分类会话列表失败",
                module="sync_session",
                sync_category=sync_category,
                error=str(e),
            )
            return []

    def get_recent_sessions(self, limit: int = 20) -> list[SyncSession]:
        """获取最近的会话列表。

        按创建时间降序返回会话列表。

        Args:
            limit: 限制数量，默认为 20。

        Returns:
            会话列表，查询失败时返回空列表。
        """
        try:
            return SyncSession.query.order_by(SyncSession.created_at.desc()).limit(limit).all()
        except Exception as e:
            self.sync_logger.error(
                "获取最近会话列表失败",
                module="sync_session",
                limit=limit,
                error=str(e),
            )
            return []

    def cancel_session(self, session_id: str) -> bool:
        """取消会话。

        将运行中的会话标记为已取消状态。

        Args:
            session_id: 会话 ID。

        Returns:
            成功返回 True，失败或会话不存在返回 False。
        """
        try:
            session = SyncSession.query.filter_by(session_id=session_id).first()
            if not session:
                return False

            if session.status == SyncStatus.RUNNING:
                session.status = "cancelled"
                session.completed_at = time_utils.now()
                session.updated_at = time_utils.now()
                db.session.commit()

                self.sync_logger.info("取消同步会话", module="sync_session", session_id=session_id)

            return True
        except Exception as e:
            db.session.rollback()
            self.sync_logger.error(
                "取消同步会话失败",
                module="sync_session",
                session_id=session_id,
                error=str(e),
            )
            return False


# 创建全局服务实例
sync_session_service = SyncSessionService()
