"""Partition namespace (Phase 4B 分区管理)."""

from __future__ import annotations

from typing import ClassVar

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import new_parser
from app.api.v1.restx_models.partition import (
    PARTITION_CORE_METRICS_FIELDS,
    PARTITION_INFO_RESPONSE_FIELDS,
    PARTITION_LIST_RESPONSE_FIELDS,
    PARTITION_STATUS_RESPONSE_FIELDS,
)
from app.core.exceptions import ValidationError
from app.schemas.partition_query import PartitionCoreMetricsQuery, PartitionsListQuery
from app.schemas.validation import validate_or_raise
from app.services.partition import PartitionReadService
from app.services.partition_management_service import PartitionManagementService
from app.services.statistics.partition_statistics_service import PartitionStatisticsService
from app.utils.decorators import require_csrf
from app.utils.structlog_config import log_info, log_warning
from app.utils.time_utils import time_utils

ns = Namespace("partition", description="分区管理")

ErrorEnvelope = get_error_envelope_model(ns)

PartitionInfoData = ns.model(
    "PartitionInfoData",
    {
        "data": fields.Raw(required=True),
        "timestamp": fields.String(required=True),
    },
)
PartitionInfoSuccessEnvelope = make_success_envelope_model(ns, "PartitionInfoSuccessEnvelope", PartitionInfoData)

_partitions_list_query_parser = new_parser()
_partitions_list_query_parser.add_argument("search", type=str, default="", location="args")
_partitions_list_query_parser.add_argument("table_type", type=str, default="", location="args")
_partitions_list_query_parser.add_argument("status", type=str, default="", location="args")
_partitions_list_query_parser.add_argument("sort", type=str, default="name", location="args")
_partitions_list_query_parser.add_argument("order", type=str, default="asc", location="args")
_partitions_list_query_parser.add_argument("page", type=int, default=1, location="args")
_partitions_list_query_parser.add_argument("limit", type=int, default=20, location="args")

_partition_core_metrics_query_parser = new_parser()
_partition_core_metrics_query_parser.add_argument("period_type", type=str, default="daily", location="args")
_partition_core_metrics_query_parser.add_argument("days", type=int, default=7, location="args")

PartitionStatusData = ns.model(
    "PartitionStatusData",
    {
        "data": fields.Raw(required=True),
        "timestamp": fields.String(required=True),
    },
)
PartitionStatusSuccessEnvelope = make_success_envelope_model(ns, "PartitionStatusSuccessEnvelope", PartitionStatusData)

PartitionListData = ns.model(
    "PartitionListData",
    {
        "items": fields.Raw(required=True),
        "total": fields.Integer(required=True),
        "page": fields.Integer(required=True),
        "pages": fields.Integer(required=True),
        "limit": fields.Integer(required=True),
    },
)
PartitionListSuccessEnvelope = make_success_envelope_model(ns, "PartitionListSuccessEnvelope", PartitionListData)

PartitionCreateData = ns.model(
    "PartitionCreateData",
    {
        "result": fields.Raw(required=True),
        "timestamp": fields.String(required=True),
    },
)
PartitionCreateSuccessEnvelope = make_success_envelope_model(ns, "PartitionCreateSuccessEnvelope", PartitionCreateData)

PartitionCleanupData = ns.model(
    "PartitionCleanupData",
    {
        "result": fields.Raw(required=True),
        "timestamp": fields.String(required=True),
    },
)
PartitionCleanupSuccessEnvelope = make_success_envelope_model(
    ns, "PartitionCleanupSuccessEnvelope", PartitionCleanupData
)

PartitionStatisticsData = ns.model(
    "PartitionStatisticsData",
    {
        "data": fields.Raw(required=True),
        "timestamp": fields.String(required=True),
    },
)
PartitionStatisticsSuccessEnvelope = make_success_envelope_model(
    ns,
    "PartitionStatisticsSuccessEnvelope",
    PartitionStatisticsData,
)

PartitionCoreMetricsData = ns.model(
    "PartitionCoreMetricsData",
    {
        "labels": fields.List(fields.String, required=True),
        "datasets": fields.Raw(required=True),
        "dataPointCount": fields.Integer(required=True),
        "timeRange": fields.String(required=True),
        "yAxisLabel": fields.String(required=True),
        "chartTitle": fields.String(required=True),
        "periodType": fields.String(required=True),
    },
)
PartitionCoreMetricsSuccessEnvelope = make_success_envelope_model(
    ns,
    "PartitionCoreMetricsSuccessEnvelope",
    PartitionCoreMetricsData,
)

_partition_read_service = PartitionReadService()


@ns.route("/info")
class PartitionInfoResource(BaseResource):
    """分区信息资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", PartitionInfoSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取分区信息."""

        def _execute():
            log_info("开始获取分区信息", module="partition", user_id=getattr(current_user, "id", None))
            snapshot = _partition_read_service.get_partition_info_snapshot()
            payload = marshal(
                {"data": snapshot, "timestamp": time_utils.now().isoformat()},
                PARTITION_INFO_RESPONSE_FIELDS,
            )
            log_info("分区信息获取成功", module="partition")
            return self.success(data=payload, message="分区信息获取成功")

        return self.safe_call(
            _execute,
            module="partition",
            action="get_partition_info",
            public_error="获取分区信息失败",
        )


@ns.route("/status")
class PartitionStatusResource(BaseResource):
    """分区状态资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", PartitionStatusSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取分区状态."""

        def _execute():
            snapshot = _partition_read_service.get_partition_status_snapshot()
            if getattr(snapshot, "status", None) != "healthy":
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
            return self.success(data=payload, message="分区状态获取成功")

        return self.safe_call(
            _execute,
            module="partition",
            action="get_partition_status",
            public_error="获取分区管理状态失败",
        )


CreatePartitionPayload = ns.model(
    "CreatePartitionPayload",
    {
        "date": fields.String(required=True, description="YYYY-MM-DD"),
    },
)


@ns.route("")
class PartitionsResource(BaseResource):
    """分区集合资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", PartitionListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_partitions_list_query_parser)
    @api_permission_required("view")
    def get(self):
        """获取分区列表."""
        parsed = _partitions_list_query_parser.parse_args()
        query = validate_or_raise(PartitionsListQuery, parsed)
        search_term = query.search
        table_type = query.table_type
        status_filter = query.status
        sort_field = query.sort_field
        sort_order = query.sort_order
        page = query.page
        limit = query.limit

        def _execute():
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
            return self.success(data=payload, message="分区列表获取成功")

        return self.safe_call(
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

    @ns.expect(CreatePartitionPayload, validate=False)
    @ns.response(200, "OK", PartitionCreateSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("admin")
    @require_csrf
    def post(self):
        """创建分区."""
        parsed_json = request.get_json(silent=True)
        raw: object = parsed_json if isinstance(parsed_json, dict) else {}
        partition_date_str = raw.get("date") if isinstance(raw, dict) else None

        def _execute():
            result = PartitionManagementService().create_partition_from_payload(raw)
            payload = {"result": result, "timestamp": time_utils.now().isoformat()}

            log_info(
                "创建分区成功",
                module="partition",
                partition_window=result.get("partition_window"),
                user_id=getattr(current_user, "id", None),
            )
            return self.success(data=payload, message="分区创建任务已触发")

        return self.safe_call(
            _execute,
            module="partition",
            action="create_partition",
            public_error="创建分区失败",
            expected_exceptions=(ValidationError,),
            context={"partition_date": partition_date_str},
        )


CleanupPartitionPayload = ns.model(
    "CleanupPartitionPayload",
    {
        "retention_months": fields.Integer(required=False, description="保留月数,默认 12"),
    },
)


@ns.route("/actions/cleanup")
class PartitionCleanupResource(BaseResource):
    """分区清理资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.expect(CleanupPartitionPayload, validate=False)
    @ns.response(200, "OK", PartitionCleanupSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """清理旧分区."""
        parsed_json = request.get_json(silent=True)
        raw: object = parsed_json if isinstance(parsed_json, dict) else {}
        raw_retention = raw.get("retention_months") if isinstance(raw, dict) else None

        def _execute():
            result = PartitionManagementService().cleanup_old_partitions_from_payload(raw)
            payload = {"result": result, "timestamp": time_utils.now().isoformat()}

            log_info(
                "清理旧分区成功",
                module="partition",
                retention_months=raw_retention,
                user_id=getattr(current_user, "id", None),
            )
            return self.success(data=payload, message="旧分区清理任务已触发")

        return self.safe_call(
            _execute,
            module="partition",
            action="cleanup_partitions",
            public_error="清理旧分区失败",
            expected_exceptions=(ValidationError,),
            context={"retention_months": raw_retention},
        )


@ns.route("/statistics")
class PartitionStatisticsResource(BaseResource):
    """分区统计资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", PartitionStatisticsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取分区统计信息."""

        def _execute():
            result = PartitionStatisticsService().get_partition_statistics()
            payload = {"data": result, "timestamp": time_utils.now().isoformat()}
            log_info("获取分区统计信息成功", module="partition")
            return self.success(data=payload, message="分区统计信息获取成功")

        return self.safe_call(
            _execute,
            module="partition",
            action="get_partition_statistics",
            public_error="获取分区统计信息失败",
        )


@ns.route("/core-metrics")
class PartitionCoreMetricsResource(BaseResource):
    """分区核心指标资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", PartitionCoreMetricsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_partition_core_metrics_query_parser)
    def get(self):
        """获取核心聚合指标."""
        parsed = _partition_core_metrics_query_parser.parse_args()
        query = validate_or_raise(PartitionCoreMetricsQuery, parsed)
        requested_period_type = query.period_type
        requested_days = query.days

        def _execute():
            result = _partition_read_service.build_core_metrics(period_type=requested_period_type, days=requested_days)
            payload = marshal(result, PARTITION_CORE_METRICS_FIELDS)
            log_info(
                "核心聚合指标获取成功",
                module="partition",
                period_type=getattr(result, "periodType", None),
                points=getattr(result, "dataPointCount", None),
            )
            return self.success(data=payload, message="核心聚合指标获取成功")

        return self.safe_call(
            _execute,
            module="partition",
            action="get_core_aggregation_metrics",
            public_error="获取核心聚合指标失败",
            expected_exceptions=(ValidationError,),
            context={"period_type": requested_period_type, "days": requested_days},
        )
