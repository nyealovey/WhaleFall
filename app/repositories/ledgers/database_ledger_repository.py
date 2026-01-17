"""数据库台账 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import ceil
from typing import Any, cast

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Query, Session
from sqlalchemy.orm.scoping import scoped_session

from app import db
from app.core.types.ledgers import DatabaseLedgerFilters, DatabaseLedgerRowProjection
from app.core.types.listing import PaginatedResult
from app.core.types.tags import TagSummary
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.models.tag import Tag, instance_tags

SessionLike = Session | scoped_session[Any]


class DatabaseLedgerRepository:
    """数据库台账查询 Repository."""

    def __init__(self, *, session: SessionLike | None = None) -> None:
        """初始化仓库并注入 SQLAlchemy session."""
        self._session = session or db.session

    @staticmethod
    def _to_row_projection(
        record: InstanceDatabase,
        instance: Instance | None,
        collected_at: datetime | None,
        size_mb: Any,
        *,
        tags_map: dict[int, list[TagSummary]],
    ) -> DatabaseLedgerRowProjection:
        instance_id = instance.id if instance else 0
        return DatabaseLedgerRowProjection(
            id=record.id,
            database_name=record.database_name,
            instance_id=instance_id,
            instance_name=instance.name if instance else "",
            instance_host=instance.host if instance else "",
            db_type=instance.db_type if instance else "",
            collected_at=collected_at,
            size_mb=int(size_mb) if size_mb is not None else None,
            tags=tags_map.get(instance_id, []),
        )

    def list_ledger(self, filters: DatabaseLedgerFilters) -> PaginatedResult[DatabaseLedgerRowProjection]:
        """分页查询数据库台账."""
        per_page = max(filters.per_page, 1)
        page = max(filters.page, 1)
        base_query = self._apply_filters(self._base_query(), filters)
        total = base_query.count()
        pages = max(ceil(total / per_page), 1) if total else 0

        items = (
            self._with_latest_stats(base_query)
            .order_by(Instance.name.asc(), InstanceDatabase.database_name.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        instance_ids = [instance.id for _, instance, _, _ in items if instance]
        tags_map = self._fetch_instance_tags(instance_ids)

        rows = [
            self._to_row_projection(record, instance, collected_at, size_mb, tags_map=tags_map)
            for record, instance, collected_at, size_mb in items
        ]

        return PaginatedResult(items=rows, total=total, page=page, pages=pages, limit=per_page)

    def iterate_all(self, filters: DatabaseLedgerFilters) -> list[DatabaseLedgerRowProjection]:
        """导出用: 获取全部数据库台账行."""
        base_query = self._apply_filters(self._base_query(), filters)
        results = (
            self._with_latest_stats(base_query)
            .order_by(Instance.name.asc(), InstanceDatabase.database_name.asc())
            .all()
        )
        instance_ids = [instance.id for _, instance, _, _ in results if instance]
        tags_map = self._fetch_instance_tags(instance_ids)

        return [
            self._to_row_projection(record, instance, collected_at, size_mb, tags_map=tags_map)
            for record, instance, collected_at, size_mb in results
        ]

    def _base_query(self) -> Query[Any]:
        """构造基础查询."""
        return (
            self._session.query(InstanceDatabase)
            .join(Instance, InstanceDatabase.instance_id == Instance.id)
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                InstanceDatabase.is_active.is_(True),
            )
        )

    def _apply_filters(self, query: Query[Any], filters: DatabaseLedgerFilters) -> Query[Any]:
        if filters.instance_id is not None:
            query = query.filter(Instance.id == filters.instance_id)

        normalized_type = filters.db_type.strip().lower()
        if normalized_type and normalized_type != "all":
            query = query.filter(Instance.db_type == normalized_type)

        normalized_search = filters.search.strip()
        if normalized_search:
            like_pattern = f"%{normalized_search}%"
            query = query.filter(
                or_(
                    InstanceDatabase.database_name.ilike(like_pattern),
                    Instance.name.ilike(like_pattern),
                    Instance.host.ilike(like_pattern),
                ),
            )

        normalized_tags = [tag.strip() for tag in filters.tags if tag.strip()]
        if normalized_tags:
            tag_name_column = cast("Any", Tag.name)
            tag_is_active_column = cast("Any", Tag.is_active)
            query = (
                query.join(instance_tags, Instance.id == instance_tags.c.instance_id)
                .join(Tag, Tag.id == instance_tags.c.tag_id)
                .filter(tag_name_column.in_(normalized_tags), tag_is_active_column.is_(True))
                .distinct()
            )
        return query

    def _with_latest_stats(self, query: Query[Any]) -> Query[Any]:
        """为查询附加最新容量信息."""
        latest_stats = (
            self._session.query(
                DatabaseSizeStat.instance_id.label("instance_id"),
                DatabaseSizeStat.database_name.label("database_name"),
                func.max(DatabaseSizeStat.collected_at).label("latest_collected_at"),
            )
            .group_by(DatabaseSizeStat.instance_id, DatabaseSizeStat.database_name)
            .subquery()
        )

        return (
            query.outerjoin(
                latest_stats,
                and_(
                    InstanceDatabase.instance_id == latest_stats.c.instance_id,
                    InstanceDatabase.database_name == latest_stats.c.database_name,
                ),
            )
            .outerjoin(
                DatabaseSizeStat,
                and_(
                    DatabaseSizeStat.instance_id == latest_stats.c.instance_id,
                    DatabaseSizeStat.database_name == latest_stats.c.database_name,
                    DatabaseSizeStat.collected_at == latest_stats.c.latest_collected_at,
                ),
            )
            .with_entities(
                InstanceDatabase,
                Instance,
                latest_stats.c.latest_collected_at,
                DatabaseSizeStat.size_mb,
            )
        )

    def _fetch_instance_tags(self, instance_ids: list[int]) -> dict[int, list[TagSummary]]:
        """根据实例 ID 批量获取标签列表."""
        normalized_ids = [instance_id for instance_id in instance_ids if instance_id]
        if not normalized_ids:
            return {}

        tag_name_column = cast("Any", Tag.name)
        tag_display_column = cast("Any", Tag.display_name)
        tag_is_active_column = cast("Any", Tag.is_active)
        tag_color_column = cast("Any", Tag.color)
        rows = (
            self._session.query(
                instance_tags.c.instance_id,
                tag_name_column,
                tag_display_column,
                tag_color_column,
            )
            .join(Tag, Tag.id == instance_tags.c.tag_id)
            .filter(
                instance_tags.c.instance_id.in_(normalized_ids),
                tag_is_active_column.is_(True),
            )
            .order_by(tag_display_column.asc())
            .all()
        )
        mapping: dict[int, list[TagSummary]] = defaultdict(list)
        for instance_id, name, display_name, color in rows:
            mapping[instance_id].append(
                TagSummary(
                    name=name,
                    display_name=display_name,
                    color=color or "secondary",
                ),
            )
        return dict(mapping)
