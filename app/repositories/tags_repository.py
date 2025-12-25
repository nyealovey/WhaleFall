"""标签读模型 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from app import db
from app.models.tag import Tag, instance_tags
from app.types.listing import PaginatedResult
from app.types.tags import TagListFilters, TagListRowProjection, TagStats


class TagsRepository:
    """标签查询 Repository."""

    def list_tags(self, filters: TagListFilters) -> tuple[PaginatedResult[TagListRowProjection], TagStats]:
        instance_count_expr = db.func.count(instance_tags.c.instance_id)
        query = db.session.query(Tag, instance_count_expr.label("instance_count")).outerjoin(
            instance_tags,
            Tag.id == instance_tags.c.tag_id,
        )

        name_column = cast(ColumnElement[str], Tag.name)
        display_name_column = cast(ColumnElement[str], Tag.display_name)
        category_column = cast(ColumnElement[str], Tag.category)

        normalized_search = (filters.search or "").strip()
        if normalized_search:
            like_pattern = f"%{normalized_search}%"
            query = query.filter(
                db.or_(
                    name_column.ilike(like_pattern),
                    display_name_column.ilike(like_pattern),
                    category_column.ilike(like_pattern),
                ),
            )

        normalized_category = (filters.category or "").strip()
        if normalized_category:
            query = query.filter(Tag.category == normalized_category)

        if filters.status_filter == "active":
            is_active_column = cast(ColumnElement[bool], Tag.is_active)
            query = query.filter(is_active_column.is_(True))
        elif filters.status_filter == "inactive":
            is_active_column = cast(ColumnElement[bool], Tag.is_active)
            query = query.filter(is_active_column.is_(False))

        query = query.group_by(Tag.id).order_by(
            category_column.asc(),
            display_name_column.asc(),
            name_column.asc(),
            Tag.created_at.desc(),
        )

        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        rows = [
            TagListRowProjection(tag=tag, instance_count=int(instance_count or 0))
            for tag, instance_count in pagination.items
        ]
        page_result = PaginatedResult(
            items=rows,
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )
        return page_result, self.get_stats()

    @staticmethod
    def get_stats() -> TagStats:
        tag_id_column = cast(ColumnElement[int], Tag.id)
        is_active_column = cast(ColumnElement[bool], Tag.is_active)
        category_column = cast(ColumnElement[str], Tag.category)

        total_tags = int(db.session.query(db.func.count(tag_id_column)).scalar() or 0)
        active_tags = int(
            db.session.query(db.func.count(tag_id_column)).filter(is_active_column.is_(True)).scalar() or 0,
        )
        inactive_tags = int(
            db.session.query(db.func.count(tag_id_column)).filter(is_active_column.is_(False)).scalar() or 0,
        )
        category_count = int(db.session.query(db.func.count(db.func.distinct(category_column))).scalar() or 0)
        return TagStats(
            total=total_tags,
            active=active_tags,
            inactive=inactive_tags,
            category_count=category_count,
        )
