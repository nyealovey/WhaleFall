"""Logs namespace (Phase 4A 日志中心)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
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
from app.core.constants.system_constants import LogLevel
from app.core.exceptions import ValidationError
from app.core.types.history_logs import LogSearchFilters
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


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def _resolve_hours_param(raw_hours: int | None) -> int | None:
    if raw_hours is None:
        return None
    hours = int(raw_hours)
    if hours < 1:
        raise ValidationError("hours 参数必须为正整数")
    max_hours = 24 * 90
    return min(hours, max_hours)


def _extract_log_search_filters(parsed: Mapping[str, object]) -> LogSearchFilters:
    raw_page = parsed.get("page")
    page = max(int(raw_page) if isinstance(raw_page, int) else 1, 1)

    raw_limit = parsed.get("limit")
    limit = int(raw_limit) if isinstance(raw_limit, int) else 20
    limit = max(min(limit, 200), 1)
    sort_field = str(parsed.get("sort") or "timestamp").lower()
    sort_order = str(parsed.get("order") or "desc").lower()
    if sort_order not in {"asc", "desc"}:
        sort_order = "desc"

    level_param = parsed.get("level")
    log_level = None
    if isinstance(level_param, str) and level_param.strip():
        try:
            log_level = LogLevel(level_param.strip().upper())
        except ValueError as exc:
            raise ValidationError("日志级别参数无效") from exc

    module_value = parsed.get("module")
    module_param = module_value.strip() if isinstance(module_value, str) and module_value.strip() else None
    search_term = str(parsed.get("search") or "").strip()

    start_time_raw = parsed.get("start_time")
    end_time_raw = parsed.get("end_time")
    start_time = _parse_iso_datetime(start_time_raw if isinstance(start_time_raw, str) else None)
    end_time = _parse_iso_datetime(end_time_raw if isinstance(end_time_raw, str) else None)
    raw_hours = parsed.get("hours")
    hours = _resolve_hours_param(raw_hours if isinstance(raw_hours, int) else None)

    return LogSearchFilters(
        page=page,
        limit=limit,
        sort_field=sort_field,
        sort_order=sort_order,
        level=log_level,
        module=module_param,
        search_term=search_term,
        start_time=start_time,
        end_time=end_time,
        hours=hours,
    )


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
            filters = _extract_log_search_filters(parsed)
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
            hours = _resolve_hours_param(parsed.get("hours") if isinstance(parsed.get("hours"), int) else None) or 24
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
