"""AccountChangeLogs namespace (账户变更历史)."""

from __future__ import annotations

from typing import ClassVar, cast

from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import new_parser
from app.api.v1.restx_models.account_change_logs import (
    ACCOUNT_CHANGE_LOG_DETAIL_FIELDS,
    ACCOUNT_CHANGE_LOG_LIST_ITEM_FIELDS,
    ACCOUNT_CHANGE_LOG_STATISTICS_FIELDS,
)
from app.core.exceptions import ValidationError
from app.schemas.account_change_logs_query import AccountChangeLogsListQuery, AccountChangeLogStatisticsQuery
from app.schemas.validation import validate_or_raise
from app.services.history_account_change_logs.history_account_change_logs_read_service import (
    HistoryAccountChangeLogsReadService,
)

ns = Namespace("account_change_logs", description="账户变更历史")

ErrorEnvelope = get_error_envelope_model(ns)

AccountChangeLogListItemModel = ns.model("AccountChangeLogListItem", ACCOUNT_CHANGE_LOG_LIST_ITEM_FIELDS)

AccountChangeLogsListData = ns.model(
    "AccountChangeLogsListData",
    {
        "items": fields.List(fields.Nested(AccountChangeLogListItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
    },
)

AccountChangeLogsListSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountChangeLogsListSuccessEnvelope",
    AccountChangeLogsListData,
)

AccountChangeLogStatisticsData = ns.model("AccountChangeLogStatisticsData", ACCOUNT_CHANGE_LOG_STATISTICS_FIELDS)
AccountChangeLogStatisticsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountChangeLogStatisticsSuccessEnvelope",
    AccountChangeLogStatisticsData,
)

AccountChangeLogDetailModel = ns.model("AccountChangeLogDetail", ACCOUNT_CHANGE_LOG_DETAIL_FIELDS)
AccountChangeLogDetailData = ns.model(
    "AccountChangeLogDetailData",
    {
        "log": fields.Nested(AccountChangeLogDetailModel),
    },
)
AccountChangeLogDetailSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountChangeLogDetailSuccessEnvelope",
    AccountChangeLogDetailData,
)

_account_change_logs_list_query_parser = new_parser()
_account_change_logs_list_query_parser.add_argument("page", type=int, default=1, location="args")
_account_change_logs_list_query_parser.add_argument("limit", type=int, default=20, location="args")
_account_change_logs_list_query_parser.add_argument("sort", type=str, default="change_time", location="args")
_account_change_logs_list_query_parser.add_argument("order", type=str, default="desc", location="args")
_account_change_logs_list_query_parser.add_argument("search", type=str, default="", location="args")
_account_change_logs_list_query_parser.add_argument("instance_id", type=int, location="args")
_account_change_logs_list_query_parser.add_argument("db_type", type=str, location="args")
_account_change_logs_list_query_parser.add_argument("change_type", type=str, location="args")
_account_change_logs_list_query_parser.add_argument("status", type=str, location="args")
_account_change_logs_list_query_parser.add_argument("hours", type=int, location="args")

_account_change_logs_statistics_query_parser = new_parser()
_account_change_logs_statistics_query_parser.add_argument("hours", type=int, location="args")


@ns.route("")
class AccountChangeLogsResource(BaseResource):
    """账户变更日志列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountChangeLogsListSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_account_change_logs_list_query_parser)
    def get(self):
        """获取账户变更日志列表(支持 query 过滤)."""

        def _execute():
            parsed = cast("dict[str, object]", _account_change_logs_list_query_parser.parse_args())
            query = validate_or_raise(AccountChangeLogsListQuery, parsed)
            filters = query.to_filters()
            result = HistoryAccountChangeLogsReadService().list_logs(filters)
            items = marshal(result.items, ACCOUNT_CHANGE_LOG_LIST_ITEM_FIELDS)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                    "limit": result.limit,
                },
                message="获取账户变更历史成功",
            )

        return self.safe_call(
            _execute,
            module="account_change_logs",
            action="list_logs",
            public_error="获取账户变更历史失败",
            expected_exceptions=(ValidationError,),
            context={"endpoint": "account_change_logs"},
        )


@ns.route("/statistics")
class AccountChangeLogsStatisticsResource(BaseResource):
    """账户变更日志统计资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountChangeLogStatisticsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_account_change_logs_statistics_query_parser)
    def get(self):
        """获取账户变更日志统计."""

        def _execute():
            parsed = cast("dict[str, object]", _account_change_logs_statistics_query_parser.parse_args())
            query = validate_or_raise(AccountChangeLogStatisticsQuery, parsed)
            stats = HistoryAccountChangeLogsReadService().get_statistics(hours=query.hours)
            payload = cast("dict[str, object]", marshal(stats, ACCOUNT_CHANGE_LOG_STATISTICS_FIELDS))
            return self.success(data=payload, message="操作成功")

        return self.safe_call(
            _execute,
            module="account_change_logs",
            action="get_statistics",
            public_error="获取账户变更统计失败",
            expected_exceptions=(ValidationError,),
            context={"endpoint": "account_change_logs_statistics"},
        )


@ns.route("/<int:log_id>")
class AccountChangeLogDetailResource(BaseResource):
    """账户变更日志详情资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountChangeLogDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, log_id: int):
        """获取单条变更日志详情."""

        def _execute():
            result = HistoryAccountChangeLogsReadService().get_log_detail(log_id)
            payload = marshal(result, {"log": fields.Nested(AccountChangeLogDetailModel)})
            return self.success(data=payload, message="获取变更日志详情成功")

        return self.safe_call(
            _execute,
            module="account_change_logs",
            action="get_log_detail",
            public_error="获取变更日志详情失败",
            context={"log_id": log_id},
        )
