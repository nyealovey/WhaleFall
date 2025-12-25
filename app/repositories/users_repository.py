"""用户读模型 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import ColumnElement

from app.models.user import User
from app.types.listing import PaginatedResult
from app.types.users import UserListFilters


class UsersRepository:
    """用户查询 Repository."""

    def list_users(self, filters: UserListFilters) -> PaginatedResult[User]:
        query: Query[Any] = cast(Query[Any], User.query)
        username_column = cast(ColumnElement[str], User.username)
        role_column = cast(ColumnElement[str], User.role)
        is_active_column = cast(ColumnElement[bool], User.is_active)

        normalized_search = (filters.search or "").strip()
        if normalized_search:
            query = query.filter(username_column.contains(normalized_search))

        if filters.role:
            query = query.filter(role_column == filters.role)

        if filters.status == "active":
            query = query.filter(is_active_column.is_(True))
        elif filters.status == "inactive":
            query = query.filter(is_active_column.is_(False))

        sortable_fields: dict[str, ColumnElement[Any]] = {
            "id": cast(ColumnElement[Any], User.id),
            "username": username_column,
            "role": role_column,
            "is_active": is_active_column,
            "created_at": cast(ColumnElement[Any], User.created_at),
        }
        sort_field = filters.sort_field if filters.sort_field in sortable_fields else "created_at"
        order_column = sortable_fields[sort_field]
        query = query.order_by(order_column.asc()) if filters.sort_order == "asc" else query.order_by(order_column.desc())

        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        return PaginatedResult(
            items=list(pagination.items),
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )
