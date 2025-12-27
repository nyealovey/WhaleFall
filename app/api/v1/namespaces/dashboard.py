"""Dashboard namespace (Phase 3 全量覆盖 - 仪表板模块)."""

from __future__ import annotations

from flask import request
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required
from app.constants.system_constants import SuccessMessages
from app.routes.dashboard_restx_models import DASHBOARD_CHART_FIELDS
from app.services.dashboard.dashboard_charts_service import get_chart_data
from app.services.dashboard.dashboard_overview_service import get_system_overview, get_system_status

ns = Namespace("dashboard", description="系统仪表板")

ErrorEnvelope = get_error_envelope_model(ns)

DashboardChartsLogTrendItem = ns.model(
    "DashboardChartsLogTrendItem",
    {
        "date": fields.String(),
        "error_count": fields.Integer(),
        "warning_count": fields.Integer(),
    },
)

DashboardChartsLogLevelItem = ns.model(
    "DashboardChartsLogLevelItem",
    {
        "level": fields.String(),
        "count": fields.Integer(),
    },
)

DashboardChartsTaskStatusItem = ns.model(
    "DashboardChartsTaskStatusItem",
    {
        "status": fields.String(),
        "count": fields.Integer(),
    },
)

DashboardChartsSyncTrendItem = ns.model(
    "DashboardChartsSyncTrendItem",
    {
        "date": fields.String(),
        "count": fields.Integer(),
    },
)

DashboardChartsData = ns.model(
    "DashboardChartsData",
    {
        "log_trend": fields.List(fields.Nested(DashboardChartsLogTrendItem), required=False),
        "log_levels": fields.List(fields.Nested(DashboardChartsLogLevelItem), required=False),
        "task_status": fields.List(fields.Nested(DashboardChartsTaskStatusItem), required=False),
        "sync_trend": fields.List(fields.Nested(DashboardChartsSyncTrendItem), required=False),
    },
)

DashboardOverviewCount = ns.model(
    "DashboardOverviewCount",
    {
        "total": fields.Integer(),
        "active": fields.Integer(),
    },
)

DashboardOverviewAccountsCount = ns.model(
    "DashboardOverviewAccountsCount",
    {
        "total": fields.Integer(),
        "active": fields.Integer(),
        "locked": fields.Integer(),
    },
)

DashboardOverviewClassificationItem = ns.model(
    "DashboardOverviewClassificationItem",
    {
        "name": fields.String(),
        "display_name": fields.String(),
        "color": fields.String(required=False),
        "priority": fields.Integer(required=False),
        "count": fields.Integer(),
    },
)

DashboardOverviewClassifiedAccounts = ns.model(
    "DashboardOverviewClassifiedAccounts",
    {
        "total": fields.Integer(),
        "auto": fields.Integer(),
        "classifications": fields.List(fields.Nested(DashboardOverviewClassificationItem)),
    },
)

DashboardOverviewCapacity = ns.model(
    "DashboardOverviewCapacity",
    {
        "total_gb": fields.Float(),
        "usage_percent": fields.Integer(),
    },
)

DashboardOverviewDatabases = ns.model(
    "DashboardOverviewDatabases",
    {
        "total": fields.Integer(),
        "active": fields.Integer(),
        "inactive": fields.Integer(),
    },
)

DashboardOverviewData = ns.model(
    "DashboardOverviewData",
    {
        "users": fields.Nested(DashboardOverviewCount),
        "instances": fields.Nested(DashboardOverviewCount),
        "accounts": fields.Nested(DashboardOverviewAccountsCount),
        "classified_accounts": fields.Nested(DashboardOverviewClassifiedAccounts),
        "capacity": fields.Nested(DashboardOverviewCapacity),
        "databases": fields.Nested(DashboardOverviewDatabases),
    },
)

DashboardStatusMemory = ns.model(
    "DashboardStatusMemory",
    {
        "used": fields.Integer(),
        "total": fields.Integer(),
        "percent": fields.Float(),
    },
)

DashboardStatusDisk = ns.model(
    "DashboardStatusDisk",
    {
        "used": fields.Integer(),
        "total": fields.Integer(),
        "percent": fields.Float(),
    },
)

DashboardStatusSystem = ns.model(
    "DashboardStatusSystem",
    {
        "cpu": fields.Float(),
        "memory": fields.Nested(DashboardStatusMemory),
        "disk": fields.Nested(DashboardStatusDisk),
    },
)

DashboardStatusServices = ns.model(
    "DashboardStatusServices",
    {
        "database": fields.String(),
        "redis": fields.String(),
    },
)

DashboardStatusData = ns.model(
    "DashboardStatusData",
    {
        "system": fields.Nested(DashboardStatusSystem),
        "services": fields.Nested(DashboardStatusServices),
        "uptime": fields.String(),
    },
)

DashboardOverviewSuccessEnvelope = make_success_envelope_model(
    ns,
    "DashboardOverviewSuccessEnvelope",
    DashboardOverviewData,
)

DashboardStatusSuccessEnvelope = make_success_envelope_model(
    ns,
    "DashboardStatusSuccessEnvelope",
    DashboardStatusData,
)

DashboardChartsSuccessEnvelope = make_success_envelope_model(
    ns,
    "DashboardChartsSuccessEnvelope",
    DashboardChartsData,
)

DashboardActivitiesSuccessEnvelope = make_success_envelope_model(
    ns,
    "DashboardActivitiesSuccessEnvelope",
)


@ns.route("/overview")
class DashboardOverviewResource(BaseResource):
    method_decorators = [api_login_required]

    @ns.response(200, "OK", DashboardOverviewSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            overview = get_system_overview()
            return self.success(
                data=overview,
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="dashboard",
            action="get_dashboard_overview",
            public_error="获取系统概览失败",
        )


@ns.route("/charts")
class DashboardChartsResource(BaseResource):
    method_decorators = [api_login_required]

    @ns.response(200, "OK", DashboardChartsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        chart_type = request.args.get("type", "all", type=str)

        def _execute():
            charts = get_chart_data(chart_type)
            response_fields = {key: DASHBOARD_CHART_FIELDS[key] for key in charts if key in DASHBOARD_CHART_FIELDS}
            payload = marshal(charts, response_fields)
            return self.success(
                data=payload,
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="dashboard",
            action="get_dashboard_charts",
            public_error="获取仪表板图表失败",
            context={"chart_type": chart_type},
        )


@ns.route("/activities")
class DashboardActivitiesResource(BaseResource):
    method_decorators = [api_login_required]

    @ns.response(200, "OK", DashboardActivitiesSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            return self.success(data=[], message=SuccessMessages.OPERATION_SUCCESS)

        return self.safe_call(
            _execute,
            module="dashboard",
            action="list_dashboard_activities",
            public_error="获取仪表板活动失败",
        )


@ns.route("/status")
class DashboardStatusResource(BaseResource):
    method_decorators = [api_login_required]

    @ns.response(200, "OK", DashboardStatusSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            status = get_system_status()
            return self.success(
                data=status,
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="dashboard",
            action="get_dashboard_status",
            public_error="获取系统状态失败",
        )

