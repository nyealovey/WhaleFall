"""账户台账 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, cast

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query, contains_eager

from app.models.account_change_log import AccountChangeLog
from app.models.account_classification import AccountClassification, AccountClassificationAssignment
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.tag import Tag, instance_tags
from app.core.types.accounts_ledgers import AccountClassificationSummary, AccountFilters, AccountLedgerMetrics
from app.core.types.listing import PaginatedResult
from app.core.types.tags import TagSummary
from app.utils.theme_color_utils import get_theme_color_value
from app.utils.structlog_config import log_warning


class AccountsLedgerRepository:
    """账户台账查询 Repository."""

    @staticmethod
    def get_account_by_instance_account_id(instance_account_id: int) -> AccountPermission:
        """获取账户及其所属实例信息."""
        instance_rel = cast("Any", AccountPermission.instance)
        query = (
            cast("Any", AccountPermission.query)
            .join(instance_rel)
            .options(contains_eager(instance_rel))
            .filter(AccountPermission.instance_account_id == instance_account_id)
        )
        return cast(AccountPermission, query.first_or_404())

    @staticmethod
    def list_change_logs(
        *,
        instance_id: int,
        username: str,
        db_type: str | None,
        limit: int = 50,
    ) -> list[AccountChangeLog]:
        """查询账户变更日志."""
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

    def list_accounts(
        self,
        filters: AccountFilters,
        *,
        sort_field: str,
        sort_order: str,
    ) -> tuple[PaginatedResult[AccountPermission], AccountLedgerMetrics]:
        """分页查询账户台账."""
        query = self._apply_sorting(self._build_account_query(filters), sort_field, sort_order)
        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        page_result = PaginatedResult(
            items=list(pagination.items),
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )
        account_ids = [account.id for account in page_result.items]
        instance_ids = [account.instance_id for account in page_result.items]
        metrics = AccountLedgerMetrics(
            tags_map=self._fetch_instance_tags(instance_ids),
            classifications_map=self._fetch_account_classifications(account_ids),
        )
        return page_result, metrics

    def list_all_accounts(
        self,
        filters: AccountFilters,
        *,
        sort_field: str,
        sort_order: str,
    ) -> tuple[list[AccountPermission], AccountLedgerMetrics]:
        """返回全部账户(用于导出等不分页场景)."""
        query = self._apply_sorting(self._build_account_query(filters), sort_field, sort_order)
        accounts = list(query.all())
        account_ids = [account.id for account in accounts]
        instance_ids = [account.instance_id for account in accounts]
        metrics = AccountLedgerMetrics(
            tags_map=self._fetch_instance_tags(instance_ids),
            classifications_map=self._fetch_account_classifications(account_ids),
        )
        return accounts, metrics

    def _build_account_query(self, filters: AccountFilters) -> Query[Any]:
        base_query = cast(Query[Any], AccountPermission.query)
        instance_rel = cast("Any", AccountPermission.instance)
        instance_account_rel = cast("Any", AccountPermission.instance_account)
        query = (
            base_query.join(instance_account_rel)
            .options(contains_eager(instance_account_rel))
            .join(instance_rel)
            .options(contains_eager(instance_rel))
        )

        if not filters.include_deleted:
            query = query.filter(InstanceAccount.is_active.is_(True))

        if filters.db_type:
            query = query.filter(AccountPermission.db_type == filters.db_type)
        if filters.instance_id:
            query = query.filter(AccountPermission.instance_id == filters.instance_id)

        query = self._apply_search_filter(query, filters.search)
        query = self._apply_lock_filters(query, filters.is_locked, filters.is_superuser)
        query = self._apply_tag_filter(query, filters.tags)
        return self._apply_classification_filter(query, filters.classification_filter)

    @staticmethod
    def _apply_search_filter(query: Query[Any], search: str) -> Query[Any]:
        if not search:
            return query
        username_column = cast("Any", AccountPermission.username)
        instance_name_column = cast("Any", Instance.name)
        instance_host_column = cast("Any", Instance.host)
        return query.filter(
            or_(
                username_column.contains(search),
                instance_name_column.contains(search),
                instance_host_column.contains(search),
            ),
        )

    @staticmethod
    def _apply_lock_filters(query: Query[Any], is_locked: str | None, is_superuser: str | None) -> Query[Any]:
        if is_locked == "true":
            query = query.filter(AccountPermission.is_locked.is_(True))
        elif is_locked == "false":
            query = query.filter(AccountPermission.is_locked.is_(False))

        if is_superuser in {"true", "false"}:
            query = query.filter(AccountPermission.is_superuser == (is_superuser == "true"))
        return query

    @staticmethod
    def _apply_sorting(query: Query[Any], sort_field: str, sort_order: str) -> Query[Any]:
        sortable_fields = {
            "username": AccountPermission.username,
            "db_type": AccountPermission.db_type,
            "is_locked": AccountPermission.is_locked,
            "is_superuser": AccountPermission.is_superuser,
        }
        order_column = sortable_fields.get(sort_field, AccountPermission.username)
        return query.order_by(order_column.desc() if sort_order == "desc" else order_column.asc())

    @staticmethod
    def _apply_tag_filter(query: Query[Any], tags: list[str]) -> Query[Any]:
        if not tags:
            return query
        try:
            tag_name_column = cast("Any", Tag.name)
            return (
                query.join(instance_tags, Instance.id == instance_tags.c.instance_id)
                .join(Tag, Tag.id == instance_tags.c.tag_id)
                .filter(tag_name_column.in_(tags))
            )
        except SQLAlchemyError as exc:  # pragma: no cover - 日志用于排查
            log_warning(
                "标签过滤失败",
                module="accounts_ledgers",
                exception=exc,
                action="_apply_tag_filter",
                tags=tags,
            )
            return query

    @staticmethod
    def _apply_classification_filter(query: Query[Any], classification_filter: str) -> Query[Any]:
        if not classification_filter:
            return query
        try:
            classification_id = int(classification_filter)
        except (ValueError, TypeError) as exc:
            safe_exc = exc if isinstance(exc, Exception) else Exception(str(exc))
            log_warning(
                "分类ID转换失败",
                module="accounts_ledgers",
                exception=safe_exc,
                action="_apply_classification_filter",
                classification=classification_filter,
            )
            return query

        return (
            query.join(AccountClassificationAssignment)
            .join(AccountClassification)
            .filter(
                AccountClassification.id == classification_id,
                AccountClassificationAssignment.is_active.is_(True),
            )
        )

    @staticmethod
    def _fetch_instance_tags(instance_ids: list[int]) -> dict[int, list[TagSummary]]:
        normalized_ids = [instance_id for instance_id in instance_ids if instance_id]
        if not normalized_ids:
            return {}

        tag_rows = (
            cast(Any, Tag.query)
            .join(instance_tags, Tag.id == instance_tags.c.tag_id)
            .filter(instance_tags.c.instance_id.in_(normalized_ids))
            .with_entities(
                instance_tags.c.instance_id,
                Tag.name,
                Tag.display_name,
                Tag.color,
            )
            .all()
        )
        mapping: dict[int, list[TagSummary]] = defaultdict(list)
        for instance_id, name, display_name, color in tag_rows:
            mapping[instance_id].append(
                TagSummary(
                    name=name,
                    display_name=display_name,
                    color=color,
                ),
            )
        return dict(mapping)

    @staticmethod
    def _fetch_account_classifications(account_ids: list[int]) -> dict[int, list[AccountClassificationSummary]]:
        if not account_ids:
            return {}

        rows = (
            cast(Any, AccountClassificationAssignment.query)
            .join(AccountClassification)
            .filter(
                AccountClassificationAssignment.account_id.in_(account_ids),
                AccountClassificationAssignment.is_active.is_(True),
            )
            .with_entities(
                AccountClassificationAssignment.account_id,
                AccountClassification.name,
                AccountClassification.color,
            )
            .all()
        )

        classifications: dict[int, list[AccountClassificationSummary]] = defaultdict(list)
        for account_id, name, color in rows:
            classifications[account_id].append(
                AccountClassificationSummary(
                    name=name,
                    color=get_theme_color_value(color or "info"),
                ),
            )
        return dict(classifications)
