"""同步会话与实例记录 Repository.

职责:
- 仅负责 Query 组装与数据库读写(add/flush/select/count)
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from sqlalchemy import func

from app import db
from app.models.instance import Instance
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession


class SyncSessionsRepository:
    """同步会话与实例记录仓库."""

    @staticmethod
    def list_instances_by_ids(instance_ids: list[int]) -> list[Instance]:
        """按 ID 列表获取实例."""
        return Instance.query.filter(Instance.id.in_(instance_ids)).all()

    @staticmethod
    def get_record_by_id(record_id: int) -> SyncInstanceRecord | None:
        """按 ID 获取实例同步记录(可为空)."""
        return SyncInstanceRecord.query.get(record_id)

    @staticmethod
    def list_records_by_session(session_id: str) -> list[SyncInstanceRecord]:
        """按会话 ID 获取实例记录列表."""
        return SyncInstanceRecord.get_records_by_session(session_id)

    @staticmethod
    def get_session_by_session_id(session_id: str) -> SyncSession | None:
        """按 session_id 获取会话(可为空)."""
        return SyncSession.query.filter_by(session_id=session_id).first()

    @staticmethod
    def list_recent_sessions(limit: int) -> list[SyncSession]:
        """获取最近的会话列表."""
        return SyncSession.query.order_by(SyncSession.created_at.desc()).limit(limit).all()

    @staticmethod
    def list_sessions_by_type(sync_type: str, *, limit: int) -> list[SyncSession]:
        """按 sync_type 获取会话列表."""
        return SyncSession.query.filter_by(sync_type=sync_type).order_by(SyncSession.created_at.desc()).limit(limit).all()

    @staticmethod
    def list_sessions_by_category(sync_category: str, *, limit: int) -> list[SyncSession]:
        """按 sync_category 获取会话列表."""
        return (
            SyncSession.query.filter_by(sync_category=sync_category)
            .order_by(SyncSession.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def lock_session_by_session_id(session_id: str) -> SyncSession:
        """锁定并获取会话(用于统计更新)."""
        return db.session.query(SyncSession).filter_by(session_id=session_id).with_for_update().one()

    @staticmethod
    def count_records_by_status(*, session_id: str, status: str) -> int:
        """统计会话中某状态的实例记录数."""
        return int(
            (
                db.session.query(func.count(SyncInstanceRecord.id))
                .filter_by(session_id=session_id, status=status)
                .scalar()
            )
            or 0,
        )

    @staticmethod
    def add_session(session: SyncSession) -> SyncSession:
        """新增同步会话并 flush."""
        db.session.add(session)
        db.session.flush()
        return session

    @staticmethod
    def add_records(records: list[SyncInstanceRecord]) -> list[SyncInstanceRecord]:
        """批量新增实例记录并 flush."""
        normalized = list(records or [])
        if not normalized:
            return []
        db.session.add_all(normalized)
        db.session.flush()
        return normalized

    @staticmethod
    def flush() -> None:
        """显式 flush,用于更新已存在对象的状态变更."""
        db.session.flush()
