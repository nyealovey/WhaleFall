"""表容量统计 Repository.

职责:
- 封装 DatabaseTableSizeStat 的 upsert 与清理逻辑
- 不做业务编排、不返回 Response、不 commit
"""

from __future__ import annotations

from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app import db
from app.models.database_table_size_stat import DatabaseTableSizeStat


class DatabaseTableSizeStatsRepository:
    """表容量统计 Repository."""

    @staticmethod
    def upsert_latest_snapshot(records: list[dict[str, object]], *, current_utc: object) -> None:
        """Upsert 最新快照."""
        if not records:
            return

        dialect = getattr(getattr(db.session, "bind", None), "dialect", None)
        dialect_name = getattr(dialect, "name", "")

        if dialect_name == "sqlite":
            insert_stmt = sqlite_insert(DatabaseTableSizeStat).values(records)
        else:
            insert_stmt = pg_insert(DatabaseTableSizeStat).values(records)

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                DatabaseTableSizeStat.instance_id,
                DatabaseTableSizeStat.database_name,
                DatabaseTableSizeStat.schema_name,
                DatabaseTableSizeStat.table_name,
            ],
            set_={
                "size_mb": insert_stmt.excluded.size_mb,
                "data_size_mb": insert_stmt.excluded.data_size_mb,
                "index_size_mb": insert_stmt.excluded.index_size_mb,
                "row_count": insert_stmt.excluded.row_count,
                "collected_at": insert_stmt.excluded.collected_at,
                "updated_at": current_utc,
            },
        )

        with db.session.begin_nested():
            db.session.execute(stmt)
            db.session.flush()

    @staticmethod
    def cleanup_removed(
        *,
        instance_id: int,
        database_name: str,
        keys: list[tuple[str, str]],
    ) -> int:
        """删除不在 keys 中的旧快照记录,返回删除数量."""
        query = DatabaseTableSizeStat.query.filter(
            DatabaseTableSizeStat.instance_id == instance_id,
            DatabaseTableSizeStat.database_name == database_name,
        )

        if keys:
            query = query.filter(
                tuple_(DatabaseTableSizeStat.schema_name, DatabaseTableSizeStat.table_name).notin_(keys),
            )

        with db.session.begin_nested():
            deleted_count = query.delete(synchronize_session=False)
            db.session.flush()

        return int(deleted_count)
