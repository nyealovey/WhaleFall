"""实例详情-账户 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import contains_eager, load_only

from app import db
from app.models.account_change_log import AccountChangeLog
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.types.instance_accounts import InstanceAccountListFilters, InstanceAccountSummary
from app.types.listing import PaginatedResult


class InstanceAccountsRepository:
    """实例账户读模型 Repository."""

    @staticmethod
    def get_instance(instance_id: int) -> Instance:
        return Instance.query.filter(
            Instance.id == instance_id,
            cast(Any, Instance.deleted_at).is_(None),
        ).first_or_404()

    @staticmethod
    def get_account(*, instance_id: int, account_id: int) -> AccountPermission:
        return AccountPermission.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

    @staticmethod
    def fetch_summary(instance_id: int) -> InstanceAccountSummary:
        summary_row = (
            db.session.query(
                func.count(AccountPermission.id).label("total"),
                func.count(AccountPermission.id).filter(InstanceAccount.is_active.is_(True)).label("active"),
                func.count(AccountPermission.id).filter(InstanceAccount.is_active.is_(False)).label("deleted"),
                func.count(AccountPermission.id).filter(AccountPermission.is_superuser.is_(True)).label("superuser"),
            )
            .join(
                InstanceAccount,
                AccountPermission.instance_account_id == InstanceAccount.id,
            )
            .filter(AccountPermission.instance_id == instance_id)
            .one()
        )
        return InstanceAccountSummary(
            total=int(summary_row.total or 0),
            active=int(summary_row.active or 0),
            deleted=int(summary_row.deleted or 0),
            superuser=int(summary_row.superuser or 0),
        )

    @staticmethod
    def list_accounts(filters: InstanceAccountListFilters) -> PaginatedResult[AccountPermission]:
        sort_columns = {
            "id": AccountPermission.id,
            "username": AccountPermission.username,
            "is_superuser": AccountPermission.is_superuser,
            "is_locked": AccountPermission.is_locked,
            "last_change_time": AccountPermission.last_change_time,
        }
        sort_column = sort_columns.get(filters.sort_field, AccountPermission.username)
        ordering = asc(sort_column) if filters.sort_order == "asc" else desc(sort_column)

        instance_account_rel = cast("Any", AccountPermission.instance_account)
        query = (
            AccountPermission.query.join(instance_account_rel)
            .options(
                contains_eager(instance_account_rel).load_only(
                    InstanceAccount.is_active,
                    InstanceAccount.deleted_at,
                ),
            )
            .filter(AccountPermission.instance_id == filters.instance_id)
        )

        if not filters.include_permissions:
            query = query.options(
                load_only(
                    AccountPermission.id,
                    AccountPermission.instance_id,
                    AccountPermission.db_type,
                    AccountPermission.instance_account_id,
                    AccountPermission.username,
                    AccountPermission.type_specific,
                    AccountPermission.permission_facts,
                    AccountPermission.last_sync_time,
                    AccountPermission.last_change_type,
                    AccountPermission.last_change_time,
                ),
            )

        normalized_search = (filters.search or "").strip()
        if normalized_search:
            query = query.filter(AccountPermission.username.ilike(f"%{normalized_search}%"))

        if not filters.include_deleted:
            query = query.filter(InstanceAccount.is_active.is_(True))

        query = query.order_by(ordering, AccountPermission.id.asc())
        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        return PaginatedResult(
            items=list(pagination.items),
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )

    @staticmethod
    def list_change_logs(
        *, instance_id: int, username: str, db_type: str | None, limit: int = 50
    ) -> list[AccountChangeLog]:
        return (
            AccountChangeLog.query.filter_by(
                instance_id=instance_id,
                username=username,
                db_type=db_type,
            )
            .order_by(AccountChangeLog.change_time.desc())
            .limit(limit)
            .all()
        )
