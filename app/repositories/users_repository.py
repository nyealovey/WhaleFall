"""用户 Repository.

职责:
- 负责 Query 组装与数据库读取（read）
- 负责写操作的数据落库（add/delete/flush）（write）
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import ColumnElement

from app import db
from app.constants import UserRole
from app.models.user import User
from app.types.listing import PaginatedResult
from app.types.users import UserListFilters


class UsersRepository:
    """用户查询 Repository."""

    def get_by_id(self, user_id: int) -> User | None:
        return cast("User | None", User.query.get(user_id))

    def get_by_username(self, username: str) -> User | None:
        normalized = (username or "").strip()
        if not normalized:
            return None
        return cast("User | None", User.query.filter_by(username=normalized).first())

    def add(self, user: User) -> User:
        db.session.add(user)
        db.session.flush()
        return user

    def delete(self, user: User) -> None:
        db.session.delete(user)

    @staticmethod
    def count_users() -> int:
        return int(User.query.count() or 0)

    @staticmethod
    def fetch_stats() -> dict[str, int]:
        total_users = int(User.query.count() or 0)
        active_users = int(User.query.filter_by(is_active=True).count() or 0)
        admin_users = int(User.query.filter_by(role=UserRole.ADMIN).count() or 0)
        user_users = int(User.query.filter_by(role=UserRole.USER).count() or 0)
        inactive_users = max(total_users - active_users, 0)
        return {
            "total": total_users,
            "active": active_users,
            "inactive": inactive_users,
            "admin": admin_users,
            "user": user_users,
        }

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
        query = (
            query.order_by(order_column.asc()) if filters.sort_order == "asc" else query.order_by(order_column.desc())
        )

        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        return PaginatedResult(
            items=list(pagination.items),
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )
