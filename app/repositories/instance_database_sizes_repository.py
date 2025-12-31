"""实例详情-数据库容量(大小) Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, cast

from sqlalchemy import func, or_
from sqlalchemy.sql.elements import ColumnElement

from app import db
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance_database import InstanceDatabase
from app.types.instance_database_sizes import (
    InstanceDatabaseSizeEntry,
    InstanceDatabaseSizesHistoryResult,
    InstanceDatabaseSizesLatestResult,
    InstanceDatabaseSizesQuery,
)


class InstanceDatabaseSizesRepository:
    """实例数据库容量读模型 Repository."""

    @staticmethod
    def _build_capacity_query(options: InstanceDatabaseSizesQuery) -> Any:
        query = (
            db.session.query(
                DatabaseSizeStat,
                InstanceDatabase.is_active,
                InstanceDatabase.deleted_at,
                InstanceDatabase.last_seen_date,
            )
            .outerjoin(
                InstanceDatabase,
                (DatabaseSizeStat.instance_id == InstanceDatabase.instance_id)
                & (DatabaseSizeStat.database_name == InstanceDatabase.database_name),
            )
            .filter(DatabaseSizeStat.instance_id == options.instance_id)
        )

        if options.database_name:
            query = query.filter(DatabaseSizeStat.database_name.ilike(f"%{options.database_name}%"))

        if options.start_date:
            query = query.filter(DatabaseSizeStat.collected_date >= options.start_date)

        if options.end_date:
            query = query.filter(DatabaseSizeStat.collected_date <= options.end_date)

        return query

    @staticmethod
    def _normalize_active_flag(flag: bool | None) -> bool:
        return True if flag is None else bool(flag)

    @staticmethod
    def _to_entry(
        stat: DatabaseSizeStat,
        *,
        is_active: bool,
        deleted_at: datetime | None,
        last_seen_date: date | None,
    ) -> InstanceDatabaseSizeEntry:
        collected_date = stat.collected_date if not isinstance(stat.collected_date, ColumnElement) else None
        collected_at = stat.collected_at if not isinstance(stat.collected_at, ColumnElement) else None

        return InstanceDatabaseSizeEntry(
            id=cast("int | None", getattr(stat, "id", None)),
            database_name=cast(str, getattr(stat, "database_name", "")),
            size_mb=cast("int | float | None", getattr(stat, "size_mb", None)),
            data_size_mb=cast("int | float | None", getattr(stat, "data_size_mb", None)),
            log_size_mb=cast("int | float | None", getattr(stat, "log_size_mb", None)),
            collected_date=collected_date.isoformat() if collected_date else None,
            collected_at=collected_at.isoformat() if collected_at else None,
            is_active=is_active,
            deleted_at=deleted_at.isoformat() if deleted_at else None,
            last_seen_date=last_seen_date.isoformat() if last_seen_date else None,
        )

    def fetch_latest(self, options: InstanceDatabaseSizesQuery) -> InstanceDatabaseSizesLatestResult:
        query = self._build_capacity_query(options)

        if not options.include_inactive:
            query = query.filter(
                or_(
                    InstanceDatabase.is_active.is_(True),
                    InstanceDatabase.is_active.is_(None),
                ),
            )

        name_key = func.lower(DatabaseSizeStat.database_name)
        ranked = (
            query.with_entities(
                DatabaseSizeStat.id.label("stat_id"),
                DatabaseSizeStat.database_name.label("database_name"),
                func.row_number()
                .over(
                    partition_by=name_key,
                    order_by=(DatabaseSizeStat.collected_date.desc(), DatabaseSizeStat.collected_at.desc()),
                )
                .label("rn"),
                InstanceDatabase.is_active.label("is_active"),
                InstanceDatabase.deleted_at.label("deleted_at"),
                InstanceDatabase.last_seen_date.label("last_seen_date"),
            )
        ).subquery()

        records = (
            db.session.query(
                DatabaseSizeStat,
                ranked.c.is_active,
                ranked.c.deleted_at,
                ranked.c.last_seen_date,
            )
            .join(ranked, DatabaseSizeStat.id == ranked.c.stat_id)
            .filter(ranked.c.rn == 1)
            .order_by(ranked.c.database_name.asc())
            .all()
        )

        latest: list[tuple[DatabaseSizeStat, bool, datetime | None, date | None]] = []
        seen: set[str] = set()

        for stat, is_active_flag, deleted_at, last_seen_date in records:
            normalized_active = self._normalize_active_flag(cast(bool | None, is_active_flag))
            latest.append(
                (stat, normalized_active, cast(datetime | None, deleted_at), cast(date | None, last_seen_date))
            )
            seen.add(stat.database_name.lower())

        include_placeholder_inactive = options.include_inactive or not latest

        if include_placeholder_inactive:
            inactive_query = InstanceDatabase.query.filter(
                InstanceDatabase.instance_id == options.instance_id,
                cast(ColumnElement[bool], InstanceDatabase.is_active).is_(False),
            )
            if options.database_name:
                inactive_query = inactive_query.filter(
                    InstanceDatabase.database_name.ilike(f"%{options.database_name}%"),
                )

            for instance_db in inactive_query:
                if not instance_db.database_name:
                    continue
                key = instance_db.database_name.lower()
                if key in seen:
                    continue
                placeholder_stat = SimpleNamespace(
                    id=None,
                    instance_id=instance_db.instance_id,
                    database_name=instance_db.database_name,
                    size_mb=0,
                    data_size_mb=None,
                    log_size_mb=None,
                    collected_date=None,
                    collected_at=None,
                )
                latest.append(
                    (
                        cast(DatabaseSizeStat, placeholder_stat),
                        False,
                        instance_db.deleted_at,
                        instance_db.last_seen_date,
                    ),
                )
                seen.add(key)

        latest.sort(
            key=lambda item: (
                -(float(getattr(item[0], "size_mb", 0) or 0)),
                str(getattr(item[0], "database_name", "") or "").lower(),
            ),
        )

        total = len(latest)
        filtered_count = sum(1 for _, active, _, _ in latest if not active)
        total_size_mb = sum((cast(Any, stat).size_mb or 0) for stat, active, _, _ in latest if active)

        paged = latest[options.offset : options.offset + options.limit]
        databases = [
            self._to_entry(
                stat,
                is_active=active,
                deleted_at=deleted_at,
                last_seen_date=last_seen_date,
            )
            for stat, active, deleted_at, last_seen_date in paged
        ]

        return InstanceDatabaseSizesLatestResult(
            total=total,
            limit=options.limit,
            offset=options.offset,
            active_count=total - filtered_count,
            filtered_count=filtered_count,
            total_size_mb=total_size_mb,
            databases=databases,
        )

    def fetch_history(self, options: InstanceDatabaseSizesQuery) -> InstanceDatabaseSizesHistoryResult:
        query = self._build_capacity_query(options)

        if not options.include_inactive:
            query = query.filter(
                or_(
                    InstanceDatabase.is_active.is_(True),
                    InstanceDatabase.is_active.is_(None),
                ),
            )

        total = query.count()
        rows = (
            query.order_by(DatabaseSizeStat.collected_date.desc(), DatabaseSizeStat.database_name.asc())
            .offset(options.offset)
            .limit(options.limit)
            .all()
        )

        databases = [
            self._to_entry(
                stat,
                is_active=self._normalize_active_flag(cast(bool | None, is_active_flag)),
                deleted_at=cast(datetime | None, deleted_at),
                last_seen_date=cast(date | None, last_seen_date),
            )
            for stat, is_active_flag, deleted_at, last_seen_date in rows
        ]

        return InstanceDatabaseSizesHistoryResult(
            total=total,
            limit=options.limit,
            offset=options.offset,
            databases=databases,
        )
