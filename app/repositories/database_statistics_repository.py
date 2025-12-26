"""数据库统计 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from app import db
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase


class DatabaseStatisticsRepository:
    """数据库统计读模型 Repository."""

    @staticmethod
    def fetch_summary(*, instance_id: int | None = None) -> dict[str, int]:
        query = InstanceDatabase.query.join(Instance, Instance.id == InstanceDatabase.instance_id).filter(
            Instance.is_active.is_(True),
            Instance.deleted_at.is_(None),
        )

        if instance_id is not None:
            query = query.filter(InstanceDatabase.instance_id == instance_id)

        total_databases = int(query.count() or 0)
        active_databases = int(query.filter(InstanceDatabase.is_active.is_(True)).count() or 0)
        inactive_databases = max(total_databases - active_databases, 0)

        deleted_query = (
            db.session.query(db.func.count(InstanceDatabase.id))
            .join(Instance, Instance.id == InstanceDatabase.instance_id)
            .filter(Instance.deleted_at.isnot(None))
        )
        if instance_id is not None:
            deleted_query = deleted_query.filter(InstanceDatabase.instance_id == instance_id)
        deleted_databases = int(deleted_query.scalar() or 0)

        return {
            "total_databases": total_databases,
            "active_databases": active_databases,
            "inactive_databases": inactive_databases,
            "deleted_databases": deleted_databases,
        }

