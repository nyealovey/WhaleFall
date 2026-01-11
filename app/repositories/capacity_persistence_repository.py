"""容量采集持久化 Repository.

职责:
- 封装容量采集相关的 upsert/query 细节
- 不做业务编排、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import or_, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import db
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance_database import InstanceDatabase
from app.models.instance_size_stat import InstanceSizeStat


class CapacityPersistenceRepository:
    """容量采集持久化 Repository."""

    @staticmethod
    def upsert_database_size_stats(records: list[dict[str, Any]], *, current_utc: object) -> None:
        """批量 upsert 数据库容量统计."""
        if not records:
            return

        insert_stmt = pg_insert(DatabaseSizeStat).values(records)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                DatabaseSizeStat.instance_id,
                DatabaseSizeStat.database_name,
                DatabaseSizeStat.collected_date,
            ],
            set_={
                "size_mb": insert_stmt.excluded.size_mb,
                "data_size_mb": insert_stmt.excluded.data_size_mb,
                "log_size_mb": insert_stmt.excluded.log_size_mb,
                "collected_at": insert_stmt.excluded.collected_at,
                "updated_at": current_utc,
            },
        )

        with db.session.begin_nested():
            db.session.execute(upsert_stmt)
            db.session.flush()

    @staticmethod
    def upsert_instance_size_stat(payload: dict[str, Any], *, current_utc: object) -> None:
        """Upsert 实例总体容量统计(按 instance_id + collected_date)."""
        insert_stmt = pg_insert(InstanceSizeStat).values(payload)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                InstanceSizeStat.instance_id,
                InstanceSizeStat.collected_date,
            ],
            index_where=text("is_deleted = false"),
            set_={
                "total_size_mb": insert_stmt.excluded.total_size_mb,
                "database_count": insert_stmt.excluded.database_count,
                "collected_at": insert_stmt.excluded.collected_at,
                "updated_at": insert_stmt.excluded.updated_at,
                "is_deleted": False,
                "deleted_at": None,
            },
        )

        with db.session.begin_nested():
            db.session.execute(upsert_stmt)
            db.session.flush()

    @staticmethod
    def list_database_size_stats_for_instance_date(*, instance_id: int, collected_date: date) -> list[DatabaseSizeStat]:
        """查询指定实例在某天的数据库容量统计(过滤非活跃库)."""
        return (
            DatabaseSizeStat.query.outerjoin(
                InstanceDatabase,
                (InstanceDatabase.instance_id == DatabaseSizeStat.instance_id)
                & (InstanceDatabase.database_name == DatabaseSizeStat.database_name),
            )
            .filter(
                DatabaseSizeStat.instance_id == instance_id,
                DatabaseSizeStat.collected_date == collected_date,
                or_(
                    InstanceDatabase.is_active.is_(True),
                    InstanceDatabase.is_active.is_(None),
                ),
            )
            .all()
        )

