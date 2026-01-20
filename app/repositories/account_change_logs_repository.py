"""账户变更日志（全量页面）Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from sqlalchemy import and_, or_
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import NotFoundError
from app.core.types.account_change_logs import AccountChangeLogsListFilters
from app.core.types.listing import PaginatedResult
from app.models.account_change_log import AccountChangeLog
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.utils.time_utils import time_utils


class AccountChangeLogsRepository:
    """账户变更日志查询 Repository."""

    def list_logs(self, filters: AccountChangeLogsListFilters) -> PaginatedResult[tuple[AccountChangeLog, str | None, int | None]]:
        """分页查询账户变更日志."""
        change_time_column = cast("ColumnElement[Any]", AccountChangeLog.change_time)
        username_column = cast(ColumnElement[str], AccountChangeLog.username)
        db_type_column = cast(ColumnElement[str], AccountChangeLog.db_type)
        change_type_column = cast(ColumnElement[str], AccountChangeLog.change_type)
        status_column = cast(ColumnElement[str], AccountChangeLog.status)

        sortable_fields: dict[str, ColumnElement[Any]] = {
            "change_time": change_time_column,
            "username": username_column,
            "db_type": db_type_column,
            "change_type": change_type_column,
            "status": status_column,
        }
        sort_column = sortable_fields.get(filters.sort_field, change_time_column)
        ordering = sort_column.asc() if filters.sort_order == "asc" else sort_column.desc()

        instance_name_column = cast(ColumnElement[str], Instance.name)
        instance_host_column = cast(ColumnElement[str], Instance.host)
        account_id_column = cast(ColumnElement[int], AccountPermission.instance_account_id)

        join_condition = and_(
            AccountPermission.instance_id == AccountChangeLog.instance_id,
            AccountPermission.db_type == AccountChangeLog.db_type,
            AccountPermission.username == AccountChangeLog.username,
        )

        query = (
            AccountChangeLog.query.join(Instance, Instance.id == AccountChangeLog.instance_id)
            .outerjoin(AccountPermission, join_condition)
            .add_columns(instance_name_column.label("instance_name"), account_id_column.label("account_id"))
        )

        if filters.instance_id is not None:
            query = query.filter(AccountChangeLog.instance_id == filters.instance_id)
        if filters.db_type:
            query = query.filter(db_type_column == filters.db_type)
        if filters.change_type:
            query = query.filter(change_type_column == filters.change_type)
        if filters.status:
            query = query.filter(status_column == filters.status)
        if filters.hours is not None:
            cutoff = time_utils.now() - timedelta(hours=int(filters.hours))
            query = query.filter(change_time_column >= cutoff)

        if filters.search_term:
            term = filters.search_term
            query = query.filter(
                or_(
                    username_column.contains(term),
                    instance_name_column.contains(term),
                    instance_host_column.contains(term),
                ),
            )

        query = query.order_by(ordering, AccountChangeLog.id.desc())
        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        return PaginatedResult(
            items=list(pagination.items),
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )

    @staticmethod
    def get_log(log_id: int) -> AccountChangeLog:
        """按 log_id 获取变更日志."""
        log_entry = AccountChangeLog.query.filter_by(id=log_id).first()
        if not log_entry:
            raise NotFoundError("变更日志不存在")
        return cast(AccountChangeLog, log_entry)

    def get_statistics(self, *, hours: int) -> dict[str, int]:
        """获取统计汇总."""
        change_time_column = cast("ColumnElement[Any]", AccountChangeLog.change_time)
        status_column = cast(ColumnElement[str], AccountChangeLog.status)
        instance_id_column = cast(ColumnElement[int], AccountChangeLog.instance_id)
        db_type_column = cast(ColumnElement[str], AccountChangeLog.db_type)
        username_column = cast(ColumnElement[str], AccountChangeLog.username)

        cutoff = time_utils.now() - timedelta(hours=int(hours))
        base_query = AccountChangeLog.query.filter(change_time_column >= cutoff)

        total_changes = cast(int, base_query.count())
        success_count = cast(int, base_query.filter(status_column == "success").count())
        failed_count = cast(int, base_query.filter(status_column != "success").count())

        affected_accounts = (
            AccountChangeLog.query.with_entities(instance_id_column, db_type_column, username_column)
            .filter(change_time_column >= cutoff)
            .distinct()
            .count()
        )

        return {
            "total_changes": int(total_changes),
            "success_count": int(success_count),
            "failed_count": int(failed_count),
            "affected_accounts": int(affected_accounts),
        }
