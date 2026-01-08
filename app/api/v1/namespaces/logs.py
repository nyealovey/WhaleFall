"""Logs namespace (Phase 4A 日志中心)."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping
from datetime import datetime
from typing import ClassVar, cast

from flask import Response, request
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_admin_required, api_login_required, api_permission_required
from app.api.v1.restx_models.history import (
    HISTORY_LOG_ITEM_FIELDS,
    HISTORY_LOG_MODULES_FIELDS,
    HISTORY_LOG_STATISTICS_FIELDS,
    HISTORY_LOG_TOP_MODULE_FIELDS,
)
from app.constants.system_constants import LogLevel
from app.errors import ValidationError
from app.models.unified_log import UnifiedLog
from app.services.files.logs_export_service import LogsExportService
from app.services.history_logs.history_logs_extras_service import HistoryLogsExtrasService
from app.services.history_logs.history_logs_list_service import HistoryLogsListService
from app.types.history_logs import LogSearchFilters
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.spreadsheet_formula_safety import sanitize_csv_row
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

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


def _serialize_logs_to_json(logs: list[UnifiedLog]) -> Response:
    logs_data = [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "level": log.level.value if log.level else None,
            "module": log.module,
            "message": log.message,
            "traceback": log.traceback,
            "context": log.context,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    payload = {"logs": logs_data, "exported_at": time_utils.now().isoformat()}
    response = Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json; charset=utf-8",
    )
    response.headers["Content-Disposition"] = "attachment; filename=logs_export.json"
    return response


def _serialize_logs_to_csv(logs: list[UnifiedLog]) -> Response:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "时间戳", "级别", "模块", "消息", "堆栈追踪", "上下文", "创建时间"])

    for log in logs:
        timestamp_str = time_utils.format_china_time(log.timestamp) if log.timestamp else ""
        created_at_str = time_utils.format_china_time(log.created_at) if log.created_at else ""

        context_str = ""
        if log.context and isinstance(log.context, dict):
            context_parts = [
                f"{key}: {value}"
                for key, value in log.context.items()
                if value not in {None, ""}
                and key not in {"request_id", "user_id", "url", "method", "ip_address", "user_agent"}
            ]
            context_str = "; ".join(context_parts)

        writer.writerow(
            sanitize_csv_row(
                [
                    log.id,
                    timestamp_str,
                    log.level.value if log.level else "",
                    log.module or "",
                    log.message or "",
                    log.traceback or "",
                    context_str,
                    created_at_str,
                ],
            ),
        )

    output.seek(0)
    response = Response(output.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = "attachment; filename=logs_export.csv"
    return response


@ns.route("")
class HistoryLogsResource(BaseResource):
    """日志列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistoryLogsListSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取日志列表(支持 query 过滤)."""

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
    def get(self):
        """获取日志统计."""

        def _execute():
            hours = resolve_page_size(  # reuse for integer parsing with caps
                {"limit": request.args.get("hours")},
                default=24,
                minimum=1,
                maximum=24 * 90,
            )
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


@ns.route("/export")
class LogsExportResource(BaseResource):
    """日志导出资源."""

    method_decorators: ClassVar[list] = [api_admin_required]

    @ns.response(200, "OK")
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """导出日志."""
        format_type = request.args.get("format", "json")

        def _execute() -> Response:
            logs = LogsExportService().list_logs(request.args.to_dict())

            if format_type == "json":
                return _serialize_logs_to_json(logs)
            if format_type == "csv":
                return _serialize_logs_to_csv(logs)

            raise ValidationError("不支持的导出格式")

        return self.safe_call(
            _execute,
            module="logs",
            action="export_logs",
            public_error="导出日志失败",
            context={"format": format_type},
            expected_exceptions=(ValidationError,),
        )
