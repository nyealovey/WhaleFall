"""Logs namespace (Phase 4A 日志中心)."""

from __future__ import annotations

from typing import ClassVar, cast

from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import new_parser
from app.api.v1.restx_models.history import (
    HISTORY_LOG_ITEM_FIELDS,
    HISTORY_LOG_MODULES_FIELDS,
    HISTORY_LOG_STATISTICS_FIELDS,
    HISTORY_LOG_TOP_MODULE_FIELDS,
)
from app.core.exceptions import ValidationError
from app.core.types.history_logs import LogSearchFilters
from app.schemas.history_logs_query import HistoryLogsListQuery, HistoryLogStatisticsQuery
from app.schemas.validation import validate_or_raise
from app.services.history_logs.history_logs_extras_service import HistoryLogsExtrasService
from app.services.history_logs.history_logs_list_service import HistoryLogsListService
from app.utils.structlog_config import log_info

ns = Namespace("history_logs", description="日志中心")

ErrorEnvelope = get_error_envelope_model(ns)

HistoryLogItemModel = ns.model("HistoryLogItem", HISTORY_LOG_ITEM_FIELDS)

HistoryLogsListData = ns.model(
    "HistoryLogsListData",
    {
        "items": fields.List(fields.Nested(HistoryLogItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
    },
)

HistoryLogsListSuccessEnvelope = make_success_envelope_model(ns, "HistoryLogsListSuccessEnvelope", HistoryLogsListData)

HistoryLogModulesData = ns.model("HistoryLogModulesData", HISTORY_LOG_MODULES_FIELDS)
HistoryLogModulesSuccessEnvelope = make_success_envelope_model(
    ns,
    "HistoryLogModulesSuccessEnvelope",
    HistoryLogModulesData,
)

HistoryLogTopModuleModel = ns.model("HistoryLogTopModule", HISTORY_LOG_TOP_MODULE_FIELDS)

HistoryLogStatisticsData = ns.model(
    "HistoryLogStatisticsData",
    {
        **HISTORY_LOG_STATISTICS_FIELDS,
        "top_modules": fields.List(fields.Nested(HistoryLogTopModuleModel), description="Top modules"),
    },
)

HistoryLogStatisticsSuccessEnvelope = make_success_envelope_model(
    ns,
    "HistoryLogStatisticsSuccessEnvelope",
    HistoryLogStatisticsData,
)

HistoryLogDetailData = ns.model(
    "HistoryLogDetailData",
    {
        "log": fields.Nested(HistoryLogItemModel),
    },
)

HistoryLogDetailSuccessEnvelope = make_success_envelope_model(
    ns,
    "HistoryLogDetailSuccessEnvelope",
    HistoryLogDetailData,
)

_history_logs_list_query_parser = new_parser()
_history_logs_list_query_parser.add_argument("page", type=int, default=1, location="args")
_history_logs_list_query_parser.add_argument("limit", type=int, default=20, location="args")
_history_logs_list_query_parser.add_argument("sort", type=str, default="timestamp", location="args")
_history_logs_list_query_parser.add_argument("order", type=str, default="desc", location="args")
_history_logs_list_query_parser.add_argument("level", type=str, location="args")
_history_logs_list_query_parser.add_argument("module", type=str, location="args")
_history_logs_list_query_parser.add_argument("search", type=str, default="", location="args")
_history_logs_list_query_parser.add_argument("start_time", type=str, location="args")
_history_logs_list_query_parser.add_argument("end_time", type=str, location="args")
_history_logs_list_query_parser.add_argument("hours", type=int, location="args")

_history_log_statistics_query_parser = new_parser()
_history_log_statistics_query_parser.add_argument("hours", type=int, default=24, location="args")


@ns.route("")
class HistoryLogsResource(BaseResource):
    """日志列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistoryLogsListSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_history_logs_list_query_parser)
    def get(self):
        """获取日志列表(支持 query 过滤)."""

        def _execute():
            parsed = cast("dict[str, object]", _history_logs_list_query_parser.parse_args())
            query = validate_or_raise(HistoryLogsListQuery, parsed)
            filters: LogSearchFilters = query.to_filters()
            result = HistoryLogsListService().list_logs(filters)
            items = marshal(result.items, HISTORY_LOG_ITEM_FIELDS)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                    "limit": result.limit,
                },
                message="日志列表获取成功",
            )

        return self.safe_call(
            _execute,
            module="history_logs",
            action="list_logs",
            public_error="获取日志列表失败",
            expected_exceptions=(ValidationError,),
            context={"endpoint": "logs"},
        )


@ns.route("/statistics")
class HistoryLogStatisticsResource(BaseResource):
    """历史日志统计资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistoryLogStatisticsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_history_log_statistics_query_parser)
    def get(self):
        """获取日志统计."""

        def _execute():
            parsed = _history_log_statistics_query_parser.parse_args()
            query = validate_or_raise(HistoryLogStatisticsQuery, dict(parsed))
            hours = query.hours
            result = HistoryLogsExtrasService().get_statistics(hours=hours)
            stats = cast("dict[str, object]", marshal(result, HISTORY_LOG_STATISTICS_FIELDS))
            total_logs_value = stats.get("total_logs")
            total_logs = int(total_logs_value) if isinstance(total_logs_value, (bool, int, float, str)) else None

            log_info(
                "日志统计数据已获取",
                module="history_logs",
                hours=hours,
                total_logs=total_logs,
            )

            return self.success(data=stats, message="操作成功")

        return self.safe_call(
            _execute,
            module="history_logs",
            action="get_log_statistics",
            public_error="获取日志统计失败",
            context={"endpoint": "logs_statistics"},
        )


@ns.route("/modules")
class HistoryLogModulesResource(BaseResource):
    """历史日志模块资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistoryLogModulesSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取日志模块列表."""

        def _execute():
            modules = HistoryLogsExtrasService().list_modules()
            payload = marshal({"modules": modules}, HISTORY_LOG_MODULES_FIELDS)
            return self.success(data=payload, message="操作成功")

        return self.safe_call(
            _execute,
            module="history_logs",
            action="list_log_modules",
            public_error="获取日志模块失败",
            context={"endpoint": "logs_modules"},
        )


@ns.route("/<int:log_id>")
class HistoryLogDetailResource(BaseResource):
    """历史日志详情资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistoryLogDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, log_id: int):
        """获取日志详情."""

        def _execute():
            log_entry = HistoryLogsExtrasService().get_log_detail(log_id)
            payload = marshal(log_entry, HISTORY_LOG_ITEM_FIELDS)
            return self.success(data={"log": payload}, message="操作成功")

        return self.safe_call(
            _execute,
            module="history_logs",
            action="get_log_detail",
            public_error="获取日志详情失败",
            context={"log_id": log_id},
        )
