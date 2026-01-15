"""标签 Repository.

职责:
- 负责 Query 组装与数据库读取（read）
- 负责写操作的数据落库与关联维护（add/delete/flush）（write）
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy.sql.elements import ColumnElement

from app import db
from app.core.types.listing import PaginatedResult
from app.core.types.tags import TagListFilters, TagListRowProjection, TagStats
from app.models.tag import Tag, instance_tags

if TYPE_CHECKING:
    from app.models.instance import Instance


class TagsRepository:
    """标签查询 Repository."""

    def get_by_id(self, tag_id: int) -> Tag | None:
        """按ID获取标签."""
        return Tag.query.get(tag_id)

    def get_by_name(self, name: str) -> Tag | None:
        """按名称获取标签."""
        normalized = name.strip()
        if not normalized:
            return None
        return Tag.query.filter_by(name=normalized).first()

    @staticmethod
    def list_tags_by_ids(tag_ids: Sequence[int]) -> list[Tag]:
        """按 ID 列表获取标签."""
        normalized_ids = [int(tag_id) for tag_id in (tag_ids or []) if tag_id]
        if not normalized_ids:
            return []
        return Tag.query.filter(Tag.id.in_(normalized_ids)).all()

    def add(self, tag: Tag) -> Tag:
        """新增标签并 flush."""
        db.session.add(tag)
        db.session.flush()
        return tag

    def delete(self, tag: Tag) -> None:
        """删除标签及关联关系."""
        if getattr(tag, "id", None) is not None:
            db.session.execute(instance_tags.delete().where(instance_tags.c.tag_id == tag.id))
        db.session.delete(tag)

    def sync_instance_tags(self, instance: Instance, tag_names: Sequence[str]) -> list[str]:
        """同步实例标签关系."""
        instance_id = getattr(instance, "id", None)
        if instance_id is not None:
            db.session.execute(instance_tags.delete().where(instance_tags.c.instance_id == instance_id))

        if hasattr(instance.tags, "clear"):
            instance.tags.clear()

        added: list[str] = []
        for name in tag_names:
            tag = self.get_by_name(name)
            if tag:
                instance.tags.append(tag)
                added.append(tag.name)
        return added

    def list_tags(self, filters: TagListFilters) -> tuple[PaginatedResult[TagListRowProjection], TagStats]:
        """分页查询标签列表."""
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
            query = query.filter(category_column == normalized_category)

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
        """获取标签统计."""
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
