"""日志路由入口.

统一管理日志检索、统计与下发的接口,支撑控制台与旧版前端.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast as t_cast

from flask import Blueprint, Response, render_template, request
from flask_login import login_required
from sqlalchemy import Text, asc, cast, desc, distinct, or_

from app import db
from app.constants import LOG_LEVELS, TIME_RANGES
from app.errors import ValidationError
from app.models.unified_log import LogLevel, UnifiedLog
from app.utils.query_filter_utils import get_log_modules as load_log_modules
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Mapping

    from flask_sqlalchemy.pagination import Pagination
    from sqlalchemy.orm import Query
else:
    from flask_sqlalchemy.pagination import Pagination

# 创建蓝图
history_logs_bp = Blueprint("history_logs", __name__)
# 兼容旧版 /logs 前缀请求
logs_bp = Blueprint("logs", __name__)


@dataclass(slots=True)
class LogSearchFilters:
    """日志搜索过滤条件."""

    page: int
    per_page: int
    sort_by: str
    sort_order: str
    level: LogLevel | None
    module: str | None
    search_term: str
    start_time: datetime | None
    end_time: datetime | None
    hours: int | None


@dataclass(slots=True)
class LegacyLogStatsFilters:
    """旧版日志统计过滤条件."""

    hours: int | None
    level: LogLevel | None
    module: str | None
    search_term: str | None
    since: datetime | None


@history_logs_bp.route("/")
@logs_bp.route("/")
@login_required
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
    per_page = _determine_per_page(args)
    sort_by = (args.get("sort_by") or args.get("sort") or "timestamp").lower()
    sort_order = (args.get("sort_order") or args.get("order") or "desc").lower()
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
    search_term = (args.get("q") or args.get("search") or "").strip()
    start_time = _parse_iso_datetime(args.get("start_time"))
    end_time = _parse_iso_datetime(args.get("end_time"))

    hours = _resolve_hours_param(args.get("hours"))

    return LogSearchFilters(
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
        level=log_level,
        module=module_param,
        search_term=search_term,
        start_time=start_time,
        end_time=end_time,
        hours=hours,
    )


def _determine_per_page(args: Mapping[str, str | None]) -> int:
    """根据 per_page/limit 参数推导分页大小."""
    per_page_param = args.get("per_page")
    limit_param = args.get("limit")
    per_page_source = per_page_param or limit_param
    max_per_page = 200 if (limit_param is not None and per_page_param is None) else 500
    return _safe_int(per_page_source, default=50, minimum=1, maximum=max_per_page)


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


def _apply_time_filters(
    query: Query,
    *,
    start_time: datetime | None,
    end_time: datetime | None,
    hours: int | None,
) -> Query:
    """根据时间条件限制日志查询范围."""
    updated_query = query
    if start_time:
        updated_query = updated_query.filter(UnifiedLog.timestamp >= start_time)
    if end_time:
        updated_query = updated_query.filter(UnifiedLog.timestamp <= end_time)
    if not start_time and not end_time:
        window_hours = hours if hours is not None else 24
        updated_query = updated_query.filter(UnifiedLog.timestamp >= time_utils.now() - timedelta(hours=window_hours))
    return updated_query


def _apply_log_sorting(query: Query, *, sort_by: str, sort_order: str) -> Query:
    """按指定字段排序日志结果."""
    sortable_fields = {
        "id": UnifiedLog.id,
        "timestamp": UnifiedLog.timestamp,
        "level": UnifiedLog.level,
        "module": UnifiedLog.module,
        "message": UnifiedLog.message,
    }
    order_column = sortable_fields.get(sort_by, UnifiedLog.timestamp)
    return query.order_by(asc(order_column)) if sort_order == "asc" else query.order_by(desc(order_column))


def _build_log_query(filters: LogSearchFilters) -> Query:
    """基于过滤条件组装日志查询."""
    query = UnifiedLog.query
    query = _apply_time_filters(
        query,
        start_time=filters.start_time,
        end_time=filters.end_time,
        hours=filters.hours,
    )

    if filters.level:
        query = query.filter(UnifiedLog.level == filters.level)

    if filters.module:
        query = query.filter(UnifiedLog.module.like(f"%{filters.module}%"))

    if filters.search_term:
        search_filter = or_(
            UnifiedLog.message.like(f"%{filters.search_term}%"),
            cast(UnifiedLog.context, Text).like(f"%{filters.search_term}%"),
        )
        query = query.filter(search_filter)

    return _apply_log_sorting(query, sort_by=filters.sort_by, sort_order=filters.sort_order)


def _build_paginated_logs(filters: LogSearchFilters) -> Pagination:
    """创建分页对象,供 API 序列化使用."""
    query = _build_log_query(filters)
    return t_cast(Pagination, t_cast(Any, query).paginate(page=filters.page, per_page=filters.per_page, error_out=False))


def _build_search_payload(pagination: Pagination) -> dict[str, Any]:
    """根据分页结果构造标准响应体."""
    return {
        "logs": [log_entry.to_dict() for log_entry in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
            "prev_num": pagination.prev_num if pagination.has_prev else None,
            "next_num": pagination.next_num if pagination.has_next else None,
        },
    }


def _serialize_grid_log_entry(log_entry: UnifiedLog) -> dict[str, Any]:
    """序列化 Grid.js 所需的单条日志."""
    china_timestamp = time_utils.to_china(log_entry.timestamp) if log_entry.timestamp else None
    timestamp_display = (
        time_utils.format_china_time(china_timestamp, "%Y-%m-%d %H:%M:%S") if china_timestamp else "-"
    )
    return {
        "id": log_entry.id,
        "timestamp": china_timestamp.isoformat() if china_timestamp else None,
        "timestamp_display": timestamp_display,
        "level": log_entry.level.value if log_entry.level else None,
        "module": log_entry.module,
        "message": log_entry.message,
        "traceback": log_entry.traceback,
        "context": log_entry.context,
    }


def _build_grid_payload(pagination: Pagination) -> dict[str, Any]:
    """构造 Grid.js 日志接口响应."""
    return {
        "items": [_serialize_grid_log_entry(log_entry) for log_entry in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "limit": pagination.per_page,
    }


def _extract_legacy_stats_filters(args: Mapping[str, str | None]) -> LegacyLogStatsFilters:
    """解析旧版统计接口的查询条件."""
    hours_param = args.get("hours")
    hours = None
    since = None
    if hours_param:
        try:
            hours = int(hours_param)
        except ValueError as exc:  # pragma: no cover - 输入非法时抛出
            msg = "hours 参数格式无效"
            raise ValidationError(msg) from exc
        if hours < 1:
            msg = "hours 参数必须为正整数"
            raise ValidationError(msg)
        since = time_utils.now() - timedelta(hours=hours)

    level_param = args.get("level")
    log_level = None
    if level_param:
        try:
            log_level = LogLevel(level_param.upper())
        except ValueError as exc:  # pragma: no cover - 输入非法时抛出
            msg = "日志级别参数无效"
            raise ValidationError(msg) from exc

    module_param = args.get("module")
    search_term = (args.get("q") or "").strip() or None

    return LegacyLogStatsFilters(
        hours=hours,
        level=log_level,
        module=module_param,
        search_term=search_term,
        since=since,
    )


def _apply_legacy_filters(query: Query, filters: LegacyLogStatsFilters) -> Query:
    """在查询上复用旧版接口的公共过滤条件."""
    updated_query = query
    if filters.level:
        updated_query = updated_query.filter(UnifiedLog.level == filters.level)
    if filters.module:
        updated_query = updated_query.filter(UnifiedLog.module == filters.module)
    if filters.search_term:
        updated_query = updated_query.filter(
            or_(
                UnifiedLog.message.contains(filters.search_term),
                UnifiedLog.module.contains(filters.search_term),
            ),
        )
    return updated_query


def _build_legacy_base_query(filters: LegacyLogStatsFilters) -> Query:
    """创建旧版统计的基础查询对象."""
    query = UnifiedLog.query
    if filters.since:
        query = query.filter(UnifiedLog.timestamp >= filters.since)
    return _apply_legacy_filters(query, filters)


def _count_modules_with_filters(filters: LegacyLogStatsFilters) -> int:
    """按照过滤条件计算模块数量."""
    modules_query = db.session.query(distinct(UnifiedLog.module))
    if filters.since:
        modules_query = modules_query.filter(UnifiedLog.timestamp >= filters.since)
    modules_query = _apply_legacy_filters(modules_query, filters)
    return modules_query.count()


def _aggregate_legacy_stats(filters: LegacyLogStatsFilters) -> dict[str, Any]:
    """执行旧版统计查询并返回聚合结果."""
    base_query = _build_legacy_base_query(filters)
    total_logs = base_query.count()
    error_logs = base_query.filter(UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL])).count()
    warning_logs = base_query.filter(UnifiedLog.level == LogLevel.WARNING).count()

    return {
        "total_logs": total_logs,
        "error_logs": error_logs,
        "warning_logs": warning_logs,
        "modules_count": _count_modules_with_filters(filters),
        "time_range_hours": filters.hours,
    }


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
@logs_bp.route("/api/search", methods=["GET"])
@login_required
def search_logs() -> tuple[Response, int]:
    """搜索日志 API.

    支持按日志级别、模块、关键词、时间范围等条件搜索日志.
    支持分页查询和排序.

    Query Parameters:
        page: 页码,默认 1.
        per_page: 每页数量,默认 50.
        level: 日志级别筛选.
        module: 模块筛选.
        q: 搜索关键词.
        start_time: 开始时间(ISO 格式).
        end_time: 结束时间(ISO 格式).
        hours: 最近 N 小时.

    Returns:
        包含日志列表和分页信息的 JSON 响应.

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
    pagination = _build_paginated_logs(filters)
    return jsonify_unified_success(data=_build_search_payload(pagination))


@history_logs_bp.route("/api/list", methods=["GET"])
@logs_bp.route("/api/list", methods=["GET"])
@login_required
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
    pagination = _build_paginated_logs(filters)
    payload = _build_grid_payload(pagination)
    return jsonify_unified_success(data=payload, message="日志列表获取成功")


@history_logs_bp.route("/api/statistics", methods=["GET"])
@logs_bp.route("/api/statistics", methods=["GET"])
@login_required
def get_log_statistics() -> tuple[Response, int]:
    """获取日志统计信息 API.

    Returns:
        Response: 日志统计 JSON.

    Raises:
        SystemError: 查询失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        hours = int(request.args.get("hours", 24))

        stats = UnifiedLog.get_log_statistics(hours=hours)

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
@logs_bp.route("/api/modules", methods=["GET"])
@login_required
def list_log_modules() -> tuple[Response, int]:
    """获取日志模块列表 API.

    Returns:
        Response: 模块列表 JSON.

    Raises:
        SystemError: 查询失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        modules = db.session.query(distinct(UnifiedLog.module).label("module")).order_by(UnifiedLog.module).all()

        module_list = [module.module for module in modules]

        return jsonify_unified_success(data={"modules": module_list})

    return safe_route_call(
        _execute,
        module="history_logs",
        action="list_log_modules",
        public_error="获取日志模块失败",
        context={"endpoint": "logs_modules"},
    )


@history_logs_bp.route("/api/stats", methods=["GET"])
@logs_bp.route("/api/stats", methods=["GET"])
@login_required
def get_log_stats() -> tuple[Response, int]:
    """获取日志统计 API(兼容旧前端).

    Returns:
        tuple[dict, int]: 统一成功 JSON 与状态码.

    Raises:
        ValidationError: 参数格式错误时抛出.
        SystemError: 查询失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        filters = _extract_legacy_stats_filters(request.args)
        stats = _aggregate_legacy_stats(filters)
        return jsonify_unified_success(data=stats)

    return safe_route_call(
        _execute,
        module="history_logs",
        action="get_log_stats",
        public_error="获取日志概要失败",
        context={"endpoint": "logs_stats_legacy"},
        expected_exceptions=(ValidationError,),
    )


@history_logs_bp.route("/api/detail/<int:log_id>", methods=["GET"])
@logs_bp.route("/api/detail/<int:log_id>", methods=["GET"])
@login_required
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
        log = UnifiedLog.query.get_or_404(log_id)

        return jsonify_unified_success(data={"log": log.to_dict()})

    return safe_route_call(
        _execute,
        module="history_logs",
        action="get_log_detail",
        public_error="获取日志详情失败",
        context={"log_id": log_id},
    )
