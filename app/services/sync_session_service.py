"""
鲸落 - 同步会话服务
管理同步会话和实例记录的业务逻辑
"""

from typing import Any

from app import db
from app.models.instance import Instance
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.utils.structlog_config import get_sync_logger, get_system_logger
from app.utils.time_utils import time_utils


class SyncSessionService:
    """同步会话服务 - 管理批量同步会话"""

    def __init__(self):
        self.system_logger = get_system_logger()
        self.sync_logger = get_sync_logger()

    def create_session(self, sync_type: str, sync_category: str = "account", created_by: int = None) -> SyncSession:
        """
        创建同步会话

        Args:
            sync_type: 同步类型 ('manual_single', 'manual_batch', 'manual_task', 'scheduled_task')
            sync_category: 同步分类 ('account', 'capacity', 'config', 'other')
            created_by: 创建用户ID

        Returns:
            SyncSession: 创建的同步会话
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

    def add_instance_records(self, session_id: str, instance_ids: list[int]) -> list[SyncInstanceRecord]:
        """
        为会话添加实例记录

        Args:
            session_id: 会话ID
            instance_ids: 实例ID列表

        Returns:
            List[SyncInstanceRecord]: 创建的实例记录列表
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
                        sync_category="account",  # 默认账户同步
                    )
                    db.session.add(record)
                    records.append(record)

            db.session.commit()

            self.sync_logger.info(
                "添加实例记录",
                module="sync_session",
                session_id=session_id,
                instance_count=len(records),
            )

            return records
        except Exception as e:
            db.session.rollback()
            self.sync_logger.error(
                "添加实例记录失败",
                module="sync_session",
                session_id=session_id,
                error=str(e),
            )
            raise

    def start_instance_sync(self, record_id: int) -> bool:
        """
        开始实例同步

        Args:
            record_id: 实例记录ID

        Returns:
            bool: 是否成功开始
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
        accounts_synced: int = 0,
        accounts_created: int = 0,
        accounts_updated: int = 0,
        accounts_deleted: int = 0,
        sync_details: dict[str, Any] = None,
    ) -> bool:
        """
        完成实例同步

        Args:
            record_id: 实例记录ID
            accounts_synced: 同步的账户总数
            accounts_created: 新增的账户数量
            accounts_updated: 更新的账户数量
            accounts_deleted: 删除的账户数量
            sync_details: 同步详情

        Returns:
            bool: 是否成功完成
        """
        try:
            record = SyncInstanceRecord.query.get(record_id)
            if not record:
                return False

            record.complete_sync(
                accounts_synced=accounts_synced,
                accounts_created=accounts_created,
                accounts_updated=accounts_updated,
                accounts_deleted=accounts_deleted,
                sync_details=sync_details,
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
                accounts_synced=accounts_synced,
                accounts_created=accounts_created,
                accounts_updated=accounts_updated,
                accounts_deleted=accounts_deleted,
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
        """
        标记实例同步失败

        Args:
            record_id: 实例记录ID
            error_message: 错误信息
            sync_details: 同步详情

        Returns:
            bool: 是否成功标记
        """
        try:
            record = SyncInstanceRecord.query.get(record_id)
            if not record:
                return False

            record.fail_sync(error_message=error_message, sync_details=sync_details)
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

    def _update_session_statistics(self, session_id: str):
        """更新会话统计信息"""
        try:
            session = SyncSession.query.filter_by(session_id=session_id).first()
            if session:
                session.update_statistics()
                db.session.commit()
        except Exception as e:
            self.sync_logger.error(
                "更新会话统计失败",
                module="sync_session",
                session_id=session_id,
                error=str(e),
            )

    def get_session_records(self, session_id: str) -> list[SyncInstanceRecord]:
        """
        获取会话的所有实例记录

        Args:
            session_id: 会话ID

        Returns:
            List[SyncInstanceRecord]: 实例记录列表
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
        """
        根据ID获取会话

        Args:
            session_id: 会话ID

        Returns:
            Optional[SyncSession]: 会话对象
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
        """
        根据类型获取会话列表

        Args:
            sync_type: 同步类型
            limit: 限制数量

        Returns:
            List[SyncSession]: 会话列表
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
        """
        根据分类获取会话列表

        Args:
            sync_category: 同步分类
            limit: 限制数量

        Returns:
            List[SyncSession]: 会话列表
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
        """
        获取最近的会话列表

        Args:
            limit: 限制数量

        Returns:
            List[SyncSession]: 会话列表
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
        """
        取消会话

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否成功取消
        """
        try:
            session = SyncSession.query.filter_by(session_id=session_id).first()
            if not session:
                return False

            if session.status == "running":
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
