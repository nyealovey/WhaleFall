"""实例统计 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any

from app import db
from app.models.instance import Instance


class InstanceStatisticsRepository:
    """实例统计读模型 Repository."""

    @staticmethod
    def fetch_summary(*, db_type: str | None = None) -> dict[str, int]:
        """获取实例统计摘要."""
        query = Instance.query
        if db_type:
            query = query.filter(Instance.db_type == db_type)

        total_instances = query.count()

        existing_query = query.filter(Instance.deleted_at.is_(None))
        existing_instances = existing_query.count()
        active_instances = existing_query.filter(Instance.is_active.is_(True)).count()
        disabled_instances = max(existing_instances - active_instances, 0)
        deleted_instances = max(total_instances - existing_instances, 0)
        normal_instances = active_instances

        return {
            "total_instances": total_instances,
            "active_instances": active_instances,
            "normal_instances": normal_instances,
            "disabled_instances": disabled_instances,
            "deleted_instances": deleted_instances,
        }

    @staticmethod
    def fetch_db_type_stats() -> list[Any]:
        """获取实例按数据库类型统计."""
        return (
            db.session.query(Instance.db_type, db.func.count(Instance.id).label("count"))
            .group_by(Instance.db_type)
            .all()
        )

    @staticmethod
    def fetch_port_stats(limit: int = 10) -> list[Any]:
        """获取实例按端口统计."""
        return (
            db.session.query(Instance.port, db.func.count(Instance.id).label("count"))
            .group_by(Instance.port)
            .order_by(db.func.count(Instance.id).desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def fetch_version_stats() -> list[Any]:
        """获取实例按版本统计."""
        return (
            db.session.query(
                Instance.db_type,
                Instance.main_version,
                db.func.count(Instance.id).label("count"),
            )
            .group_by(Instance.db_type, Instance.main_version)
            .all()
        )
