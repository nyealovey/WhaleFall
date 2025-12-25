"""实例容量统计 API 路由."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from flask import Blueprint, Response, render_template, request
from flask_restx import marshal
from flask_login import login_required

from app.constants import DATABASE_TYPES, PERIOD_TYPES
from app.constants.system_constants import SuccessMessages
from app.errors import ValidationError
from app.services.database_type_service import DatabaseTypeService
from app.services.capacity.instance_aggregations_read_service import InstanceAggregationsReadService
from app.services.common.filter_options_service import FilterOptionsService
from app.routes.capacity.restx_models import (
    CAPACITY_INSTANCE_AGGREGATION_ITEM_FIELDS,
    CAPACITY_INSTANCE_SUMMARY_FIELDS,
)
from app.types.capacity_instances import InstanceAggregationsFilters, InstanceAggregationsSummaryFilters
from app.utils.decorators import view_required
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Mapping

# 创建蓝图
capacity_instances_bp = Blueprint("capacity_instances", __name__)
_filter_options_service = FilterOptionsService()


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
        return time_utils.to_china(value + "T00:00:00").date()  # type: ignore[union-attr]
    except Exception as exc:
        msg = f"{field_name} 格式错误,需使用 YYYY-MM-DD"
        raise ValidationError(msg) from exc


def _resolve_date_range(args: Mapping[str, str | None]) -> tuple[date | None, date | None]:
    """根据 start/end/time_range 解析日期范围."""
    start_date_str = args.get("start_date")
    end_date_str = args.get("end_date")
    time_range = args.get("time_range")

    if time_range and not start_date_str and not end_date_str:
        try:
            delta_days = int(time_range)
        except (TypeError, ValueError) as exc:
            msg = "time_range 必须为整数(天)"
            raise ValidationError(msg) from exc

        end_date_obj = time_utils.now_china().date()
        start_date_obj = end_date_obj - timedelta(days=delta_days)
        return start_date_obj, end_date_obj

    start_date = _parse_iso_date(start_date_str, "start_date") if start_date_str else None
    end_date = _parse_iso_date(end_date_str, "end_date") if end_date_str else None
    return start_date, end_date


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

    instance_options = (
        _filter_options_service.list_instance_select_options(selected_db_type or None) if selected_db_type else []
    )

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
        start_date, end_date = _resolve_date_range(request.args)
        filters = InstanceAggregationsFilters(
            instance_id=request.args.get("instance_id", type=int),
            db_type=request.args.get("db_type"),
            period_type=request.args.get("period_type"),
            start_date=start_date,
            end_date=end_date,
            page=resolve_page(request.args, default=1, minimum=1),
            limit=resolve_page_size(
                request.args,
                default=20,
                minimum=1,
                maximum=200,
                module="capacity_instances",
                action="fetch_instance_metrics",
            ),
            get_all=(request.args.get("get_all", "false") or "false").lower() == "true",
        )
        result = InstanceAggregationsReadService().list_aggregations(filters)
        items = marshal(result.items, CAPACITY_INSTANCE_AGGREGATION_ITEM_FIELDS)
        payload = {
            "items": items,
            "total": result.total,
            "page": result.page,
            "pages": result.pages,
            "limit": result.limit,
            "has_prev": result.has_prev,
            "has_next": result.has_next,
        }
        return jsonify_unified_success(
            data=payload,
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    return safe_route_call(
        _execute,
        module="capacity_instances",
        action="fetch_instance_metrics",
        public_error="获取实例聚合数据失败",
        expected_exceptions=(ValidationError,),
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
        start_date, end_date = _resolve_date_range(request.args)
        filters = InstanceAggregationsSummaryFilters(
            instance_id=request.args.get("instance_id", type=int),
            db_type=request.args.get("db_type"),
            period_type=request.args.get("period_type"),
            start_date=start_date,
            end_date=end_date,
        )
        result = InstanceAggregationsReadService().build_summary(filters)
        summary_payload = marshal(result, CAPACITY_INSTANCE_SUMMARY_FIELDS)
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
