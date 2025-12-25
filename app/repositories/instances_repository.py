"""实例读模型 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, or_
from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from app import db
from app.constants import SyncStatus
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.instance_database import InstanceDatabase
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.tag import Tag, instance_tags
from app.types.instances import InstanceListFilters, InstanceListMetrics, InstanceTagSummary
from app.types.listing import PaginatedResult


class InstancesRepository:
    """实例查询 Repository."""

    def list_instances(
        self,
        filters: InstanceListFilters,
    ) -> tuple[PaginatedResult[Instance], InstanceListMetrics]:
        """按筛选条件返回实例分页列表."""
        query: Query[Any] = cast(Query[Any], Instance.query)
        query = self._apply_instance_filters(query, filters)
        last_sync_subquery = self._build_last_sync_subquery()
        query = self._apply_instance_sorting(query, filters, last_sync_subquery)

        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        page_result = PaginatedResult(
            items=list(pagination.items),
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )

        instance_ids = [instance.id for instance in page_result.items]
        metrics = self._collect_instance_metrics(instance_ids)
        return page_result, metrics

    @staticmethod
    def _build_last_sync_subquery() -> Subquery[Any]:
        """构建同步时间子查询."""
        instance_id_column = cast(ColumnElement[int], SyncInstanceRecord.instance_id)
        completed_at_column = cast(ColumnElement[datetime], SyncInstanceRecord.completed_at)
        sync_category_column = cast(ColumnElement[str], SyncInstanceRecord.sync_category)
        status_column = cast(ColumnElement[str], SyncInstanceRecord.status)

        query: Query[Any] = cast(
            Query[Any],
            db.session.query(
                instance_id_column.label("instance_id"),
                func.max(completed_at_column).label("last_sync_time"),
            ),
        )
        return (
            query.filter(
                sync_category_column.in_(["account", "capacity"]),
                status_column == SyncStatus.COMPLETED,
                completed_at_column.isnot(None),
            )
            .group_by(instance_id_column)
            .subquery()
        )

    @staticmethod
    def _apply_instance_filters(query: Query[Any], filters: InstanceListFilters) -> Query[Any]:
        """将搜索、数据库类型、状态与标签筛选应用到查询."""
        if not filters.include_deleted:
            query = cast("Query[Any]", query).filter(Instance.deleted_at.is_(None))

        if filters.search:
            like_term = f"%{filters.search}%"
            query = cast("Query[Any]", query).filter(
                or_(
                    Instance.name.ilike(like_term),
                    Instance.host.ilike(like_term),
                    Instance.description.ilike(like_term),
                ),
            )

        if filters.db_type and filters.db_type != "all":
            query = cast("Query[Any]", query).filter(Instance.db_type == filters.db_type)

        if filters.status:
            if filters.status == "active":
                query = cast("Query[Any]", query).filter(Instance.is_active.is_(True))
            elif filters.status == "inactive":
                query = cast("Query[Any]", query).filter(Instance.is_active.is_(False))

        if filters.tags:
            tag_name_column = cast(ColumnElement[str], Tag.name)
            query = (
                cast("Query[Any]", query)
                .join(instance_tags, instance_tags.c.instance_id == Instance.id)
                .join(Tag, Tag.id == instance_tags.c.tag_id)
                .filter(tag_name_column.in_(filters.tags))
            )

        return query

    @staticmethod
    def _apply_instance_sorting(
        query: Query[Any],
        filters: InstanceListFilters,
        last_sync_subquery: Subquery[Any],
    ) -> Query[Any]:
        """根据排序字段组装 SQLAlchemy 排序语句."""
        sortable_fields: dict[str, ColumnElement[Any]] = {
            "id": cast(ColumnElement[Any], Instance.id),
            "name": cast(ColumnElement[Any], Instance.name),
            "db_type": cast(ColumnElement[Any], Instance.db_type),
            "host": cast(ColumnElement[Any], Instance.host),
        }
        if filters.sort_field == "last_sync_time":
            query = query.outerjoin(last_sync_subquery, Instance.id == last_sync_subquery.c.instance_id)
            sortable_fields["last_sync_time"] = cast(ColumnElement[Any], last_sync_subquery.c.last_sync_time)

        order_column = sortable_fields.get(filters.sort_field, cast(ColumnElement[Any], Instance.id))
        if filters.sort_order == "asc":
            return query.order_by(order_column.asc())
        return query.order_by(order_column.desc())

    @staticmethod
    def _collect_instance_metrics(instance_ids: list[int]) -> InstanceListMetrics:
        """加载实例关联的数据库/账户数量、同步时间与标签."""
        if not instance_ids:
            return InstanceListMetrics(database_counts={}, account_counts={}, last_sync_times={}, tags_map={})

        db_instance_id_column = cast(ColumnElement[int], InstanceDatabase.instance_id)
        db_active_column = cast(ColumnElement[bool], InstanceDatabase.is_active)
        db_id_column = cast(ColumnElement[int], InstanceDatabase.id)
        account_instance_id_column = cast(ColumnElement[int], InstanceAccount.instance_id)
        account_active_column = cast(ColumnElement[bool], InstanceAccount.is_active)
        account_id_column = cast(ColumnElement[int], InstanceAccount.id)
        sync_instance_id_column = cast(ColumnElement[int], SyncInstanceRecord.instance_id)
        sync_category_column = cast(ColumnElement[str], SyncInstanceRecord.sync_category)
        sync_status_column = cast(ColumnElement[str], SyncInstanceRecord.status)
        sync_completed_at_column = cast(ColumnElement[datetime], SyncInstanceRecord.completed_at)

        database_counts_query: Query[Any] = cast(
            Query[Any],
            db.session.query(db_instance_id_column, func.count(db_id_column)),
        )
        database_counts = dict(
            database_counts_query.filter(
                db_instance_id_column.in_(instance_ids),
                db_active_column.is_(True),
            )
            .group_by(db_instance_id_column)
            .all(),
        )

        account_counts_query: Query[Any] = cast(
            Query[Any],
            db.session.query(account_instance_id_column, func.count(account_id_column)),
        )
        account_counts = dict(
            account_counts_query.filter(
                account_instance_id_column.in_(instance_ids),
                account_active_column.is_(True),
            )
            .group_by(account_instance_id_column)
            .all(),
        )

        last_sync_query: Query[Any] = cast(
            Query[Any],
            db.session.query(
                sync_instance_id_column,
                func.max(sync_completed_at_column),
            ),
        )
        last_sync_rows = (
            last_sync_query.filter(
                sync_instance_id_column.in_(instance_ids),
                sync_category_column.in_(["account", "capacity"]),
                sync_status_column == SyncStatus.COMPLETED,
                sync_completed_at_column.isnot(None),
            )
            .group_by(sync_instance_id_column)
            .all()
        )
        last_sync_times = dict(last_sync_rows)

        tags_map: dict[int, list[InstanceTagSummary]] = defaultdict(list)
        tag_instance_id_column = cast(ColumnElement[int], instance_tags.c.instance_id)
        tag_name_column = cast(ColumnElement[str], Tag.name)
        tag_display_name_column = cast(ColumnElement[str], Tag.display_name)
        tag_color_column = cast(ColumnElement[str], Tag.color)
        tag_rows_query: Query[Any] = cast(
            Query[Any],
            db.session.query(
                tag_instance_id_column,
                tag_name_column,
                tag_display_name_column,
                tag_color_column,
            ),
        )
        tag_rows = (
            tag_rows_query.join(Tag, Tag.id == instance_tags.c.tag_id)
            .filter(tag_instance_id_column.in_(instance_ids))
            .all()
        )
        for instance_id, tag_name, display_name, color in tag_rows:
            tags_map[instance_id].append(
                InstanceTagSummary(
                    name=tag_name,
                    display_name=display_name,
                    color=color,
                ),
            )

        return InstanceListMetrics(
            database_counts=database_counts,
            account_counts=account_counts,
            last_sync_times=last_sync_times,
            tags_map=dict(tags_map),
        )

