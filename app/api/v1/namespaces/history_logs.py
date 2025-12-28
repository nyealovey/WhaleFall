"""History logs namespace (Phase 4A 日志中心)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from flask import request
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.constants.system_constants import LogLevel
from app.errors import ValidationError
from app.routes.history.restx_models import (
    HISTORY_LOG_ITEM_FIELDS,
    HISTORY_LOG_MODULES_FIELDS,
    HISTORY_LOG_STATISTICS_FIELDS,
    HISTORY_LOG_TOP_MODULE_FIELDS,
)
from app.services.history_logs.history_logs_extras_service import HistoryLogsExtrasService
from app.services.history_logs.history_logs_list_service import HistoryLogsListService
from app.types.history_logs import LogSearchFilters
from app.utils.pagination_utils import resolve_page, resolve_page_size
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


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def _resolve_hours_param(raw_hours: str | None) -> int | None:
    if not raw_hours:
        return None
    try:
        hours = int(raw_hours)
    except ValueError as exc:
        raise ValidationError("hours 参数格式无效") from exc
    if hours < 1:
        raise ValidationError("hours 参数必须为正整数")
    max_hours = 24 * 90
    return min(hours, max_hours)


def _extract_log_search_filters(args: Mapping[str, str | None]) -> LogSearchFilters:
    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=20,
        minimum=1,
        maximum=200,
        module="history_logs",
        action="list_logs",
    )
    sort_field = (args.get("sort") or "timestamp").lower()
    sort_order = (args.get("order") or "desc").lower()
    if sort_order not in {"asc", "desc"}:
        sort_order = "desc"

    level_param = args.get("level")
    log_level = None
    if level_param:
        try:
            log_level = LogLevel(level_param.upper())
        except ValueError as exc:
            raise ValidationError("日志级别参数无效") from exc

    module_param = args.get("module")
    search_term = (args.get("search") or "").strip()
    start_time = _parse_iso_datetime(args.get("start_time"))
    end_time = _parse_iso_datetime(args.get("end_time"))
    hours = _resolve_hours_param(args.get("hours"))

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


@ns.route("/list")
class HistoryLogsListResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistoryLogsListSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            filters = _extract_log_search_filters(request.args)
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
            context={"endpoint": "logs_list"},
        )


@ns.route("/search")
class HistoryLogsSearchResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistoryLogsListSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            filters = _extract_log_search_filters(request.args)
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
                message="操作成功",
            )

        return self.safe_call(
            _execute,
            module="history_logs",
            action="search_logs",
            public_error="日志查询失败",
            expected_exceptions=(ValidationError,),
            context={"endpoint": "logs_search"},
        )


@ns.route("/statistics")
class HistoryLogStatisticsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistoryLogStatisticsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            hours = resolve_page_size(  # reuse for integer parsing with caps
                {"page_size": request.args.get("hours")},
                default=24,
                minimum=1,
                maximum=24 * 90,
            )
            result = HistoryLogsExtrasService().get_statistics(hours=hours)
            stats = marshal(result, HISTORY_LOG_STATISTICS_FIELDS)

            log_info(
                "日志统计数据已获取",
                module="history_logs",
                hours=hours,
                total_logs=stats.get("total_logs"),
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
    method_decorators = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistoryLogModulesSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
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


@ns.route("/detail/<int:log_id>")
class HistoryLogDetailResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistoryLogDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, log_id: int):
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
