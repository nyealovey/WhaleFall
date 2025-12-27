"""Partition namespace (Phase 4B 分区管理)."""

from __future__ import annotations

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
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
from app.utils.decorators import require_csrf
from app.utils.pagination_utils import resolve_page, resolve_page_size
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
PartitionCleanupSuccessEnvelope = make_success_envelope_model(ns, "PartitionCleanupSuccessEnvelope", PartitionCleanupData)

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
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", PartitionInfoSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
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
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", PartitionStatusSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
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


@ns.route("/partitions")
class PartitionsListResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", PartitionListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        search_term = request.args.get("search", "", type=str) or ""
        table_type = request.args.get("table_type", "", type=str) or ""
        status_filter = request.args.get("status", "", type=str) or ""
        sort_field = request.args.get("sort", "name", type=str) or "name"
        sort_order = request.args.get("order", "asc", type=str) or "asc"
        page = resolve_page(request.args, default=1, minimum=1)
        limit = resolve_page_size(
            request.args,
            default=20,
            minimum=1,
            maximum=200,
            module="partition",
            action="list_partitions",
        )

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


CreatePartitionPayload = ns.model(
    "CreatePartitionPayload",
    {
        "date": fields.String(required=True, description="YYYY-MM-DD"),
    },
)


@ns.route("/create")
class PartitionCreateResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("admin")]

    @ns.expect(CreatePartitionPayload, validate=False)
    @ns.response(200, "OK", PartitionCreateSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        data = request.get_json(silent=True) or {}
        partition_date_str = data.get("date")

        def _execute():
            if not partition_date_str:
                raise ValidationError("缺少日期参数")

            try:
                parsed_dt = time_utils.to_china(str(partition_date_str) + "T00:00:00")
            except Exception as exc:
                raise ValidationError("日期格式错误,请使用 YYYY-MM-DD 格式") from exc
            if parsed_dt is None:
                raise ValidationError("无法解析日期")
            partition_date = parsed_dt.date()

            today = time_utils.now_china().date()
            current_month_start = today.replace(day=1)
            if partition_date < current_month_start:
                raise ValidationError("只能创建当前或未来月份的分区")

            result = PartitionManagementService().create_partition(partition_date)
            payload = {"result": result, "timestamp": time_utils.now().isoformat()}

            log_info(
                "创建分区成功",
                module="partition",
                partition_date=str(partition_date),
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


@ns.route("/cleanup")
class PartitionCleanupResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("admin")]

    @ns.expect(CleanupPartitionPayload, validate=False)
    @ns.response(200, "OK", PartitionCleanupSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        data = request.get_json(silent=True) or {}
        raw_retention = data.get("retention_months", 12)

        def _execute():
            try:
                retention_months = int(raw_retention)
            except (TypeError, ValueError) as exc:
                raise ValidationError("retention_months 必须为数字") from exc

            result = PartitionManagementService().cleanup_old_partitions(retention_months=retention_months)
            payload = {"result": result, "timestamp": time_utils.now().isoformat()}

            log_info(
                "清理旧分区成功",
                module="partition",
                retention_months=retention_months,
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
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", PartitionStatisticsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
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


@ns.route("/aggregations/core-metrics")
class PartitionCoreMetricsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", PartitionCoreMetricsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        requested_period_type = (request.args.get("period_type") or "daily").lower()
        requested_days = request.args.get("days", 7, type=int)

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

