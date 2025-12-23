"""分区管理 API 路由."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, cast

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.errors import ValidationError
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.services.partition_management_service import PartitionManagementService
from app.services.statistics.partition_statistics_service import PartitionStatisticsService
from app.types import RouteReturn
from app.utils.decorators import admin_required, require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info, log_warning
from app.utils.time_utils import time_utils

# 创建蓝图
partition_bp = Blueprint("partition", __name__)


@dataclass(slots=True)
class PeriodWindow:
    """核心指标查询窗口."""

    period_start: date
    period_end: date
    stats_start: date
    stats_end: date
    step_mode: str


# 页面路由
@partition_bp.route("/", methods=["GET"])
@login_required
@view_required
def partitions_page() -> RouteReturn:
    """分区管理页面.

    Returns:
        渲染的分区管理页面.

    """
    return render_template("admin/partitions/index.html")


# API 路由
@partition_bp.route("/api/info", methods=["GET"])
@login_required
@view_required
def get_partition_info() -> RouteReturn:
    """获取分区信息 API.

    Returns:
        JSON 响应,包含分区信息、状态和缺失分区列表.

    """
    log_info("开始获取分区信息", module="partition", user_id=getattr(current_user, "id", None))
    stats_service = PartitionStatisticsService()
    result = stats_service.get_partition_info()
    status_snapshot = _build_partition_status(stats_service, partition_info=result)
    result["status"] = status_snapshot.get("status", "healthy")
    result["missing_partitions"] = status_snapshot.get("missing_partitions", [])
    payload = {
        "data": result,
        "timestamp": time_utils.now().isoformat(),
    }
    log_info("分区信息获取成功", module="partition")
    return jsonify_unified_success(data=payload, message="分区信息获取成功")


# API 路由


def _safe_int(value: str | None, default: int, *, minimum: int = 1, maximum: int = 100) -> int:
    """解析并限制整数参数范围.

    Args:
        value: 待解析的字符串值.
        default: 默认值.
        minimum: 最小值,默认 1.
        maximum: 最大值,默认 100.

    Returns:
        解析后的整数,限制在 [minimum, maximum] 范围内.

    """
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


def _normalize_period_type(requested: str) -> str:
    """校验周期类型,非法时直接抛出校验错误."""
    valid = {"daily", "weekly", "monthly", "quarterly"}
    if requested not in valid:
        msg = "不支持的周期类型"
        raise ValidationError(msg)
    return requested


def _add_months(base_date: date, months: int) -> date:
    """以月份步长调整日期."""
    month = base_date.month - 1 + months
    year = base_date.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


def _period_end(start_date: date, months: int) -> date:
    """计算周期结束日期(闭区间)."""
    return _add_months(start_date, months) - timedelta(days=1)


def _resolve_period_window(period_type: str, days: int, today: date) -> PeriodWindow:
    """根据周期类型推导统计窗口."""
    days = max(days, 1)
    if period_type == "daily":
        stats_end = today
        stats_start = stats_end - timedelta(days=days - 1)
        return PeriodWindow(
            period_start=stats_start,
            period_end=stats_end,
            stats_start=stats_start,
            stats_end=stats_end,
            step_mode="daily",
        )

    if period_type == "weekly":
        week_start = today - timedelta(days=today.weekday())
        period_end = week_start
        period_start = week_start - timedelta(weeks=days - 1)
        stats_end = period_end + timedelta(days=6)
        return PeriodWindow(
            period_start=period_start,
            period_end=period_end,
            stats_start=period_start,
            stats_end=stats_end,
            step_mode="weekly",
        )

    if period_type == "monthly":
        month_start = today.replace(day=1)
        period_end = month_start
        period_start = _add_months(month_start, -(days - 1))
        stats_end = _period_end(period_end, 1)
        return PeriodWindow(
            period_start=period_start,
            period_end=period_end,
            stats_start=period_start,
            stats_end=stats_end,
            step_mode="monthly",
        )

    quarter_month = ((today.month - 1) // 3) * 3 + 1
    quarter_start = date(today.year, quarter_month, 1)
    period_end = quarter_start
    period_start = _add_months(quarter_start, -3 * (days - 1))
    stats_end = _period_end(period_end, 3)
    return PeriodWindow(
        period_start=period_start,
        period_end=period_end,
        stats_start=period_start,
        stats_end=stats_end,
        step_mode="quarterly",
    )


def _load_core_metric_records(
    period_type: str,
    window: PeriodWindow,
) -> tuple[dict[date, int], dict[date, int], dict[date, int], dict[date, int]]:
    """加载核心指标需要的聚合与统计计数.

    仅返回按日期/周期分组后的计数,避免对大表执行 ``.all()`` 拉全量.
    """
    db_aggs_rows = (
        DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.period_type == period_type,
            DatabaseSizeAggregation.period_start >= window.period_start,
            DatabaseSizeAggregation.period_start <= window.period_end,
        )
        .with_entities(
            DatabaseSizeAggregation.period_start,
            func.count(DatabaseSizeAggregation.id),
        )
        .group_by(DatabaseSizeAggregation.period_start)
        .all()
    )
    db_aggs = {period_start: int(count) for period_start, count in db_aggs_rows}

    instance_aggs_rows = (
        InstanceSizeAggregation.query.filter(
            InstanceSizeAggregation.period_type == period_type,
            InstanceSizeAggregation.period_start >= window.period_start,
            InstanceSizeAggregation.period_start <= window.period_end,
        )
        .with_entities(
            InstanceSizeAggregation.period_start,
            func.count(InstanceSizeAggregation.id),
        )
        .group_by(InstanceSizeAggregation.period_start)
        .all()
    )
    instance_aggs = {period_start: int(count) for period_start, count in instance_aggs_rows}

    db_stats_rows = (
        DatabaseSizeStat.query.filter(
            DatabaseSizeStat.collected_date >= window.stats_start,
            DatabaseSizeStat.collected_date <= window.stats_end,
        )
        .with_entities(
            DatabaseSizeStat.collected_date,
            func.count(DatabaseSizeStat.id),
        )
        .group_by(DatabaseSizeStat.collected_date)
        .all()
    )
    db_stats = {collected_date: int(count) for collected_date, count in db_stats_rows}

    instance_stats_rows = (
        InstanceSizeStat.query.filter(
            InstanceSizeStat.collected_date >= window.stats_start,
            InstanceSizeStat.collected_date <= window.stats_end,
        )
        .with_entities(
            InstanceSizeStat.collected_date,
            func.count(InstanceSizeStat.id),
        )
        .group_by(InstanceSizeStat.collected_date)
        .all()
    )
    instance_stats = {collected_date: int(count) for collected_date, count in instance_stats_rows}

    return db_aggs, instance_aggs, db_stats, instance_stats


def _build_daily_metrics(
    window: PeriodWindow,
    db_stats: dict[date, int],
    instance_stats: dict[date, int],
    db_aggs: dict[date, int],
    instance_aggs: dict[date, int],
) -> defaultdict[str, dict[str, float]]:
    """将原始记录合并为以日期为 key 的指标字典."""
    metrics: defaultdict[str, dict[str, float]] = defaultdict(
        lambda: {
            "instance_count": 0.0,
            "database_count": 0.0,
            "instance_aggregation_count": 0.0,
            "database_aggregation_count": 0.0,
        },
    )

    for collected_date, count in db_stats.items():
        metrics[collected_date.isoformat()]["database_count"] = float(count)

    for collected_date, count in instance_stats.items():
        metrics[collected_date.isoformat()]["instance_count"] = float(count)

    for period_start, count in db_aggs.items():
        metrics[period_start.isoformat()]["database_aggregation_count"] = float(count)

    for period_start, count in instance_aggs.items():
        metrics[period_start.isoformat()]["instance_aggregation_count"] = float(count)

    if window.step_mode != "daily":
        _rollup_period_metrics(window, metrics)

    return metrics


def _rollup_period_metrics(window: PeriodWindow, daily_metrics: defaultdict[str, dict[str, float]]) -> None:
    """当周期为周/月/季时,将每日数据聚合到各周期."""
    buckets: defaultdict[str, dict[str, float]] = defaultdict(
        lambda: {
            "instance_count": 0.0,
            "database_count": 0.0,
            "instance_aggregation_count": 0.0,
            "database_aggregation_count": 0.0,
            "days_in_period": 0.0,
        },
    )

    for date_str, values in list(daily_metrics.items()):
        parsed = time_utils.to_china(f"{date_str}T00:00:00")
        if parsed is None:
            continue
        source_date = parsed.date()
        if window.step_mode == "weekly":
            key_date = source_date - timedelta(days=source_date.weekday())
        elif window.step_mode == "monthly":
            key_date = source_date.replace(day=1)
        else:
            quarter_month = ((source_date.month - 1) // 3) * 3 + 1
            key_date = source_date.replace(month=quarter_month, day=1)

        bucket = buckets[key_date.isoformat()]
        bucket["instance_count"] += values["instance_count"]
        bucket["database_count"] += values["database_count"]
        bucket["instance_aggregation_count"] += values["instance_aggregation_count"]
        bucket["database_aggregation_count"] += values["database_aggregation_count"]
        bucket["days_in_period"] += 1

    daily_metrics.clear()
    for key, values in buckets.items():
        if values["days_in_period"] <= 0:
            continue
        daily_metrics[key] = {
            "instance_count": round(values["instance_count"] / values["days_in_period"], 1),
            "database_count": round(values["database_count"] / values["days_in_period"], 1),
            "instance_aggregation_count": values["instance_aggregation_count"],
            "database_aggregation_count": values["database_aggregation_count"],
        }


def _compose_chart_payload(
    period_type: str,
    window: PeriodWindow,
    daily_metrics: defaultdict[str, dict[str, float]],
) -> tuple[list[str], list[dict[str, Any]], str]:
    """基于每日指标构建 labels/datasets/time_range."""
    labels: list[str] = []
    instance_count_data: list[float] = []
    database_count_data: list[float] = []
    instance_aggregation_data: list[float] = []
    database_aggregation_data: list[float] = []

    cursor = window.stats_start if window.step_mode == "daily" else window.period_start
    limit_date = window.stats_end if window.step_mode == "daily" else window.period_end

    while cursor <= limit_date:
        key = cursor.isoformat()
        display_date = _display_label_date(cursor, window).isoformat()
        labels.append(display_date)
        values = daily_metrics.get(
            key,
            {
                "instance_count": 0.0,
                "database_count": 0.0,
                "instance_aggregation_count": 0.0,
                "database_aggregation_count": 0.0,
            },
        )
        instance_count_data.append(values["instance_count"])
        database_count_data.append(values["database_count"])
        instance_aggregation_data.append(values["instance_aggregation_count"])
        database_aggregation_data.append(values["database_aggregation_count"])

        if window.step_mode == "weekly":
            cursor += timedelta(weeks=1)
        elif window.step_mode == "monthly":
            cursor = _add_months(cursor, 1)
        elif window.step_mode == "quarterly":
            cursor = _add_months(cursor, 3)
        else:
            cursor += timedelta(days=1)

    instance_label, database_label, inst_agg_label, db_agg_label = _resolve_dataset_labels(period_type)

    datasets = [
        {
            "label": instance_label,
            "data": instance_count_data,
            "borderColor": "rgba(54, 162, 235, 0.7)",
            "backgroundColor": "rgba(54, 162, 235, 0.1)",
            "borderWidth": 4,
            "pointStyle": "circle",
            "tension": 0.1,
            "fill": False,
        },
        {
            "label": inst_agg_label,
            "data": instance_aggregation_data,
            "borderColor": "rgba(255, 99, 132, 0.7)",
            "backgroundColor": "rgba(255, 99, 132, 0.05)",
            "borderWidth": 3,
            "pointStyle": "triangle",
            "tension": 0.1,
            "fill": False,
        },
        {
            "label": database_label,
            "data": database_count_data,
            "borderColor": "rgba(75, 192, 192, 0.7)",
            "backgroundColor": "rgba(75, 192, 192, 0.1)",
            "borderWidth": 4,
            "pointStyle": "rect",
            "tension": 0.1,
            "fill": False,
        },
        {
            "label": db_agg_label,
            "data": database_aggregation_data,
            "borderColor": "rgba(255, 159, 64, 0.7)",
            "backgroundColor": "rgba(255, 159, 64, 0.05)",
            "borderWidth": 3,
            "pointStyle": "star",
            "tension": 0.1,
            "fill": False,
        },
    ]

    time_range = "-"
    if labels:
        time_range = f"{labels[0]} - {labels[-1]}"

    return labels, datasets, time_range


def _display_label_date(source: date, window: PeriodWindow) -> date:
    """根据 step_mode 决定标签日期."""
    if window.step_mode == "daily":
        return source
    if window.step_mode == "weekly":
        return source + timedelta(days=6)
    if window.step_mode == "monthly":
        return _period_end(source, 1)
    if window.step_mode == "quarterly":
        return _period_end(source, 3)
    return source


def _resolve_dataset_labels(period_type: str) -> tuple[str, str, str, str]:
    """返回不同周期类型的图表标签文本."""
    mapping = {
        "daily": ("实例数总量", "数据库数总量", "实例日统计数量", "数据库日统计数量"),
        "weekly": ("实例数平均值(周)", "数据库数平均值(周)", "实例周统计数量", "数据库周统计数量"),
        "monthly": ("实例数平均值(月)", "数据库数平均值(月)", "实例月统计数量", "数据库月统计数量"),
        "quarterly": ("实例数平均值(季)", "数据库数平均值(季)", "实例季统计数量", "数据库季统计数量"),
    }
    return mapping.get(
        period_type,
        ("实例数总量", "数据库数总量", "实例统计数量", "数据库统计数量"),
    )
def _build_partition_status(
    stats_service: PartitionStatisticsService,
    partition_info: dict[str, object] | None = None,
) -> dict[str, object]:
    """构建分区状态信息.

    Args:
        stats_service: 分区统计服务实例.
        partition_info: 已获取的分区信息,缺省时内部拉取.

    Returns:
        dict[str, object]: 包含状态、缺失分区等信息的字典.

    """
    info = partition_info or stats_service.get_partition_info()
    raw_partitions = info.get("partitions") or []
    partitions: list[dict[str, object]] = list(raw_partitions) if isinstance(raw_partitions, Iterable) else []

    current_date = time_utils.now().date()
    required_partitions: list[str] = []
    for offset in range(3):
        month_date = (current_date.replace(day=1) + timedelta(days=offset * 32)).replace(day=1)
        required_partitions.append(
            f"database_size_stats_{time_utils.format_china_time(month_date, '%Y_%m')}",
        )

    existing_partitions = {partition["name"] for partition in partitions}
    missing_partitions = [name for name in required_partitions if name not in existing_partitions]

    status = "healthy" if not missing_partitions else "warning"
    return {
        "status": status,
        "total_partitions": info.get("total_partitions", 0),
        "total_size": info.get("total_size", "0 B"),
        "total_records": info.get("total_records", 0),
        "missing_partitions": missing_partitions,
        "partitions": partitions,
    }


@partition_bp.route("/api/status", methods=["GET"])
@login_required
@view_required
def get_partition_status() -> RouteReturn:
    """获取分区管理状态.

    检查分区健康状态,包括缺失分区检测.

    Returns:
        JSON 响应,包含分区状态、总数、大小和缺失分区列表.

    Raises:
        SystemError: 当获取状态失败时抛出.

    """

    def _execute() -> RouteReturn:
        stats_service = PartitionStatisticsService()
        result = _build_partition_status(stats_service)
        status_value = str(result.get("status", "unknown"))
        missing_partitions_raw = result.get("missing_partitions") or []
        missing_partitions = [str(item) for item in cast(list[object], missing_partitions_raw)]

        if status_value != "healthy":
            log_warning(
                "分区状态存在告警",
                module="partition",
                status=status_value,
                missing_partitions=missing_partitions,
            )

        payload = {
            "data": result,
            "timestamp": time_utils.now().isoformat(),
        }
        log_info("获取分区状态成功", module="partition")
        return jsonify_unified_success(data=payload, message="分区状态获取成功")

    return safe_route_call(
        _execute,
        module="partition",
        action="get_partition_status",
        public_error="获取分区管理状态失败",
    )


@partition_bp.route("/api/partitions", methods=["GET"])
@login_required
@view_required
def list_partitions() -> RouteReturn:
    """分页返回分区列表,供 Grid.js 使用.

    支持分页、排序、搜索和筛选(按表类型、状态).

    Returns:
        JSON 响应,包含分区列表和分页信息.

    Query Parameters:
        page: 页码,默认 1.
        limit: 每页数量,默认 20,最大 200.
        sort: 排序字段,默认 'name'.
        order: 排序方向('asc'、'desc'),默认 'asc'.
        search: 搜索关键词,可选.
        table_type: 表类型筛选,可选.
        status: 状态筛选,可选.

    """
    stats_service = PartitionStatisticsService()
    partition_info = stats_service.get_partition_info()
    partitions = list(partition_info.get("partitions", []))

    search_term = (request.args.get("search") or "").strip().lower()
    table_type = (request.args.get("table_type") or "").strip().lower()
    status_filter = (request.args.get("status") or "").strip().lower()

    if table_type:
        partitions = [
            partition for partition in partitions if (partition.get("table_type") or "").lower() == table_type
        ]

    if status_filter:
        partitions = [partition for partition in partitions if (partition.get("status") or "").lower() == status_filter]

    if search_term:
        partitions = [
            partition
            for partition in partitions
            if search_term in (partition.get("name") or "").lower()
            or search_term in (partition.get("display_name") or "").lower()
        ]

    sort_field = (request.args.get("sort") or "name").lower()
    sort_order = (request.args.get("order") or "asc").lower()
    sortable_fields = {
        "name": lambda item: (item.get("name") or "").lower(),
        "table_type": lambda item: (item.get("table_type") or "").lower(),
        "size": lambda item: item.get("size_bytes") or 0,
        "size_bytes": lambda item: item.get("size_bytes") or 0,
        "record_count": lambda item: item.get("record_count") or 0,
        "status": lambda item: (item.get("status") or "").lower(),
        "date": lambda item: item.get("date") or "",
    }
    sort_resolver = sortable_fields.get(sort_field, sortable_fields["date"])
    partitions.sort(key=sort_resolver, reverse=(sort_order == "desc"))

    limit = _safe_int(request.args.get("limit"), default=20, minimum=1, maximum=200)
    total = len(partitions)
    pages = max((total + limit - 1) // limit, 1)
    page = _safe_int(request.args.get("page"), default=1, minimum=1, maximum=pages)

    start = (page - 1) * limit
    end = start + limit
    items = partitions[start:end]

    payload = {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "limit": limit,
    }

    log_info(
        "获取分区列表成功",
        module="partition",
        total=total,
        page=page,
        limit=limit,
    )
    return jsonify_unified_success(data=payload, message="分区列表获取成功")


@partition_bp.route("/api/create", methods=["POST"])
@login_required
@admin_required
@require_csrf
def create_partition() -> RouteReturn:
    """创建分区任务.

    Returns:
        Response: 包含分区创建结果的 JSON 响应.

    """
    data = request.get_json() or {}
    partition_date_str = data.get("date")

    if not partition_date_str:
        msg = "缺少日期参数"
        raise ValidationError(msg)

    try:
        parsed_dt = time_utils.to_china(partition_date_str + "T00:00:00")
    except Exception as exc:
        msg = "日期格式错误,请使用 YYYY-MM-DD 格式"
        raise ValidationError(msg) from exc
    if parsed_dt is None:
        msg = "无法解析日期"
        raise ValidationError(msg)
    partition_date = parsed_dt.date()

    today = time_utils.now_china().date()
    current_month_start = today.replace(day=1)
    if partition_date < current_month_start:
        msg = "只能创建当前或未来月份的分区"
        raise ValidationError(msg)

    service = PartitionManagementService()
    result = service.create_partition(partition_date)

    payload = {
        "result": result,
        "timestamp": time_utils.now().isoformat(),
    }

    log_info(
        "创建分区成功",
        module="partition",
        partition_date=str(partition_date),
        user_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(data=payload, message="分区创建任务已触发")


@partition_bp.route("/api/cleanup", methods=["POST"])
@login_required
@admin_required
@require_csrf
def cleanup_partitions() -> RouteReturn:
    """清理旧分区.

    Returns:
        Response: 包含清理任务执行结果的 JSON 响应.

    """
    data = request.get_json() or {}
    raw_retention = data.get("retention_months", 12)
    try:
        retention_months = int(raw_retention)
    except (TypeError, ValueError) as exc:
        msg = "retention_months 必须为数字"
        raise ValidationError(msg) from exc

    service = PartitionManagementService()
    result = service.cleanup_old_partitions(retention_months=retention_months)

    payload = {
        "result": result,
        "timestamp": time_utils.now().isoformat(),
    }

    log_info(
        "清理旧分区成功",
        module="partition",
        retention_months=retention_months,
        user_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(data=payload, message="旧分区清理任务已触发")


@partition_bp.route("/api/statistics", methods=["GET"])
@login_required
@view_required
def get_partition_statistics() -> RouteReturn:
    """获取分区统计信息.

    Returns:
        JSON 响应,包含分区统计数据.

    """
    service = PartitionStatisticsService()
    result = service.get_partition_statistics()

    payload = {
        "data": result,
        "timestamp": time_utils.now().isoformat(),
    }

    log_info("获取分区统计信息成功", module="partition")
    return jsonify_unified_success(data=payload, message="分区统计信息获取成功")


@partition_bp.route("/api/aggregations/core-metrics", methods=["GET"])
@login_required
@view_required
def get_core_aggregation_metrics() -> RouteReturn:
    """获取核心聚合指标数据.

    Returns:
        Response: 包含周期指标与统计曲线的 JSON.

    Raises:
        SystemError: 数据查询失败时抛出.

    """
    requested_period_type = (request.args.get("period_type") or "daily").lower()
    requested_days = request.args.get("days", 7, type=int)

    def _execute() -> RouteReturn:
        normalized_type = _normalize_period_type(requested_period_type)

        today_china = time_utils.now_china().date()
        window = _resolve_period_window(normalized_type, requested_days, today_china)
        db_aggs, instance_aggs, db_stats, instance_stats = _load_core_metric_records(normalized_type, window)
        daily_metrics = _build_daily_metrics(window, db_stats, instance_stats, db_aggs, instance_aggs)
        labels, datasets, time_range = _compose_chart_payload(normalized_type, window, daily_metrics)

        payload = {
            "labels": labels,
            "datasets": datasets,
            "dataPointCount": len(labels),
            "timeRange": time_range,
            "yAxisLabel": "数量",
            "chartTitle": f"{normalized_type.title()}核心指标统计",
            "periodType": normalized_type,
        }

        log_info(
            "核心聚合指标获取成功",
            module="partition",
            period_type=normalized_type,
            points=len(labels),
        )
        return jsonify_unified_success(data=payload, message="核心聚合指标获取成功")

    return safe_route_call(
        _execute,
        module="partition",
        action="get_core_aggregation_metrics",
        public_error="获取核心聚合指标失败",
        expected_exceptions=(ValidationError,),
        context={"period_type": requested_period_type, "days": requested_days},
    )
