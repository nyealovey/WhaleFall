"""Capacity namespace (Phase 2 核心域迁移)."""

from __future__ import annotations

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
from app.core.exceptions import ValidationError
from app.core.types.capacity_aggregations import CurrentAggregationRequest
from app.schemas.capacity_query import (
    CapacityDatabasesAggregationsQuery,
    CapacityDatabasesSummaryQuery,
    CapacityInstancesAggregationsQuery,
    CapacityInstancesSummaryQuery,
)
from app.schemas.validation import validate_or_raise
from app.services.capacity.current_aggregation_service import CurrentAggregationService
from app.services.capacity.database_aggregations_read_service import DatabaseAggregationsReadService
from app.services.capacity.instance_aggregations_read_service import InstanceAggregationsReadService
from app.utils.decorators import require_csrf

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

        raw_period_type = payload_dict.get("period_type")
        requested_period_type = (
            raw_period_type.strip().lower() if isinstance(raw_period_type, str) and raw_period_type.strip() else "daily"
        )
        raw_scope = payload_dict.get("scope")
        scope = raw_scope.strip().lower() if isinstance(raw_scope, str) and raw_scope.strip() else "all"

        aggregation_request = CurrentAggregationRequest(
            requested_period_type=requested_period_type,
            scope=scope,
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

        parsed = dict(_capacity_databases_query_parser.parse_args())
        query = validate_or_raise(CapacityDatabasesAggregationsQuery, parsed)
        filters = query.to_filters()

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

        parsed = dict(_capacity_databases_summary_query_parser.parse_args())
        query = validate_or_raise(CapacityDatabasesSummaryQuery, parsed)
        filters = query.to_filters()

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

        parsed = dict(_capacity_instances_query_parser.parse_args())
        query = validate_or_raise(CapacityInstancesAggregationsQuery, parsed)
        filters = query.to_filters()

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

        parsed = dict(_capacity_instances_summary_query_parser.parse_args())
        query = validate_or_raise(CapacityInstancesSummaryQuery, parsed)
        filters = query.to_filters()

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
