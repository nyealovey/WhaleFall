"""日志路由入口.

统一管理日志检索、统计与下发的接口,支撑控制台与旧版前端.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from flask import Blueprint, Response, render_template, request
from flask_restx import marshal

from app.constants import LOG_LEVELS, TIME_RANGES
from app.constants.system_constants import LogLevel
from app.errors import ValidationError
from app.routes.history.restx_models import HISTORY_LOG_ITEM_FIELDS, HISTORY_LOG_MODULES_FIELDS, HISTORY_LOG_STATISTICS_FIELDS
from app.services.history_logs.history_logs_extras_service import HistoryLogsExtrasService
from app.services.history_logs.history_logs_list_service import HistoryLogsListService
from app.types.history_logs import LogSearchFilters
from app.utils.decorators import admin_required
from app.utils.pagination_utils import resolve_page_size
from app.utils.query_filter_utils import get_log_modules as load_log_modules
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info

# 创建蓝图
history_logs_bp = Blueprint("history_logs", __name__)


@history_logs_bp.route("/")
@admin_required
def logs_dashboard() -> str | tuple[dict, int]:
    """日志中心仪表板.

    渲染日志查询和展示页面,提供日志级别、模块和时间范围的筛选选项.

    Returns:
        渲染的日志仪表板 HTML 页面.

    Raises:
        SystemError: 当页面加载失败时抛出.

    """

    def _render() -> str:
        module_values = load_log_modules()
        module_options = [{"value": value, "label": value} for value in module_values]
        return render_template(
            "history/logs/logs.html",
            log_level_options=LOG_LEVELS,
            module_options=module_options,
            time_range_options=TIME_RANGES,
        )

    return safe_route_call(
        _render,
        module="history_logs",
        action="logs_dashboard",
        public_error="日志仪表盘加载失败",
        context={"endpoint": "logs_dashboard"},
    )


def _extract_log_search_filters(args: Mapping[str, str | None]) -> LogSearchFilters:
    """解析请求参数并转换为结构化的搜索条件."""
    page = _safe_int(args.get("page"), default=1, minimum=1)
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
        except ValueError as exc:  # pragma: no cover - 输入非法时抛出
            msg = "日志级别参数无效"
            raise ValidationError(msg) from exc

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


def _resolve_hours_param(raw_hours: str | None) -> int | None:
    """验证 hours 参数并收敛至最大范围."""
    if not raw_hours:
        return None
    try:
        hours = int(raw_hours)
    except ValueError as exc:  # pragma: no cover - 输入非法时抛出
        msg = "hours 参数格式无效"
        raise ValidationError(msg) from exc
    if hours < 1:
        msg = "hours 参数必须为正整数"
        raise ValidationError(msg)
    max_hours = 24 * 90
    return min(hours, max_hours)


def _safe_int(value: str | None, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
    """安全地将字符串转换为整数并裁剪到范围.

    Args:
        value: 原始字符串值.
        default: 转换失败时使用的默认值.
        minimum: 最小值.
        maximum: 可选最大值.

    Returns:
        int: 转换后的整数.

    """
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    if parsed < minimum:
        return minimum
    if maximum is not None and parsed > maximum:
        return maximum
    return parsed


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    """解析 ISO 格式时间字符串.

    Args:
        raw_value: ISO 格式字符串,可为 None.

    Returns:
        datetime | None: 解析成功返回 datetime,否则 None.

    """
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


@history_logs_bp.route("/api/search", methods=["GET"])
@admin_required
def search_logs() -> tuple[Response, int]:
    """搜索日志 API.

    支持按日志级别、模块、关键词、时间范围等条件搜索日志.
    支持分页查询和排序.

    Query Parameters:
        page: 页码,默认 1.
        page_size: 每页数量,默认 20,最大 200(兼容 limit/pageSize).
        level: 日志级别筛选.
        module: 模块筛选.
        search: 搜索关键词.
        start_time: 开始时间(ISO 格式).
        end_time: 结束时间(ISO 格式).
        hours: 最近 N 小时.
        sort: 排序字段(id/timestamp/level/module/message),默认 timestamp.
        order: 排序方向(asc/desc),默认 desc.

    Returns:
        包含 Grid 风格分页字段的 JSON 响应.

    Raises:
        ValidationError: 当参数验证失败时抛出.
        SystemError: 当查询失败时抛出.

    """
    return safe_route_call(
        _search_logs_impl,
        module="history_logs",
        action="search_logs",
        public_error="日志查询失败",
        context={"endpoint": "logs_search"},
        expected_exceptions=(ValidationError,),
    )


def _search_logs_impl() -> tuple[Response, int]:
    filters = _extract_log_search_filters(request.args)
    result = HistoryLogsListService().list_logs(filters)
    items = marshal(result.items, HISTORY_LOG_ITEM_FIELDS)
    return jsonify_unified_success(
        data={
            "items": items,
            "total": result.total,
            "page": result.page,
            "pages": result.pages,
            "limit": result.limit,
        },
    )


@history_logs_bp.route("/api/list", methods=["GET"])
@admin_required
def list_logs() -> tuple[Response, int]:
    """Grid.js 日志列表 API.

    Returns:
        Response: 包含分页日志数据的 JSON.

    Raises:
        ValidationError: 参数校验失败时抛出.
        SystemError: 查询或序列化失败时抛出.

    """
    return safe_route_call(
        _list_logs_impl,
        module="history_logs",
        action="list_logs",
        public_error="获取日志列表失败",
        context={"endpoint": "logs_list"},
        expected_exceptions=(ValidationError,),
    )


def _list_logs_impl() -> tuple[Response, int]:
    filters = _extract_log_search_filters(request.args)
    result = HistoryLogsListService().list_logs(filters)
    items = marshal(result.items, HISTORY_LOG_ITEM_FIELDS)
    payload = {
        "items": items,
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
        "limit": result.limit,
    }
    return jsonify_unified_success(data=payload, message="日志列表获取成功")


@history_logs_bp.route("/api/statistics", methods=["GET"])
@admin_required
def get_log_statistics() -> tuple[Response, int]:
    """获取日志统计信息 API.

    Returns:
        Response: 日志统计 JSON.

    Raises:
        SystemError: 查询失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        hours = _safe_int(request.args.get("hours"), default=24, minimum=1, maximum=24 * 90)
        result = HistoryLogsExtrasService().get_statistics(hours=hours)
        stats = marshal(result, HISTORY_LOG_STATISTICS_FIELDS)

        log_info(
            "日志统计数据已获取",
            module="history_logs",
            hours=hours,
            total_logs=stats["total_logs"],
        )

        return jsonify_unified_success(data=stats)

    return safe_route_call(
        _execute,
        module="history_logs",
        action="get_log_statistics",
        public_error="获取日志统计失败",
        context={"endpoint": "logs_statistics"},
    )


@history_logs_bp.route("/api/modules", methods=["GET"])
@admin_required
def list_log_modules() -> tuple[Response, int]:
    """获取日志模块列表 API.

    Returns:
        Response: 模块列表 JSON.

    Raises:
        SystemError: 查询失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        modules = HistoryLogsExtrasService().list_modules()
        payload = marshal({"modules": modules}, HISTORY_LOG_MODULES_FIELDS)
        return jsonify_unified_success(data=payload)

    return safe_route_call(
        _execute,
        module="history_logs",
        action="list_log_modules",
        public_error="获取日志模块失败",
        context={"endpoint": "logs_modules"},
    )


@history_logs_bp.route("/api/detail/<int:log_id>", methods=["GET"])
@admin_required
def get_log_detail(log_id: int) -> tuple[Response, int]:
    """获取日志详情 API.

    Args:
        log_id: 日志记录 ID.

    Returns:
        tuple[dict, int]: 日志详情 JSON 与状态码.

    Raises:
        SystemError: 查询失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        log_entry = HistoryLogsExtrasService().get_log_detail(log_id)
        payload = marshal(log_entry, HISTORY_LOG_ITEM_FIELDS)
        return jsonify_unified_success(data={"log": payload})

    return safe_route_call(
        _execute,
        module="history_logs",
        action="get_log_detail",
        public_error="获取日志详情失败",
        context={"log_id": log_id},
    )
