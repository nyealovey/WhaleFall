"""Capacity namespace (Phase 2 核心域迁移)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import ClassVar

from flask import request
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import bool_with_default, new_parser
from app.api.v1.restx_models.capacity import (
    CAPACITY_CURRENT_AGGREGATION_RESULT_FIELDS,
    CAPACITY_DATABASE_AGGREGATION_ITEM_FIELDS,
    CAPACITY_DATABASE_SUMMARY_FIELDS,
    CAPACITY_INSTANCE_AGGREGATION_ITEM_FIELDS,
    CAPACITY_INSTANCE_REF_FIELDS,
    CAPACITY_INSTANCE_SUMMARY_FIELDS,
)
from app.errors import ValidationError
from app.services.capacity.current_aggregation_service import CurrentAggregationService
from app.services.capacity.database_aggregations_read_service import DatabaseAggregationsReadService
from app.services.capacity.instance_aggregations_read_service import InstanceAggregationsReadService
from app.types.capacity_aggregations import CurrentAggregationRequest
from app.types.capacity_databases import DatabaseAggregationsFilters, DatabaseAggregationsSummaryFilters
from app.types.capacity_instances import InstanceAggregationsFilters, InstanceAggregationsSummaryFilters
from app.utils.decorators import require_csrf
from app.utils.time_utils import time_utils

ns = Namespace("capacity", description="容量统计")

ErrorEnvelope = get_error_envelope_model(ns)

CapacityCurrentAggregationPayload = ns.model(
    "CapacityCurrentAggregationPayload",
    {
        "period_type": fields.String(required=False, description="聚合周期类型(当前仅支持 daily)"),
        "scope": fields.String(required=False, description="聚合范围(instance/database/all)"),
    },
)

CapacityCurrentAggregationResultModel = ns.model(
    "CapacityCurrentAggregationResult",
    CAPACITY_CURRENT_AGGREGATION_RESULT_FIELDS,
)

CapacityCurrentAggregationData = ns.model(
    "CapacityCurrentAggregationData",
    {
        "result": fields.Nested(CapacityCurrentAggregationResultModel),
    },
)

CapacityCurrentAggregationSuccessEnvelope = make_success_envelope_model(
    ns,
    "CapacityCurrentAggregationSuccessEnvelope",
    CapacityCurrentAggregationData,
)

CapacityDatabasesInstanceRefModel = ns.model(
    "CapacityDatabasesInstanceRef",
    CAPACITY_INSTANCE_REF_FIELDS,
)

CapacityDatabaseAggregationItemModel = ns.model(
    "CapacityDatabaseAggregationItem",
    {
        **CAPACITY_DATABASE_AGGREGATION_ITEM_FIELDS,
        "instance": fields.Nested(CapacityDatabasesInstanceRefModel),
    },
)

CapacityDatabaseAggregationsListData = ns.model(
    "CapacityDatabaseAggregationsListData",
    {
        "items": fields.List(fields.Nested(CapacityDatabaseAggregationItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
        "has_prev": fields.Boolean(),
        "has_next": fields.Boolean(),
    },
)

CapacityDatabaseAggregationsListSuccessEnvelope = make_success_envelope_model(
    ns,
    "CapacityDatabaseAggregationsListSuccessEnvelope",
    CapacityDatabaseAggregationsListData,
)

CapacityDatabaseSummaryModel = ns.model(
    "CapacityDatabaseSummary",
    CAPACITY_DATABASE_SUMMARY_FIELDS,
)

CapacityDatabaseSummaryData = ns.model(
    "CapacityDatabaseSummaryData",
    {
        "summary": fields.Nested(CapacityDatabaseSummaryModel),
    },
)

CapacityDatabaseSummarySuccessEnvelope = make_success_envelope_model(
    ns,
    "CapacityDatabaseSummarySuccessEnvelope",
    CapacityDatabaseSummaryData,
)

CapacityInstancesInstanceRefModel = ns.model(
    "CapacityInstancesInstanceRef",
    CAPACITY_INSTANCE_REF_FIELDS,
)

CapacityInstanceAggregationItemModel = ns.model(
    "CapacityInstanceAggregationItem",
    {
        **CAPACITY_INSTANCE_AGGREGATION_ITEM_FIELDS,
        "instance": fields.Nested(CapacityInstancesInstanceRefModel),
    },
)

CapacityInstanceAggregationsListData = ns.model(
    "CapacityInstanceAggregationsListData",
    {
        "items": fields.List(fields.Nested(CapacityInstanceAggregationItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
        "has_prev": fields.Boolean(),
        "has_next": fields.Boolean(),
    },
)

CapacityInstanceAggregationsListSuccessEnvelope = make_success_envelope_model(
    ns,
    "CapacityInstanceAggregationsListSuccessEnvelope",
    CapacityInstanceAggregationsListData,
)

CapacityInstanceSummaryModel = ns.model(
    "CapacityInstanceSummary",
    CAPACITY_INSTANCE_SUMMARY_FIELDS,
)

CapacityInstanceSummaryData = ns.model(
    "CapacityInstanceSummaryData",
    {
        "summary": fields.Nested(CapacityInstanceSummaryModel),
    },
)

CapacityInstanceSummarySuccessEnvelope = make_success_envelope_model(
    ns,
    "CapacityInstanceSummarySuccessEnvelope",
    CapacityInstanceSummaryData,
)

_capacity_databases_query_parser = new_parser()
_capacity_databases_query_parser.add_argument("start_date", type=str, location="args")
_capacity_databases_query_parser.add_argument("end_date", type=str, location="args")
_capacity_databases_query_parser.add_argument("instance_id", type=int, location="args")
_capacity_databases_query_parser.add_argument("db_type", type=str, location="args")
_capacity_databases_query_parser.add_argument("database_name", type=str, location="args")
_capacity_databases_query_parser.add_argument("database_id", type=int, location="args")
_capacity_databases_query_parser.add_argument("period_type", type=str, location="args")
_capacity_databases_query_parser.add_argument("page", type=int, default=1, location="args")
_capacity_databases_query_parser.add_argument("limit", type=int, default=20, location="args")
_capacity_databases_query_parser.add_argument("get_all", type=bool_with_default(False), default=False, location="args")

_capacity_databases_summary_query_parser = new_parser()
for argument in _capacity_databases_query_parser.args:
    _capacity_databases_summary_query_parser.args.append(argument)

_capacity_instances_query_parser = new_parser()
_capacity_instances_query_parser.add_argument("start_date", type=str, location="args")
_capacity_instances_query_parser.add_argument("end_date", type=str, location="args")
_capacity_instances_query_parser.add_argument("time_range", type=str, location="args")
_capacity_instances_query_parser.add_argument("instance_id", type=int, location="args")
_capacity_instances_query_parser.add_argument("db_type", type=str, location="args")
_capacity_instances_query_parser.add_argument("period_type", type=str, location="args")
_capacity_instances_query_parser.add_argument("page", type=int, default=1, location="args")
_capacity_instances_query_parser.add_argument("limit", type=int, default=20, location="args")
_capacity_instances_query_parser.add_argument("get_all", type=bool_with_default(False), default=False, location="args")

_capacity_instances_summary_query_parser = new_parser()
for argument in _capacity_instances_query_parser.args:
    _capacity_instances_summary_query_parser.args.append(argument)


def _parse_date(value: str, field: str) -> date:
    try:
        parsed_dt = time_utils.to_china(value + "T00:00:00")
    except Exception as exc:
        msg = f"{field} 格式错误,应为 YYYY-MM-DD"
        raise ValidationError(msg) from exc
    if parsed_dt is None:
        raise ValidationError("无法解析日期")
    return parsed_dt.date()


def _resolve_date_range(params: dict[str, object]) -> tuple[date | None, date | None]:
    start_date_raw = params.get("start_date")
    end_date_raw = params.get("end_date")
    time_range_raw = params.get("time_range")

    start_date_str = start_date_raw.strip() if isinstance(start_date_raw, str) and start_date_raw.strip() else None
    end_date_str = end_date_raw.strip() if isinstance(end_date_raw, str) and end_date_raw.strip() else None
    time_range = time_range_raw.strip() if isinstance(time_range_raw, str) and time_range_raw.strip() else None

    if time_range and not start_date_str and not end_date_str:
        try:
            delta_days = int(time_range)
        except (TypeError, ValueError) as exc:
            raise ValidationError("time_range 必须为整数(天)") from exc

        end_date_obj = time_utils.now_china().date()
        start_date_obj = end_date_obj - timedelta(days=delta_days)
        return start_date_obj, end_date_obj

    start_date = _parse_date(start_date_str, "start_date") if start_date_str else None
    end_date = _parse_date(end_date_str, "end_date") if end_date_str else None
    return start_date, end_date


@ns.route("/aggregations/current")
class CapacityCurrentAggregationResource(BaseResource):
    """当前周期容量聚合资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.expect(CapacityCurrentAggregationPayload, validate=False)
    @ns.response(200, "OK", CapacityCurrentAggregationSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """触发当前周期容量聚合."""
        payload = request.get_json(silent=True) if request.is_json else None
        payload_dict = payload if isinstance(payload, dict) else {}

        aggregation_request = CurrentAggregationRequest(
            requested_period_type=(payload_dict.get("period_type") or "daily").lower(),
            scope=(payload_dict.get("scope") or "all").lower(),
        )
        context_snapshot = {
            "requested_period_type": aggregation_request.requested_period_type,
            "scope": aggregation_request.scope,
        }

        def _execute():
            result = CurrentAggregationService().aggregate_current(aggregation_request)
            data = marshal(
                {"result": result},
                {"result": fields.Nested(CapacityCurrentAggregationResultModel)},
            )
            return self.success(data=data, message="已仅聚合今日数据")

        return self.safe_call(
            _execute,
            module="capacity_aggregations",
            action="aggregate_current",
            public_error="触发当前周期数据聚合失败",
            context=context_snapshot,
        )


@ns.route("/databases")
class CapacityDatabasesAggregationsResource(BaseResource):
    """数据库容量聚合列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", CapacityDatabaseAggregationsListSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_capacity_databases_query_parser)
    def get(self):
        """获取数据库容量聚合列表."""
        query_params = request.args.to_dict(flat=False)

        parsed = _capacity_databases_query_parser.parse_args()
        start_date_str = str(parsed.get("start_date") or "").strip() or None
        end_date_str = str(parsed.get("end_date") or "").strip() or None
        start_date = _parse_date(start_date_str, "start_date") if start_date_str else None
        end_date = _parse_date(end_date_str, "end_date") if end_date_str else None

        filters = DatabaseAggregationsFilters(
            instance_id=parsed.get("instance_id") if isinstance(parsed.get("instance_id"), int) else None,
            db_type=parsed.get("db_type") if isinstance(parsed.get("db_type"), str) else None,
            database_name=str(parsed.get("database_name") or "").strip() or None,
            database_id=parsed.get("database_id") if isinstance(parsed.get("database_id"), int) else None,
            period_type=parsed.get("period_type") if isinstance(parsed.get("period_type"), str) else None,
            start_date=start_date,
            end_date=end_date,
            page=max(int(parsed.get("page") or 1), 1),
            limit=max(min(int(parsed.get("limit") or 20), 200), 1),
            get_all=bool(parsed.get("get_all") or False),
        )

        def _execute():
            result = DatabaseAggregationsReadService().list_aggregations(filters)
            items = marshal(result.items, CapacityDatabaseAggregationItemModel)
            return self.success(
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

        return self.safe_call(
            _execute,
            module="capacity_databases",
            action="fetch_database_metrics",
            public_error="获取数据库统计聚合数据失败",
            context={"query_params": query_params},
        )


@ns.route("/databases/summary")
class CapacityDatabasesSummaryResource(BaseResource):
    """数据库容量聚合汇总资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", CapacityDatabaseSummarySuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_capacity_databases_summary_query_parser)
    def get(self):
        """获取数据库容量聚合汇总."""
        query_params = request.args.to_dict(flat=False)

        parsed = _capacity_databases_summary_query_parser.parse_args()
        start_date_str = str(parsed.get("start_date") or "").strip() or None
        end_date_str = str(parsed.get("end_date") or "").strip() or None
        start_date = _parse_date(start_date_str, "start_date") if start_date_str else None
        end_date = _parse_date(end_date_str, "end_date") if end_date_str else None

        filters = DatabaseAggregationsSummaryFilters(
            instance_id=parsed.get("instance_id") if isinstance(parsed.get("instance_id"), int) else None,
            db_type=parsed.get("db_type") if isinstance(parsed.get("db_type"), str) else None,
            database_name=str(parsed.get("database_name") or "").strip() or None,
            database_id=parsed.get("database_id") if isinstance(parsed.get("database_id"), int) else None,
            period_type=parsed.get("period_type") if isinstance(parsed.get("period_type"), str) else None,
            start_date=start_date,
            end_date=end_date,
        )

        def _execute():
            result = DatabaseAggregationsReadService().build_summary(filters)
            payload = marshal(result, CapacityDatabaseSummaryModel)
            return self.success(
                data={"summary": payload},
                message="数据库统计聚合汇总获取成功",
            )

        return self.safe_call(
            _execute,
            module="capacity_databases",
            action="fetch_database_summary",
            public_error="获取数据库统计聚合汇总信息失败",
            context={"query_params": query_params},
        )


@ns.route("/instances")
class CapacityInstancesAggregationsResource(BaseResource):
    """实例容量聚合列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", CapacityInstanceAggregationsListSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_capacity_instances_query_parser)
    def get(self):
        """获取实例容量聚合列表."""
        query_params = request.args.to_dict(flat=False)

        parsed = _capacity_instances_query_parser.parse_args()
        start_date, end_date = _resolve_date_range(dict(parsed))
        filters = InstanceAggregationsFilters(
            instance_id=parsed.get("instance_id") if isinstance(parsed.get("instance_id"), int) else None,
            db_type=parsed.get("db_type") if isinstance(parsed.get("db_type"), str) else None,
            period_type=parsed.get("period_type") if isinstance(parsed.get("period_type"), str) else None,
            start_date=start_date,
            end_date=end_date,
            page=max(int(parsed.get("page") or 1), 1),
            limit=max(min(int(parsed.get("limit") or 20), 200), 1),
            get_all=bool(parsed.get("get_all") or False),
        )

        def _execute():
            result = InstanceAggregationsReadService().list_aggregations(filters)
            items = marshal(result.items, CapacityInstanceAggregationItemModel)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                    "limit": result.limit,
                    "has_prev": result.has_prev,
                    "has_next": result.has_next,
                },
                message="操作成功",
            )

        return self.safe_call(
            _execute,
            module="capacity_instances",
            action="fetch_instance_metrics",
            public_error="获取实例聚合数据失败",
            context={"query_params": query_params},
            expected_exceptions=(ValidationError,),
        )


@ns.route("/instances/summary")
class CapacityInstancesSummaryResource(BaseResource):
    """实例容量聚合汇总资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", CapacityInstanceSummarySuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_capacity_instances_summary_query_parser)
    def get(self):
        """获取实例容量聚合汇总."""
        query_params = request.args.to_dict(flat=False)

        parsed = _capacity_instances_summary_query_parser.parse_args()
        start_date, end_date = _resolve_date_range(dict(parsed))
        filters = InstanceAggregationsSummaryFilters(
            instance_id=parsed.get("instance_id") if isinstance(parsed.get("instance_id"), int) else None,
            db_type=parsed.get("db_type") if isinstance(parsed.get("db_type"), str) else None,
            period_type=parsed.get("period_type") if isinstance(parsed.get("period_type"), str) else None,
            start_date=start_date,
            end_date=end_date,
        )

        def _execute():
            result = InstanceAggregationsReadService().build_summary(filters)
            payload = marshal(result, CapacityInstanceSummaryModel)
            return self.success(
                data={"summary": payload},
                message="操作成功",
            )

        return self.safe_call(
            _execute,
            module="capacity_instances",
            action="fetch_instance_summary",
            public_error="获取实例聚合汇总失败",
            context={"query_params": query_params},
            expected_exceptions=(ValidationError,),
        )
