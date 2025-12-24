"""实例统计 API 路由."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from flask import Blueprint, Response, render_template, request
from flask_login import login_required
from sqlalchemy import desc, func

from app import db
from app.constants import DATABASE_TYPES, PERIOD_TYPES
from app.constants.system_constants import SuccessMessages
from app.errors import NotFoundError, ValidationError
from app.models.instance import Instance
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.services.database_type_service import DatabaseTypeService
from app.types import QueryProtocol
from app.utils.decorators import view_required
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.query_filter_utils import get_instance_options
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Mapping

# 创建蓝图
capacity_instances_bp = Blueprint("capacity_instances", __name__)
InstanceAggregationQuery = QueryProtocol[InstanceSizeAggregation]
InstanceStatQuery = QueryProtocol[InstanceSizeStat]


@dataclass(slots=True)
class InstanceMetricsFilters:
    """实例聚合查询参数."""

    instance_id: int | None
    db_type: str | None
    period_type: str | None
    start_date: str | None
    end_date: str | None
    time_range: str | None
    page: int
    limit: int
    get_all: bool

    @property
    def offset(self) -> int:
        """计算分页偏移."""
        return max(self.page - 1, 0) * self.limit


@dataclass(slots=True)
class SummaryFilters:
    """实例容量汇总查询参数."""

    instance_id: int | None
    db_type: str | None
    period_type: str | None
    start_date: str | None
    end_date: str | None
    time_range: str | None


def _get_instance(instance_id: int) -> Instance:
    """获取实例或抛出错误.

    Args:
        instance_id: 实例 ID.

    Returns:
        实例对象.

    Raises:
        NotFoundError: 当实例不存在时抛出.

    """
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance is None:
        msg = "实例不存在"
        raise NotFoundError(msg)
    return instance


def _parse_iso_date(value: str, field_name: str) -> date:
    """解析 ISO 格式日期字符串.

    Args:
        value: 日期字符串,格式 'YYYY-MM-DD'.
        field_name: 字段名称,用于错误消息.

    Returns:
        解析后的日期对象.

    Raises:
        ValidationError: 当日期格式无效时抛出.

    """
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
        return parsed.date()
    except ValueError as exc:
        msg = f"{field_name} 格式错误,需使用 YYYY-MM-DD"
        raise ValidationError(msg) from exc


# 页面路由
@capacity_instances_bp.route("/instances", methods=["GET"])
@login_required
@view_required
def list_instances() -> str:
    """实例统计聚合页面.

    Returns:
        str: 渲染后的实例统计聚合页面 HTML.

    """
    # 读取已选择的筛选条件以便回填
    selected_db_type = request.args.get("db_type", "")
    selected_instance = request.args.get("instance", "")
    selected_period_type = request.args.get("period_type", "daily")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    database_type_configs = DatabaseTypeService.get_active_types()
    if database_type_configs:
        database_type_options = [
            {
                "value": config.name,
                "label": config.display_name,
            }
            for config in database_type_configs
        ]
    else:
        database_type_options = [
            {
                "value": item["name"],
                "label": item["display_name"],
            }
            for item in DATABASE_TYPES
        ]

    instance_options = get_instance_options(selected_db_type or None) if selected_db_type else []

    return render_template(
        "capacity/instances.html",
        instance_options=instance_options,
        database_type_options=database_type_options,
        period_type_options=PERIOD_TYPES,
        db_type=selected_db_type,
        instance=selected_instance,
        period_type=selected_period_type,
        start_date=start_date,
        end_date=end_date,
    )


@capacity_instances_bp.route("/api/instances", methods=["GET"])
@login_required
@view_required
def fetch_instance_metrics() -> tuple[Response, int]:
    """获取实例聚合数据(实例统计层面).

    Args:
        instance_id: 请求参数,实例ID.
        db_type: 请求参数,数据库类型.
        period_type: 请求参数,聚合周期类型.
        start_date: 请求参数,开始日期(YYYY-MM-DD).
        end_date: 请求参数,结束日期(YYYY-MM-DD).
        time_range: 请求参数,快捷时间范围(天).
        page: 请求参数,分页页码.
        page_size: 请求参数,每页数量(兼容 limit/pageSize).
        get_all: 请求参数,是否返回全部记录(用于图表).

    Returns:
        Response: 包含实例聚合数据的 JSON 响应.

    """
    query_params = request.args.to_dict(flat=False)

    def _execute() -> tuple[Response, int]:
        filters = _extract_instance_metrics_filters()
        query = _build_instance_metrics_query(filters)
        aggregations, total = _query_instance_aggregations(query, filters)
        items = _serialize_instance_aggregations(aggregations)
        payload = _build_metrics_payload(items, total, filters)
        return jsonify_unified_success(data=payload, message=SuccessMessages.OPERATION_SUCCESS)

    return safe_route_call(
        _execute,
        module="capacity_instances",
        action="fetch_instance_metrics",
        public_error="获取实例聚合数据失败",
        expected_exceptions=(ValidationError, NotFoundError),
        context={"query_params": query_params},
    )


@capacity_instances_bp.route("/api/instances/summary", methods=["GET"])
@login_required
@view_required
def fetch_instance_summary() -> tuple[Response, int]:
    """获取实例聚合汇总信息(实例统计层面).

    Args:
        instance_id: 请求参数,实例ID.
        db_type: 请求参数,数据库类型.
        period_type: 请求参数,周期类型.
        start_date: 请求参数,开始日期(YYYY-MM-DD).
        end_date: 请求参数,结束日期(YYYY-MM-DD).
        time_range: 请求参数,快捷时间范围(天).

    Returns:
        Response: 包含实例聚合汇总信息的 JSON 响应.

    """
    query_params = request.args.to_dict(flat=False)

    def _execute() -> tuple[Response, int]:
        filters = _parse_summary_filters(request.args)
        stats_query = _build_summary_query(filters)
        latest_stats = _collect_latest_instance_stats(stats_query)
        summary_payload = _build_summary_payload(latest_stats, filters.period_type)
        return jsonify_unified_success(
            data={"summary": summary_payload},
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    return safe_route_call(
        _execute,
        module="capacity_instances",
        action="fetch_instance_summary",
        public_error="获取实例聚合汇总失败",
        expected_exceptions=(ValidationError,),
        context={"query_params": query_params},
    )


def _extract_instance_metrics_filters() -> InstanceMetricsFilters:
    """解析列表查询参数."""
    instance_id = request.args.get("instance_id", type=int)
    db_type = request.args.get("db_type")
    period_type = request.args.get("period_type")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    time_range = request.args.get("time_range")
    normalized_start, normalized_end = _normalize_time_range(start_date, end_date, time_range)
    page = resolve_page(request.args, default=1, minimum=1)
    limit = resolve_page_size(
        request.args,
        default=20,
        minimum=1,
        maximum=200,
        module="capacity_instances",
        action="fetch_instance_metrics",
    )
    get_all = request.args.get("get_all", "false").lower() == "true"

    return InstanceMetricsFilters(
        instance_id=instance_id,
        db_type=db_type,
        period_type=period_type,
        start_date=normalized_start,
        end_date=normalized_end,
        time_range=time_range,
        page=page,
        limit=limit,
        get_all=get_all,
    )


def _normalize_time_range(
    start_date: str | None,
    end_date: str | None,
    time_range: str | None,
) -> tuple[str | None, str | None]:
    """根据快捷时间范围填充起止日期."""
    if time_range and not start_date and not end_date:
        end_date_obj = time_utils.now_china()
        start_date_obj = end_date_obj - timedelta(days=int(time_range))
        start_date = time_utils.format_china_time(start_date_obj, "%Y-%m-%d")
        end_date = time_utils.format_china_time(end_date_obj, "%Y-%m-%d")
    return start_date, end_date


def _build_instance_metrics_query(filters: InstanceMetricsFilters) -> InstanceAggregationQuery:
    """根据过滤条件构建实例聚合查询."""
    base_query = InstanceSizeAggregation.query.join(Instance).filter(
        cast(Any, Instance.is_active).is_(True),
        cast(Any, Instance.deleted_at).is_(None),
    )
    query = cast("InstanceAggregationQuery", base_query)
    if filters.instance_id:
        query = query.filter(InstanceSizeAggregation.instance_id == filters.instance_id)
    if filters.db_type:
        query = query.filter(Instance.db_type == filters.db_type)
    if filters.period_type:
        query = query.filter(InstanceSizeAggregation.period_type == filters.period_type)
    if filters.start_date:
        start_date_obj = _parse_iso_date(filters.start_date, "start_date")
        query = query.filter(InstanceSizeAggregation.period_start >= start_date_obj)
    if filters.end_date:
        end_date_obj = _parse_iso_date(filters.end_date, "end_date")
        query = query.filter(InstanceSizeAggregation.period_end <= end_date_obj)
    return query


def _query_instance_aggregations(
    query: InstanceAggregationQuery,
    filters: InstanceMetricsFilters,
) -> tuple[list[InstanceSizeAggregation], int]:
    """查询实例聚合记录."""
    if filters.get_all:
        subquery = (
            query.with_entities(
                InstanceSizeAggregation.instance_id,
                func.max(InstanceSizeAggregation.total_size_mb).label("max_total_size_mb"),
            )
            .group_by(InstanceSizeAggregation.instance_id)
            .subquery()
        )
        top_instances = (
            db.session.query(subquery.c.instance_id).order_by(desc(subquery.c.max_total_size_mb)).limit(100).all()
        )
        top_instance_ids = [row[0] for row in top_instances]
        aggregations = (
            query.filter(InstanceSizeAggregation.instance_id.in_(top_instance_ids))
            .order_by(desc(InstanceSizeAggregation.total_size_mb))
            .all()
        )
        return aggregations, len(aggregations)

    ordered_query = query.order_by(
        desc(InstanceSizeAggregation.period_start),
        desc(InstanceSizeAggregation.id),
    )
    total = ordered_query.count()
    aggregations = ordered_query.offset(filters.offset).limit(filters.limit).all()
    return aggregations, total


def _serialize_instance_aggregations(
    aggregations: list[InstanceSizeAggregation],
) -> list[dict[str, Any]]:
    """转换聚合记录,补充实例元数据."""
    serialized: list[dict[str, Any]] = []
    for agg in aggregations:
        agg_dict = agg.to_dict()
        agg_dict["instance"] = {
            "id": agg.instance.id,
            "name": agg.instance.name,
            "db_type": agg.instance.db_type,
        }
        agg_dict["avg_size_mb"] = agg_dict.get("total_size_mb", 0)
        serialized.append(agg_dict)
    return serialized


def _build_metrics_payload(
    items: list[dict[str, Any]],
    total: int,
    filters: InstanceMetricsFilters,
) -> dict[str, Any]:
    """构造返回给前端的分页载荷."""
    pages = max((total + filters.limit - 1) // filters.limit, 1)
    return {
        "items": items,
        "total": total,
        "page": filters.page,
        "pages": pages,
        "limit": filters.limit,
        "has_prev": filters.page > 1,
        "has_next": filters.page < pages,
    }

def _parse_summary_filters(args: Mapping[str, str | None]) -> SummaryFilters:
    """解析汇总查询参数."""
    instance_id = args.get("instance_id")
    db_type = args.get("db_type")
    period_type = args.get("period_type")
    start_date = args.get("start_date")
    end_date = args.get("end_date")
    time_range = args.get("time_range")

    if time_range and not start_date and not end_date:
        end_date_obj = time_utils.now_china()
        start_date_obj = end_date_obj - timedelta(days=int(time_range))
        start_date = time_utils.format_china_time(start_date_obj, "%Y-%m-%d")
        end_date = time_utils.format_china_time(end_date_obj, "%Y-%m-%d")

    return SummaryFilters(
        instance_id=int(instance_id) if instance_id else None,
        db_type=db_type,
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
        time_range=time_range,
    )


def _build_summary_query(filters: SummaryFilters) -> InstanceStatQuery:
    """根据汇总过滤参数构建查询."""
    base_query = (
        InstanceSizeStat.query.join(Instance)
        .filter(InstanceSizeStat.is_deleted.is_(False))
        .filter(cast(Any, Instance.is_active).is_(True), cast(Any, Instance.deleted_at).is_(None))
    )
    query = cast("InstanceStatQuery", base_query)
    if filters.instance_id:
        query = query.filter(InstanceSizeStat.instance_id == filters.instance_id)
    if filters.db_type:
        query = query.filter(Instance.db_type == filters.db_type)
    if filters.start_date:
        start_date_obj = _parse_iso_date(filters.start_date, "start_date")
        query = query.filter(InstanceSizeStat.collected_date >= start_date_obj)
    if filters.end_date:
        end_date_obj = _parse_iso_date(filters.end_date, "end_date")
        query = query.filter(InstanceSizeStat.collected_date <= end_date_obj)
    return query


def _collect_latest_instance_stats(query: InstanceStatQuery) -> dict[int, InstanceSizeStat]:
    """获取每个实例最新的容量记录."""
    stats = query.all()
    latest_stats: dict[int, InstanceSizeStat] = {}
    for stat in stats:
        existing = latest_stats.get(stat.instance_id)
        current_ts = _to_timestamp(stat)
        if not existing:
            latest_stats[stat.instance_id] = stat
            continue
        existing_ts = _to_timestamp(existing)
        if current_ts > existing_ts:
            latest_stats[stat.instance_id] = stat
    return latest_stats


def _to_timestamp(stat: InstanceSizeStat) -> datetime:
    """将采集日期/时间统一为 datetime 便于比较."""
    if stat.collected_at:
        return stat.collected_at
    return datetime.combine(stat.collected_date, datetime.min.time())


def _build_summary_payload(latest_stats: dict[int, InstanceSizeStat], period_type: str | None) -> dict[str, Any]:
    """根据最新记录构建汇总响应."""
    total_instances = len(latest_stats)
    total_size_mb = sum(stat.total_size_mb or 0 for stat in latest_stats.values())
    avg_size_mb = total_size_mb / total_instances if total_instances else 0
    max_size_mb = max((stat.total_size_mb or 0) for stat in latest_stats.values()) if latest_stats else 0
    return {
        "total_instances": total_instances,
        "total_size_mb": total_size_mb,
        "avg_size_mb": avg_size_mb,
        "max_size_mb": max_size_mb,
        "period_type": period_type or "all",
        "source": "instance_size_stats",
    }
