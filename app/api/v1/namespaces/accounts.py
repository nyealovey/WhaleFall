"""Accounts namespace (Phase 2 核心域迁移 - Ledgers)."""

from __future__ import annotations

from typing import ClassVar

from flask import Response, request
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.restx_models.accounts import (
    ACCOUNT_CLASSIFICATION_RULE_STAT_ITEM_FIELDS,
    ACCOUNT_LEDGER_ITEM_FIELDS,
    ACCOUNT_LEDGER_PERMISSIONS_RESPONSE_FIELDS,
    ACCOUNT_STATISTICS_FIELDS,
)
from app.api.v1.restx_models.instances import (
    INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS,
    INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS,
    INSTANCE_ACCOUNT_CHANGE_HISTORY_RESPONSE_FIELDS,
)
from app.errors import ValidationError
from app.services.accounts.account_classifications_read_service import AccountClassificationsReadService
from app.services.accounts.accounts_statistics_read_service import AccountsStatisticsReadService
from app.services.files.account_export_service import AccountExportService
from app.services.ledgers.accounts_ledger_list_service import AccountsLedgerListService
from app.services.ledgers.accounts_ledger_change_history_service import AccountsLedgerChangeHistoryService
from app.services.ledgers.accounts_ledger_permissions_service import AccountsLedgerPermissionsService
from app.types.accounts_ledgers import AccountFilters
from app.utils.pagination_utils import resolve_page, resolve_page_size

ns = Namespace("accounts", description="账户管理")

ErrorEnvelope = get_error_envelope_model(ns)
_account_export_service = AccountExportService()

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

AccountLedgerChangeLogModel = ns.model("AccountLedgerChangeLog", INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS)
AccountLedgerChangeHistoryAccountModel = ns.model(
    "AccountLedgerChangeHistoryAccount",
    INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS,
)
AccountLedgerChangeHistoryData = ns.model(
    "AccountLedgerChangeHistoryData",
    {
        "account": fields.Nested(AccountLedgerChangeHistoryAccountModel),
        "history": fields.List(fields.Nested(AccountLedgerChangeLogModel)),
    },
)
AccountLedgerChangeHistorySuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountLedgerChangeHistorySuccessEnvelope",
    AccountLedgerChangeHistoryData,
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

AccountStatisticsRuleStatItemModel = ns.model(
    "AccountStatisticsRuleStatItem",
    ACCOUNT_CLASSIFICATION_RULE_STAT_ITEM_FIELDS,
)
AccountStatisticsRulesData = ns.model(
    "AccountStatisticsRulesData",
    {
        "rule_stats": fields.List(fields.Nested(AccountStatisticsRuleStatItemModel)),
    },
)
AccountStatisticsRulesSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountStatisticsRulesSuccessEnvelope",
    AccountStatisticsRulesData,
)


def _parse_account_filters(*, allow_query_db_type: bool = True) -> AccountFilters:
    args = request.args
    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=20,
        minimum=1,
        maximum=200,
    )
    search = (args.get("search") or "").strip()
    instance_id = args.get("instance_id", type=int)
    include_deleted = (args.get("include_deleted") or "").lower() == "true"
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
        include_deleted=include_deleted,
        is_locked=is_locked,
        is_superuser=is_superuser,
        plugin=plugin,
        tags=tags,
        classification=classification_param,
        classification_filter=classification_filter,
        db_type=normalized_db_type,
    )


def _parse_rule_ids_param(raw_value: str | None) -> list[int] | None:
    if not raw_value:
        return None
    rule_ids: list[int] = []
    for token in raw_value.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        try:
            rule_ids.append(int(stripped))
        except ValueError as exc:
            raise ValidationError("rule_ids 参数必须为整数ID,使用逗号分隔") from exc
    return rule_ids or None


@ns.route("/ledgers")
class AccountsLedgersResource(BaseResource):
    """账户台账列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountLedgersListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取账户台账列表."""
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
                "limit": filters.limit,
                "sort": sort_field,
                "order": sort_order,
            },
        )


@ns.route("/ledgers/<int:account_id>/permissions")
class AccountsLedgersPermissionsResource(BaseResource):
    """账户台账权限资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountLedgerPermissionsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, account_id: int):
        """获取账户权限详情."""

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


@ns.route("/ledgers/<int:account_id>/change-history")
class AccountsLedgersChangeHistoryResource(BaseResource):
    """账户台账变更历史资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountLedgerChangeHistorySuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, account_id: int):
        """获取账户变更历史."""

        def _execute():
            result = AccountsLedgerChangeHistoryService().get_change_history(account_id)
            payload = marshal(result, INSTANCE_ACCOUNT_CHANGE_HISTORY_RESPONSE_FIELDS)
            return self.success(
                data=payload,
                message="获取账户变更历史成功",
            )

        return self.safe_call(
            _execute,
            module="accounts_ledgers",
            action="get_account_change_history",
            public_error="获取变更历史失败",
            context={"account_id": account_id},
        )


@ns.route("/ledgers/exports")
class AccountsLedgersExportResource(BaseResource):
    """账户台账导出资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK")
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
        """导出账户台账."""
        filters = _parse_account_filters(allow_query_db_type=True)

        def _execute() -> Response:
            result = _account_export_service.export_accounts_csv(filters)
            return Response(
                result.content,
                mimetype=result.mimetype,
                headers={"Content-Disposition": f"attachment; filename={result.filename}"},
            )

        return self.safe_call(
            _execute,
            module="accounts_ledgers",
            action="export_accounts",
            public_error="导出账户失败",
            context={
                "db_type": filters.db_type,
                "instance_id": filters.instance_id,
                "include_deleted": filters.include_deleted,
                "tags_count": len(filters.tags),
            },
        )


@ns.route("/statistics")
class AccountsStatisticsResource(BaseResource):
    """账户统计资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取账户统计信息."""

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
    """账户统计汇总资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsSummarySuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取账户统计汇总."""
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
    """账户数据库类型统计资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsDbTypesSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取数据库类型统计."""

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
    """账户分类统计资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsClassificationsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取账户分类统计."""

        def _execute():
            stats = AccountsStatisticsReadService().fetch_classification_stats()
            return self.success(data=stats, message="获取账户分类统计成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_account_statistics_by_classification",
            public_error="获取账户分类统计失败",
        )


@ns.route("/statistics/rules")
class AccountsStatisticsRulesResource(BaseResource):
    """账户分类规则命中统计资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsRulesSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取规则命中统计."""
        rule_ids = _parse_rule_ids_param(request.args.get("rule_ids"))

        def _execute():
            stats = AccountClassificationsReadService().get_rule_stats(rule_ids=rule_ids)
            payload = marshal(stats, ACCOUNT_CLASSIFICATION_RULE_STAT_ITEM_FIELDS)
            return self.success(data={"rule_stats": payload}, message="规则命中统计获取成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_rule_stats",
            public_error="获取规则命中统计失败",
            context={"rule_ids": rule_ids},
        )
