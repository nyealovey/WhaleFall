"""凭据 Repository.

职责:
- 负责 Query 组装与数据库读取（read）
- 负责写操作的数据落库与关联维护（add/delete/flush）（write）
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import or_
from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import ColumnElement

from app import db
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.tag import Tag
from app.types.credentials import CredentialListFilters, CredentialListRowProjection
from app.types.listing import PaginatedResult


class CredentialsRepository:
    """凭据查询 Repository."""

    def get_by_id(self, credential_id: int) -> Credential | None:
        return cast("Credential | None", Credential.query.get(credential_id))

    def get_by_name(self, name: str) -> Credential | None:
        normalized = name.strip()
        if not normalized:
            return None
        return cast("Credential | None", Credential.query.filter_by(name=normalized).first())

    def add(self, credential: Credential) -> Credential:
        db.session.add(credential)
        db.session.flush()
        return credential

    def delete(self, credential: Credential) -> None:
        db.session.delete(credential)

    @staticmethod
    def list_active_credentials() -> list[Credential]:
        return Credential.query.filter_by(is_active=True).order_by(Credential.created_at.desc()).all()

    def list_credentials(self, filters: CredentialListFilters) -> PaginatedResult[CredentialListRowProjection]:
        instance_count_expr = db.func.count(Instance.id)
        query = db.session.query(Credential, instance_count_expr.label("instance_count")).outerjoin(
            Instance,
            Credential.id == Instance.credential_id,
        )

        normalized_search = (filters.search or "").strip()
        if normalized_search:
            query = query.filter(
                or_(
                    Credential.name.contains(normalized_search),
                    Credential.username.contains(normalized_search),
                    Credential.description.contains(normalized_search),
                ),
            )

        if filters.credential_type:
            query = query.filter(Credential.credential_type == filters.credential_type)
        if filters.db_type:
            query = query.filter(Credential.db_type == filters.db_type)

        is_active_column = cast(ColumnElement[bool], Credential.is_active)
        if filters.status == "active":
            query = query.filter(is_active_column.is_(True))
        elif filters.status == "inactive":
            query = query.filter(is_active_column.is_(False))

        if filters.tags:
            tag_name_column = cast(ColumnElement[str], Tag.name)
            query = query.join(cast(Any, Instance.tags)).filter(tag_name_column.in_(filters.tags))

        query = self._apply_sorting(query.group_by(Credential.id), filters, instance_count_expr)

        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        items = [
            CredentialListRowProjection(credential=credential, instance_count=int(instance_count or 0))
            for credential, instance_count in pagination.items
        ]
        return PaginatedResult(
            items=items,
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )

    @staticmethod
    def _apply_sorting(
        query: Query[Any],
        filters: CredentialListFilters,
        instance_count_expr: Any,
    ) -> Query[Any]:
        """根据排序字段排序."""
        sortable_fields: dict[str, ColumnElement[Any]] = {
            "id": cast(ColumnElement[Any], Credential.id),
            "name": cast(ColumnElement[Any], Credential.name),
            "credential_type": cast(ColumnElement[Any], Credential.credential_type),
            "db_type": cast(ColumnElement[Any], Credential.db_type),
            "username": cast(ColumnElement[Any], Credential.username),
            "created_at": cast(ColumnElement[Any], Credential.created_at),
            "instance_count": cast(ColumnElement[Any], instance_count_expr),
            "is_active": cast(ColumnElement[Any], Credential.is_active),
        }
        sort_field = filters.sort_field if filters.sort_field in sortable_fields else "created_at"
        sort_order = "asc" if filters.sort_order == "asc" else "desc"

        column = sortable_fields[sort_field]
        ordered = column.asc() if sort_order == "asc" else column.desc()
        return query.order_by(ordered)
