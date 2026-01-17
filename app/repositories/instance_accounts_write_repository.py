"""实例账户写模型 Repository.

职责:
- 负责 InstanceAccount 的写入(add/flush)(不 commit)
- 不做业务编排、不返回 Response、不做序列化
"""

from __future__ import annotations

from app import db
from app.models.instance_account import InstanceAccount


class InstanceAccountsWriteRepository:
    """InstanceAccount 写入仓储."""

    @staticmethod
    def add(record: InstanceAccount) -> InstanceAccount:
        """新增/保存账户记录(不 commit)."""
        db.session.add(record)
        return record

    @staticmethod
    def flush() -> None:
        """显式 flush,用于增量同步批量更新."""
        db.session.flush()
