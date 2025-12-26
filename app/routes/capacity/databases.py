"""数据库统计 API 路由.

提供数据库大小监控、历史数据、统计聚合等接口,专注于数据库层面的统计功能.
"""

from datetime import date

from flask import Blueprint, Response, render_template, request
from flask_login import login_required
from flask_restx import marshal

from app.constants import PERIOD_TYPES
from app.errors import ValidationError
from app.routes.capacity.restx_models import CAPACITY_DATABASE_AGGREGATION_ITEM_FIELDS, CAPACITY_DATABASE_SUMMARY_FIELDS
from app.services.capacity.database_aggregations_read_service import DatabaseAggregationsReadService
from app.services.capacity.capacity_databases_page_service import CapacityDatabasesPageService
from app.types.capacity_databases import DatabaseAggregationsFilters, DatabaseAggregationsSummaryFilters
from app.utils.decorators import view_required
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.time_utils import time_utils

# 创建蓝图
capacity_databases_bp = Blueprint("capacity_databases", __name__)
_capacity_databases_page_service = CapacityDatabasesPageService()


@capacity_databases_bp.route("/databases", methods=["GET"])
@login_required
@view_required
def list_databases() -> str:
    """数据库统计聚合页面(数据库统计层面).

    Returns:
        渲染的数据库统计聚合页面,包含筛选选项和图表.

    Query Parameters:
        db_type: 数据库类型筛选,可选.
        instance: 实例 ID 筛选,可选.
        database_id: 数据库 ID 筛选,可选.
        database: 数据库名称筛选,可选.
        period_type: 统计周期类型,默认 'daily'.
        start_date: 开始日期,可选.
        end_date: 结束日期,可选.

    """
    selected_db_type = request.args.get("db_type", "")
    selected_instance = request.args.get("instance", "")
    selected_database_id = request.args.get("database_id", "")
    selected_database = request.args.get("database", "")
    selected_period_type = request.args.get("period_type", "daily")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    def _execute() -> str:
        page_context = _capacity_databases_page_service.build_context(
            db_type=selected_db_type,
            instance=selected_instance,
            database_id=selected_database_id,
            database=selected_database,
        )
        return render_template(
            "capacity/databases.html",
            database_type_options=page_context.database_type_options,
            instance_options=page_context.instance_options,
            database_options=page_context.database_options,
            period_type_options=PERIOD_TYPES,
            db_type=page_context.db_type,
            instance=page_context.instance,
            database_id=page_context.database_id,
            database=page_context.database,
            period_type=selected_period_type,
            start_date=start_date,
            end_date=end_date,
        )

    return safe_route_call(
        _execute,
        module="capacity_databases",
        action="list_databases",
        public_error="加载数据库容量统计页面失败",
        context={
            "db_type": selected_db_type,
            "instance": selected_instance,
            "database_id": selected_database_id,
            "has_database_name": bool(selected_database),
            "period_type": selected_period_type,
        },
    )


@capacity_databases_bp.route("/api/databases", methods=["GET"])
@login_required
@view_required
def fetch_database_metrics() -> tuple[Response, int]:
    """获取数据库统计聚合数据(数据库统计层面).

    支持分页、筛选和日期范围查询.

    Returns:
        JSON 响应,包含聚合数据列表和分页信息.

    Raises:
        ValidationError: 当参数无效时抛出.
        SystemError: 当获取数据失败时抛出.

    Query Parameters:
        instance_id: 实例 ID 筛选,可选.
        db_type: 数据库类型筛选,可选.
        database_name: 数据库名称筛选,可选.
        database_id: 数据库 ID 筛选,可选.
        period_type: 统计周期类型,可选.
        start_date: 开始日期(YYYY-MM-DD),可选.
        end_date: 结束日期(YYYY-MM-DD),可选.
        page: 页码,默认 1.
        per_page: 每页数量,默认 20.
        get_all: 是否获取全部数据,默认 false.

    """
    query_params = request.args.to_dict(flat=False)

    def _execute() -> tuple[Response, int]:
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        start_date = _parse_date(start_date_str, "start_date") if start_date_str else None
        end_date = _parse_date(end_date_str, "end_date") if end_date_str else None

        filters = DatabaseAggregationsFilters(
            instance_id=request.args.get("instance_id", type=int),
            db_type=request.args.get("db_type"),
            database_name=request.args.get("database_name"),
            database_id=request.args.get("database_id", type=int),
            period_type=request.args.get("period_type"),
            start_date=start_date,
            end_date=end_date,
            page=resolve_page(request.args, default=1, minimum=1),
            limit=resolve_page_size(
                request.args,
                default=20,
                minimum=1,
                maximum=200,
                module="capacity_databases",
                action="fetch_database_metrics",
            ),
            get_all=(request.args.get("get_all", "false") or "false").lower() == "true",
        )
        result = DatabaseAggregationsReadService().list_aggregations(filters)
        items = marshal(result.items, CAPACITY_DATABASE_AGGREGATION_ITEM_FIELDS)

        return jsonify_unified_success(
            data={
                "items": items,
                "total": result.total,
                "page": result.page,
                "pages": result.pages,
                "limit": result.limit,
                "has_prev": result.has_prev,
                "has_next": result.has_next,
            },
            message="数据库统计聚合数据获取成功",
        )

    return safe_route_call(
        _execute,
        module="capacity_databases",
        action="fetch_database_metrics",
        public_error="获取数据库统计聚合数据失败",
        expected_exceptions=(ValidationError,),
        context={"query_params": query_params},
    )


def _parse_date(value: str, field: str) -> date:
    """解析日期字符串.

    Args:
        value: 日期字符串,格式 'YYYY-MM-DD'.
        field: 字段名称,用于错误消息.

    Returns:
        解析后的日期对象.

    Raises:
        ValidationError: 当日期格式无效时抛出.

    """
    try:
        parsed_dt = time_utils.to_china(value + "T00:00:00")
    except Exception as exc:
        msg = f"{field} 格式错误,应为 YYYY-MM-DD"
        raise ValidationError(msg) from exc
    if parsed_dt is None:
        msg = "无法解析日期"
        raise ValidationError(msg)
    return parsed_dt.date()


@capacity_databases_bp.route("/api/databases/summary", methods=["GET"])
@login_required
@view_required
def fetch_database_summary() -> tuple[Response, int]:
    """获取数据库统计聚合汇总信息.

    Returns:
        JSON 响应,包含汇总统计数据.

    Raises:
        ValidationError: 当参数无效时抛出.
        SystemError: 当获取汇总失败时抛出.

    Query Parameters:
        instance_id: 实例 ID 筛选,可选.
        db_type: 数据库类型筛选,可选.
        database_name: 数据库名称筛选,可选.
        database_id: 数据库 ID 筛选,可选.
        period_type: 统计周期类型,可选.
        start_date: 开始日期(YYYY-MM-DD),可选.
        end_date: 结束日期(YYYY-MM-DD),可选.

    """
    query_params = request.args.to_dict(flat=False)

    def _execute() -> tuple[Response, int]:
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        start_date = _parse_date(start_date_str, "start_date") if start_date_str else None
        end_date = _parse_date(end_date_str, "end_date") if end_date_str else None

        filters = DatabaseAggregationsSummaryFilters(
            instance_id=request.args.get("instance_id", type=int),
            db_type=request.args.get("db_type"),
            database_name=request.args.get("database_name"),
            database_id=request.args.get("database_id", type=int),
            period_type=request.args.get("period_type"),
            start_date=start_date,
            end_date=end_date,
        )
        result = DatabaseAggregationsReadService().build_summary(filters)
        payload = marshal(result, CAPACITY_DATABASE_SUMMARY_FIELDS)
        return jsonify_unified_success(
            data={"summary": payload},
            message="数据库统计聚合汇总获取成功",
        )

    return safe_route_call(
        _execute,
        module="capacity_databases",
        action="fetch_database_summary",
        public_error="获取数据库统计聚合汇总信息失败",
        expected_exceptions=(ValidationError,),
        context={"query_params": query_params},
    )
