"""Accounts namespace (Phase 2 核心域迁移 - Ledgers)."""

from __future__ import annotations

from flask import request
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.routes.accounts.restx_models import (
    ACCOUNT_LEDGER_ITEM_FIELDS,
    ACCOUNT_LEDGER_PERMISSIONS_RESPONSE_FIELDS,
    ACCOUNT_STATISTICS_FIELDS,
)
from app.services.accounts.accounts_statistics_read_service import AccountsStatisticsReadService
from app.services.ledgers.accounts_ledger_list_service import AccountsLedgerListService
from app.services.ledgers.accounts_ledger_permissions_service import AccountsLedgerPermissionsService
from app.types.accounts_ledgers import AccountFilters
from app.utils.pagination_utils import resolve_page, resolve_page_size

ns = Namespace("accounts", description="账户管理")

ErrorEnvelope = get_error_envelope_model(ns)

TagModel = ns.model(
    "AccountTag",
    {
        "name": fields.String(),
        "display_name": fields.String(),
        "color": fields.String(),
    },
)

ClassificationModel = ns.model(
    "AccountClassification",
    {
        "name": fields.String(),
        "color": fields.String(),
    },
)

AccountLedgerItemModel = ns.model(
    "AccountLedgerItem",
    {
        "id": fields.Integer(),
        "username": fields.String(),
        "instance_name": fields.String(),
        "instance_host": fields.String(),
        "db_type": fields.String(),
        "is_locked": fields.Boolean(),
        "is_superuser": fields.Boolean(),
        "is_active": fields.Boolean(),
        "is_deleted": fields.Boolean(),
        "tags": fields.List(fields.Nested(TagModel)),
        "classifications": fields.List(fields.Nested(ClassificationModel)),
    },
)

AccountLedgersListData = ns.model(
    "AccountLedgersListData",
    {
        "items": fields.List(fields.Nested(AccountLedgerItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
    },
)

AccountLedgersListSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountLedgersListSuccessEnvelope",
    AccountLedgersListData,
)

AccountLedgerPermissionsData = ns.model(
    "AccountLedgerPermissionsData",
    {
        "permissions": fields.Raw,
        "account": fields.Raw,
    },
)

AccountLedgerPermissionsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountLedgerPermissionsSuccessEnvelope",
    AccountLedgerPermissionsData,
)

AccountStatisticsStatsModel = ns.model(
    "AccountStatisticsStats",
    {
        "total_accounts": fields.Integer(),
        "active_accounts": fields.Integer(),
        "locked_accounts": fields.Integer(),
        "normal_accounts": fields.Integer(),
        "deleted_accounts": fields.Integer(),
        "database_instances": fields.Integer(),
        "total_instances": fields.Integer(),
        "active_instances": fields.Integer(),
        "disabled_instances": fields.Integer(),
        "normal_instances": fields.Integer(),
        "deleted_instances": fields.Integer(),
        "db_type_stats": fields.Raw(),
        "classification_stats": fields.Raw(),
    },
)

AccountStatisticsData = ns.model(
    "AccountStatisticsData",
    {
        "stats": fields.Nested(AccountStatisticsStatsModel),
    },
)

AccountStatisticsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountStatisticsSuccessEnvelope",
    AccountStatisticsData,
)

AccountStatisticsSummaryData = ns.model(
    "AccountStatisticsSummaryData",
    {
        "total_accounts": fields.Integer(),
        "active_accounts": fields.Integer(),
        "locked_accounts": fields.Integer(),
        "normal_accounts": fields.Integer(),
        "deleted_accounts": fields.Integer(),
        "total_instances": fields.Integer(),
        "active_instances": fields.Integer(),
        "disabled_instances": fields.Integer(),
        "normal_instances": fields.Integer(),
        "deleted_instances": fields.Integer(),
    },
)

AccountStatisticsSummarySuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountStatisticsSummarySuccessEnvelope",
    AccountStatisticsSummaryData,
)

AccountStatisticsDbTypesSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountStatisticsDbTypesSuccessEnvelope",
)

AccountStatisticsClassificationsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountStatisticsClassificationsSuccessEnvelope",
)


def _parse_account_filters(*, allow_query_db_type: bool = True) -> AccountFilters:
    args = request.args
    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=20,
        minimum=1,
        maximum=200,
        module="accounts_ledgers",
        action="list_accounts_data",
    )
    search = (args.get("search") or "").strip()
    instance_id = args.get("instance_id", type=int)
    is_locked = args.get("is_locked")
    is_superuser = args.get("is_superuser")
    plugin = (args.get("plugin", "") or "").strip()
    tags = [tag.strip() for tag in args.getlist("tags") if tag and tag.strip()]
    classification_param = (args.get("classification", "") or "").strip()
    classification_filter = classification_param if classification_param not in {"", "all"} else ""
    raw_db_type = args.get("db_type") if allow_query_db_type else None
    normalized_db_type = raw_db_type if raw_db_type not in {None, "", "all"} else None

    return AccountFilters(
        page=page,
        limit=limit,
        search=search,
        instance_id=instance_id,
        is_locked=is_locked,
        is_superuser=is_superuser,
        plugin=plugin,
        tags=tags,
        classification=classification_param,
        classification_filter=classification_filter,
        db_type=normalized_db_type,
    )


@ns.route("/ledgers")
class AccountsLedgersResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountLedgersListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        filters = _parse_account_filters(allow_query_db_type=True)
        sort_field = request.args.get("sort", "username")
        sort_order = (request.args.get("order", "asc") or "asc").lower()

        def _execute():
            result = AccountsLedgerListService().list_accounts(filters, sort_field=sort_field, sort_order=sort_order)
            items = marshal(result.items, ACCOUNT_LEDGER_ITEM_FIELDS)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                    "limit": result.limit,
                },
                message="获取账户列表成功",
            )

        return self.safe_call(
            _execute,
            module="accounts_ledgers",
            action="list_accounts_data",
            public_error="获取账户列表失败",
            context={
                "search": filters.search,
                "db_type": filters.db_type,
                "instance_id": filters.instance_id,
                "is_locked": filters.is_locked,
                "is_superuser": filters.is_superuser,
                "tags_count": len(filters.tags),
                "classification": filters.classification_filter,
                "page": filters.page,
                "page_size": filters.limit,
                "sort": sort_field,
                "order": sort_order,
            },
        )


@ns.route("/ledgers/<int:account_id>/permissions")
class AccountsLedgersPermissionsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountLedgerPermissionsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, account_id: int):
        def _execute():
            result = AccountsLedgerPermissionsService().get_permissions(account_id)
            payload = marshal(result, ACCOUNT_LEDGER_PERMISSIONS_RESPONSE_FIELDS, skip_none=True)
            return self.success(
                data=payload,
                message="获取账户权限成功",
            )

        return self.safe_call(
            _execute,
            module="accounts_ledgers",
            action="get_account_permissions",
            public_error="获取账户权限失败",
            context={"account_id": account_id},
        )


@ns.route("/statistics")
class AccountsStatisticsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            result = AccountsStatisticsReadService().build_statistics()
            stats_payload = marshal(result, ACCOUNT_STATISTICS_FIELDS)
            return self.success(data={"stats": stats_payload}, message="获取账户统计信息成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_account_statistics",
            public_error="获取账户统计信息失败",
        )


@ns.route("/statistics/summary")
class AccountsStatisticsSummaryResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsSummarySuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        instance_id = request.args.get("instance_id", type=int)
        db_type = request.args.get("db_type", type=str)

        def _execute():
            summary = AccountsStatisticsReadService().fetch_summary(instance_id=instance_id, db_type=db_type)
            return self.success(data=summary, message="获取账户统计汇总成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_account_statistics_summary",
            public_error="获取账户统计汇总失败",
            context={"instance_id": instance_id, "db_type": db_type},
        )


@ns.route("/statistics/db-types")
class AccountsStatisticsByDbTypeResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsDbTypesSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            stats = AccountsStatisticsReadService().fetch_db_type_stats()
            return self.success(data=stats, message="获取数据库类型统计成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_account_statistics_by_db_type",
            public_error="获取数据库类型统计失败",
        )


@ns.route("/statistics/classifications")
class AccountsStatisticsByClassificationResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsClassificationsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            stats = AccountsStatisticsReadService().fetch_classification_stats()
            return self.success(data=stats, message="获取账户分类统计成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_account_statistics_by_classification",
            public_error="获取账户分类统计失败",
        )
