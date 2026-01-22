"""Accounts namespace (Phase 2 核心域迁移 - Ledgers)."""

from __future__ import annotations

from typing import ClassVar

from flask import Response
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import bool_with_default, new_parser
from app.api.v1.restx_models.accounts import (
    ACCOUNT_CLASSIFICATION_RULE_STAT_ITEM_FIELDS,
    ACCOUNT_LEDGER_ITEM_FIELDS,
    ACCOUNT_LEDGER_PERMISSIONS_RESPONSE_FIELDS,
    ACCOUNT_STATISTICS_FIELDS,
)
from app.api.v1.restx_models.instances import (
    INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS,
    INSTANCE_ACCOUNT_CHANGE_HISTORY_RESPONSE_FIELDS,
    INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS,
)
from app.core.exceptions import ValidationError
from app.core.types.accounts_ledgers import AccountFilters
from app.schemas.accounts_query import AccountsFiltersQuery, AccountsLedgersListQuery
from app.schemas.validation import validate_or_raise
from app.services.accounts.account_classification_daily_stats_read_service import (
    AccountClassificationDailyStatsReadService,
)
from app.services.accounts.account_classifications_read_service import AccountClassificationsReadService
from app.services.accounts.accounts_statistics_read_service import AccountsStatisticsReadService
from app.services.files.account_export_service import AccountExportService
from app.services.ledgers.accounts_ledger_change_history_service import AccountsLedgerChangeHistoryService
from app.services.ledgers.accounts_ledger_list_service import AccountsLedgerListService
from app.services.ledgers.accounts_ledger_permissions_service import AccountsLedgerPermissionsService

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

_accounts_filters_query_parser = new_parser()
_accounts_filters_query_parser.add_argument("page", type=int, default=1, location="args")
_accounts_filters_query_parser.add_argument("limit", type=int, default=20, location="args")
_accounts_filters_query_parser.add_argument("search", type=str, default="", location="args")
_accounts_filters_query_parser.add_argument("instance_id", type=int, location="args")
_accounts_filters_query_parser.add_argument(
    "include_deleted", type=bool_with_default(False), default=False, location="args"
)
_accounts_filters_query_parser.add_argument(
    "include_roles", type=bool_with_default(False), default=False, location="args"
)
_accounts_filters_query_parser.add_argument("is_locked", type=str, location="args")
_accounts_filters_query_parser.add_argument("is_superuser", type=str, location="args")
_accounts_filters_query_parser.add_argument("plugin", type=str, default="", location="args")
_accounts_filters_query_parser.add_argument("tags", type=str, action="append", location="args")
_accounts_filters_query_parser.add_argument("classification", type=str, default="", location="args")
_accounts_filters_query_parser.add_argument("db_type", type=str, location="args")

_accounts_ledgers_list_query_parser = new_parser()
for argument in _accounts_filters_query_parser.args:
    _accounts_ledgers_list_query_parser.args.append(argument)
_accounts_ledgers_list_query_parser.add_argument("sort", type=str, default="username", location="args")
_accounts_ledgers_list_query_parser.add_argument("order", type=str, default="asc", location="args")

_accounts_statistics_summary_query_parser = new_parser()
_accounts_statistics_summary_query_parser.add_argument("instance_id", type=int, location="args")
_accounts_statistics_summary_query_parser.add_argument("db_type", type=str, location="args")

_accounts_statistics_rules_query_parser = new_parser()
_accounts_statistics_rules_query_parser.add_argument("rule_ids", type=str, location="args")

_account_classification_trend_query_parser = new_parser()
_account_classification_trend_query_parser.add_argument("classification_id", type=int, location="args")
_account_classification_trend_query_parser.add_argument("period_type", type=str, default="daily", location="args")
_account_classification_trend_query_parser.add_argument("periods", type=int, default=7, location="args")
_account_classification_trend_query_parser.add_argument("db_type", type=str, location="args")
_account_classification_trend_query_parser.add_argument("instance_id", type=int, location="args")

_account_classification_trends_query_parser = new_parser()
_account_classification_trends_query_parser.add_argument("period_type", type=str, default="daily", location="args")
_account_classification_trends_query_parser.add_argument("periods", type=int, default=7, location="args")
_account_classification_trends_query_parser.add_argument("db_type", type=str, location="args")
_account_classification_trends_query_parser.add_argument("instance_id", type=int, location="args")

_account_classification_rule_trend_query_parser = new_parser()
_account_classification_rule_trend_query_parser.add_argument("rule_id", type=int, location="args")
_account_classification_rule_trend_query_parser.add_argument("period_type", type=str, default="daily", location="args")
_account_classification_rule_trend_query_parser.add_argument("periods", type=int, default=7, location="args")
_account_classification_rule_trend_query_parser.add_argument("db_type", type=str, location="args")
_account_classification_rule_trend_query_parser.add_argument("instance_id", type=int, location="args")

_account_classification_rule_contributions_query_parser = new_parser()
_account_classification_rule_contributions_query_parser.add_argument("classification_id", type=int, location="args")
_account_classification_rule_contributions_query_parser.add_argument(
    "period_type", type=str, default="daily", location="args"
)
_account_classification_rule_contributions_query_parser.add_argument("db_type", type=str, location="args")
_account_classification_rule_contributions_query_parser.add_argument("instance_id", type=int, location="args")
_account_classification_rule_contributions_query_parser.add_argument("limit", type=int, default=10, location="args")

_account_classification_rules_overview_query_parser = new_parser()
_account_classification_rules_overview_query_parser.add_argument("classification_id", type=int, location="args")
_account_classification_rules_overview_query_parser.add_argument(
    "period_type", type=str, default="daily", location="args"
)
_account_classification_rules_overview_query_parser.add_argument("periods", type=int, default=7, location="args")
_account_classification_rules_overview_query_parser.add_argument("db_type", type=str, location="args")
_account_classification_rules_overview_query_parser.add_argument("instance_id", type=int, location="args")
_account_classification_rules_overview_query_parser.add_argument("status", type=str, default="active", location="args")


AccountClassificationTrendPointModel = ns.model(
    "AccountClassificationTrendPoint",
    {
        "period_start": fields.String(required=True),
        "period_end": fields.String(required=True),
        "value_avg": fields.Float(required=True),
        "value_sum": fields.Integer(required=True),
        "coverage_days": fields.Integer(required=True),
        "expected_days": fields.Integer(required=True),
    },
)
AccountClassificationTrendData = ns.model(
    "AccountClassificationTrendData",
    {"trend": fields.List(fields.Nested(AccountClassificationTrendPointModel), required=True)},
)
AccountClassificationTrendSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationTrendSuccessEnvelope",
    AccountClassificationTrendData,
)

AccountClassificationTrendsBucketModel = ns.model(
    "AccountClassificationTrendsBucket",
    {
        "period_start": fields.String(required=True),
        "period_end": fields.String(required=True),
        "expected_days": fields.Integer(required=True),
    },
)
AccountClassificationTrendsSeriesModel = ns.model(
    "AccountClassificationTrendsSeries",
    {
        "classification_id": fields.Integer(required=True),
        "classification_name": fields.String(required=True),
        "points": fields.List(fields.Nested(AccountClassificationTrendPointModel), required=True),
    },
)
AccountClassificationTrendsData = ns.model(
    "AccountClassificationTrendsData",
    {
        "period_type": fields.String(required=True),
        "periods": fields.Integer(required=True),
        "buckets": fields.List(fields.Nested(AccountClassificationTrendsBucketModel), required=True),
        "series": fields.List(fields.Nested(AccountClassificationTrendsSeriesModel), required=True),
    },
)
AccountClassificationTrendsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationTrendsSuccessEnvelope",
    AccountClassificationTrendsData,
)

AccountClassificationRuleContributionsItemModel = ns.model(
    "AccountClassificationRuleContributionsItem",
    {
        "rule_id": fields.Integer(required=True),
        "rule_name": fields.String(required=True),
        "db_type": fields.String(required=False),
        "rule_version": fields.Integer(required=False),
        "is_active": fields.Boolean(required=False),
        "value_avg": fields.Float(required=True),
        "value_sum": fields.Integer(required=True),
        "coverage_days": fields.Integer(required=True),
        "expected_days": fields.Integer(required=True),
    },
)
AccountClassificationRuleContributionsData = ns.model(
    "AccountClassificationRuleContributionsData",
    {
        "period_start": fields.String(required=True),
        "period_end": fields.String(required=True),
        "coverage_days": fields.Integer(required=True),
        "expected_days": fields.Integer(required=True),
        "contributions": fields.List(fields.Nested(AccountClassificationRuleContributionsItemModel), required=True),
    },
)
AccountClassificationRuleContributionsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationRuleContributionsSuccessEnvelope",
    AccountClassificationRuleContributionsData,
)

AccountClassificationRuleOverviewItemModel = ns.model(
    "AccountClassificationRuleOverviewItem",
    {
        "rule_id": fields.Integer(required=True),
        "rule_name": fields.String(required=True),
        "db_type": fields.String(required=True),
        "rule_version": fields.Integer(required=True),
        "is_active": fields.Boolean(required=True),
        "latest_value_avg": fields.Float(required=True),
        "latest_value_sum": fields.Integer(required=True),
        "latest_coverage_days": fields.Integer(required=True),
        "latest_expected_days": fields.Integer(required=True),
        "window_value_sum": fields.Integer(required=True),
    },
)
AccountClassificationRulesOverviewData = ns.model(
    "AccountClassificationRulesOverviewData",
    {
        "window_start": fields.String(required=True),
        "window_end": fields.String(required=True),
        "latest_period_start": fields.String(required=True),
        "latest_period_end": fields.String(required=True),
        "latest_coverage_days": fields.Integer(required=True),
        "latest_expected_days": fields.Integer(required=True),
        "rules": fields.List(fields.Nested(AccountClassificationRuleOverviewItemModel), required=True),
    },
)
AccountClassificationRulesOverviewSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationRulesOverviewSuccessEnvelope",
    AccountClassificationRulesOverviewData,
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
    return rule_ids if rule_ids else None


@ns.route("/ledgers")
class AccountsLedgersResource(BaseResource):
    """账户台账列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountLedgersListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_accounts_ledgers_list_query_parser)
    def get(self):
        """获取账户台账列表."""
        parsed = dict(_accounts_ledgers_list_query_parser.parse_args())
        query = validate_or_raise(AccountsLedgersListQuery, parsed)
        filters: AccountFilters = query.to_filters()
        sort_field = query.sort_field
        sort_order = query.sort_order

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
    @ns.expect(_accounts_filters_query_parser)
    @api_permission_required("view")
    def get(self):
        """导出账户台账."""
        parsed = dict(_accounts_filters_query_parser.parse_args())
        query = validate_or_raise(AccountsFiltersQuery, parsed)
        filters: AccountFilters = query.to_filters()

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
    @ns.expect(_accounts_statistics_summary_query_parser)
    def get(self):
        """获取账户统计汇总."""
        parsed = _accounts_statistics_summary_query_parser.parse_args()
        instance_id = parsed.get("instance_id") if isinstance(parsed.get("instance_id"), int) else None
        db_type = parsed.get("db_type") if isinstance(parsed.get("db_type"), str) else None

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
    @ns.expect(_accounts_statistics_rules_query_parser)
    def get(self):
        """获取规则命中统计."""
        parsed = _accounts_statistics_rules_query_parser.parse_args()
        raw_rule_ids = parsed.get("rule_ids") if isinstance(parsed.get("rule_ids"), str) else None
        rule_ids = _parse_rule_ids_param(raw_rule_ids)

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


@ns.route("/statistics/classifications/trends")
class AccountClassificationTrendsResource(BaseResource):
    """账户分类趋势统计资源(全分类, 每日留痕)."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationTrendsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_account_classification_trends_query_parser)
    def get(self):
        """获取全分类趋势(未选分类时用于多折线)."""
        parsed = _account_classification_trends_query_parser.parse_args()
        raw_period_type = parsed.get("period_type")
        period_type = raw_period_type if isinstance(raw_period_type, str) else "daily"
        raw_periods = parsed.get("periods")
        periods = raw_periods if isinstance(raw_periods, int) else 7
        raw_db_type = parsed.get("db_type")
        db_type = raw_db_type if isinstance(raw_db_type, str) else None
        raw_instance_id = parsed.get("instance_id")
        instance_id = raw_instance_id if isinstance(raw_instance_id, int) else None

        def _execute():
            result = AccountClassificationDailyStatsReadService().get_all_classifications_trends(
                period_type=period_type,
                periods=periods,
                db_type=db_type,
                instance_id=instance_id,
            )
            return self.success(data=result, message="全分类趋势获取成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_all_classifications_trends",
            public_error="获取全分类趋势失败",
            context={
                "period_type": period_type,
                "periods": periods,
                "db_type": db_type,
                "instance_id": instance_id,
            },
        )


@ns.route("/statistics/classifications/trend")
class AccountClassificationTrendResource(BaseResource):
    """账户分类趋势统计资源(每日留痕)."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationTrendSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_account_classification_trend_query_parser)
    def get(self):
        """获取分类趋势(分类去重账号数)."""
        parsed = _account_classification_trend_query_parser.parse_args()
        raw_classification_id = parsed.get("classification_id")
        classification_id = raw_classification_id if isinstance(raw_classification_id, int) else None
        raw_period_type = parsed.get("period_type")
        period_type = raw_period_type if isinstance(raw_period_type, str) else "daily"
        raw_periods = parsed.get("periods")
        periods = raw_periods if isinstance(raw_periods, int) else 7
        raw_db_type = parsed.get("db_type")
        db_type = raw_db_type if isinstance(raw_db_type, str) else None
        raw_instance_id = parsed.get("instance_id")
        instance_id = raw_instance_id if isinstance(raw_instance_id, int) else None

        if not classification_id:
            raise ValidationError("classification_id 必填")

        def _execute():
            trend = AccountClassificationDailyStatsReadService().get_classification_trend(
                classification_id=classification_id,
                period_type=period_type,
                periods=periods,
                db_type=db_type,
                instance_id=instance_id,
            )
            return self.success(data={"trend": trend}, message="分类趋势获取成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_classification_trend",
            public_error="获取分类趋势失败",
            context={
                "classification_id": classification_id,
                "period_type": period_type,
                "periods": periods,
                "db_type": db_type,
                "instance_id": instance_id,
            },
        )


@ns.route("/statistics/rules/trend")
class AccountClassificationRuleTrendResource(BaseResource):
    """分类规则趋势统计资源(每日留痕)."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationTrendSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_account_classification_rule_trend_query_parser)
    def get(self):
        """获取规则趋势(规则命中账号数)."""
        parsed = _account_classification_rule_trend_query_parser.parse_args()
        raw_rule_id = parsed.get("rule_id")
        rule_id = raw_rule_id if isinstance(raw_rule_id, int) else None
        raw_period_type = parsed.get("period_type")
        period_type = raw_period_type if isinstance(raw_period_type, str) else "daily"
        raw_periods = parsed.get("periods")
        periods = raw_periods if isinstance(raw_periods, int) else 7
        raw_db_type = parsed.get("db_type")
        db_type = raw_db_type if isinstance(raw_db_type, str) else None
        raw_instance_id = parsed.get("instance_id")
        instance_id = raw_instance_id if isinstance(raw_instance_id, int) else None

        if not rule_id:
            raise ValidationError("rule_id 必填")

        def _execute():
            trend = AccountClassificationDailyStatsReadService().get_rule_trend(
                rule_id=rule_id,
                period_type=period_type,
                periods=periods,
                db_type=db_type,
                instance_id=instance_id,
            )
            return self.success(data={"trend": trend}, message="规则趋势获取成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_rule_trend",
            public_error="获取规则趋势失败",
            context={
                "rule_id": rule_id,
                "period_type": period_type,
                "periods": periods,
                "db_type": db_type,
                "instance_id": instance_id,
            },
        )


@ns.route("/statistics/rules/contributions")
class AccountClassificationRuleContributionsResource(BaseResource):
    """分类规则贡献统计资源(当前周期 Top 规则)."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationRuleContributionsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_account_classification_rule_contributions_query_parser)
    def get(self):
        """获取规则贡献(未选规则时用于柱状图)."""
        parsed = _account_classification_rule_contributions_query_parser.parse_args()
        raw_classification_id = parsed.get("classification_id")
        classification_id = raw_classification_id if isinstance(raw_classification_id, int) else None
        raw_period_type = parsed.get("period_type")
        period_type = raw_period_type if isinstance(raw_period_type, str) else "daily"
        raw_db_type = parsed.get("db_type")
        db_type = raw_db_type if isinstance(raw_db_type, str) else None
        raw_instance_id = parsed.get("instance_id")
        instance_id = raw_instance_id if isinstance(raw_instance_id, int) else None
        raw_limit = parsed.get("limit")
        limit = raw_limit if isinstance(raw_limit, int) else 10

        if not classification_id:
            raise ValidationError("classification_id 必填")

        def _execute():
            result = AccountClassificationDailyStatsReadService().get_rule_contributions(
                classification_id=classification_id,
                period_type=period_type,
                db_type=db_type,
                instance_id=instance_id,
                limit=limit,
            )
            return self.success(data=result, message="规则贡献获取成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_rule_contributions",
            public_error="获取规则贡献失败",
            context={
                "classification_id": classification_id,
                "period_type": period_type,
                "db_type": db_type,
                "instance_id": instance_id,
                "limit": limit,
            },
        )


@ns.route("/statistics/rules/overview")
class AccountClassificationRulesOverviewResource(BaseResource):
    """分类规则列表统计资源(窗口累计)."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationRulesOverviewSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_account_classification_rules_overview_query_parser)
    def get(self):
        """获取规则列表(用于左侧排序/展示)."""
        parsed = _account_classification_rules_overview_query_parser.parse_args()
        raw_classification_id = parsed.get("classification_id")
        classification_id = raw_classification_id if isinstance(raw_classification_id, int) else None
        raw_period_type = parsed.get("period_type")
        period_type = raw_period_type if isinstance(raw_period_type, str) else "daily"
        raw_periods = parsed.get("periods")
        periods = raw_periods if isinstance(raw_periods, int) else 7
        raw_db_type = parsed.get("db_type")
        db_type = raw_db_type if isinstance(raw_db_type, str) else None
        raw_instance_id = parsed.get("instance_id")
        instance_id = raw_instance_id if isinstance(raw_instance_id, int) else None
        raw_status = parsed.get("status")
        status = raw_status if isinstance(raw_status, str) else "active"

        if not classification_id:
            raise ValidationError("classification_id 必填")

        def _execute():
            result = AccountClassificationDailyStatsReadService().list_rules_overview(
                classification_id=classification_id,
                period_type=period_type,
                periods=periods,
                db_type=db_type,
                instance_id=instance_id,
                status=status,
            )
            return self.success(data=result, message="规则列表获取成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_rules_overview",
            public_error="获取规则列表失败",
            context={
                "classification_id": classification_id,
                "period_type": period_type,
                "periods": periods,
                "db_type": db_type,
                "instance_id": instance_id,
                "status": status,
            },
        )
