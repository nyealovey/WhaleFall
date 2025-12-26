"""分区管理 API 路由."""

from __future__ import annotations

from flask_restx import marshal

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app.errors import ValidationError
from app.routes.partition_restx_models import (
    PARTITION_CORE_METRICS_FIELDS,
    PARTITION_INFO_RESPONSE_FIELDS,
    PARTITION_LIST_RESPONSE_FIELDS,
    PARTITION_STATUS_RESPONSE_FIELDS,
)
from app.services.partition import PartitionReadService
from app.services.partition_management_service import PartitionManagementService
from app.services.statistics.partition_statistics_service import PartitionStatisticsService
from app.types import RouteReturn
from app.utils.decorators import admin_required, require_csrf, view_required
from app.utils.pagination_utils import resolve_page_size
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info, log_warning
from app.utils.time_utils import time_utils

# 创建蓝图
partition_bp = Blueprint("partition", __name__)
_partition_read_service = PartitionReadService()


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
    def _execute() -> RouteReturn:
        log_info("开始获取分区信息", module="partition", user_id=getattr(current_user, "id", None))
        snapshot = _partition_read_service.get_partition_info_snapshot()
        payload = marshal(
            {"data": snapshot, "timestamp": time_utils.now().isoformat()},
            PARTITION_INFO_RESPONSE_FIELDS,
        )
        log_info("分区信息获取成功", module="partition")
        return jsonify_unified_success(data=payload, message="分区信息获取成功")

    return safe_route_call(
        _execute,
        module="partition",
        action="get_partition_info",
        public_error="获取分区信息失败",
    )


# API 路由


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
        snapshot = _partition_read_service.get_partition_status_snapshot()
        if snapshot.status != "healthy":
            log_warning(
                "分区状态存在告警",
                module="partition",
                status=snapshot.status,
                missing_partitions=snapshot.missing_partitions,
            )

        payload = marshal(
            {"data": snapshot, "timestamp": time_utils.now().isoformat()},
            PARTITION_STATUS_RESPONSE_FIELDS,
        )
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
        page_size: 每页数量,默认 20,最大 200(兼容 limit/pageSize).
        sort: 排序字段,默认 'name'.
        order: 排序方向('asc'、'desc'),默认 'asc'.
        search: 搜索关键词,可选.
        table_type: 表类型筛选,可选.
        status: 状态筛选,可选.

    """
    search_term = request.args.get("search", "", type=str) or ""
    table_type = request.args.get("table_type", "", type=str) or ""
    status_filter = request.args.get("status", "", type=str) or ""
    sort_field = request.args.get("sort", "name", type=str) or "name"
    sort_order = request.args.get("order", "asc", type=str) or "asc"
    page = request.args.get("page", 1, type=int) or 1

    limit = resolve_page_size(
        request.args,
        default=20,
        minimum=1,
        maximum=200,
        module="partition",
        action="list_partitions",
    )

    def _execute() -> RouteReturn:
        result = _partition_read_service.list_partitions(
            page=page,
            limit=limit,
            search=search_term,
            table_type=table_type,
            status_filter=status_filter,
            sort_field=sort_field,
            sort_order=sort_order,
        )
        payload = marshal(
            {
                "items": result.items,
                "total": result.total,
                "page": result.page,
                "pages": result.pages,
                "limit": result.limit,
            },
            PARTITION_LIST_RESPONSE_FIELDS,
        )
        log_info(
            "获取分区列表成功",
            module="partition",
            total=result.total,
            page=result.page,
            limit=result.limit,
        )
        return jsonify_unified_success(data=payload, message="分区列表获取成功")

    return safe_route_call(
        _execute,
        module="partition",
        action="list_partitions",
        public_error="获取分区列表失败",
        context={
            "search": search_term,
            "table_type": table_type,
            "status": status_filter,
            "sort": sort_field,
            "order": sort_order,
            "page": page,
            "limit": limit,
        },
    )


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

    def _execute() -> RouteReturn:
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

    return safe_route_call(
        _execute,
        module="partition",
        action="create_partition",
        public_error="创建分区失败",
        context={"partition_date": partition_date_str},
        expected_exceptions=(ValidationError,),
    )


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
    def _execute() -> RouteReturn:
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

    return safe_route_call(
        _execute,
        module="partition",
        action="cleanup_partitions",
        public_error="清理旧分区失败",
        context={"retention_months": raw_retention},
        expected_exceptions=(ValidationError,),
    )


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
        result = _partition_read_service.build_core_metrics(period_type=requested_period_type, days=requested_days)
        payload = marshal(result, PARTITION_CORE_METRICS_FIELDS)

        log_info(
            "核心聚合指标获取成功",
            module="partition",
            period_type=result.periodType,
            points=result.dataPointCount,
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
