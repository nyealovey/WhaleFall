"""Dashboard namespace (Phase 3 全量覆盖 - 仪表板模块)."""

from __future__ import annotations

from typing import ClassVar

from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required
from app.api.v1.resources.query_parsers import new_parser
from app.api.v1.restx_models.dashboard import DASHBOARD_CHART_FIELDS
from app.core.constants.system_constants import SuccessMessages
from app.services.dashboard.dashboard_charts_service import get_chart_data
from app.services.dashboard.dashboard_overview_service import get_system_overview, get_system_status

ns = Namespace("dashboard", description="系统仪表板")

ErrorEnvelope = get_error_envelope_model(ns)

DashboardChartsLogTrendItem = ns.model(
    "DashboardChartsLogTrendItem",
    {
        "date": fields.String(description="日期(YYYY-MM-DD)", example="2025-01-01"),
        "error_count": fields.Integer(description="错误数量", example=1),
        "warning_count": fields.Integer(description="警告数量", example=2),
    },
)

DashboardChartsLogLevelItem = ns.model(
    "DashboardChartsLogLevelItem",
    {
        "level": fields.String(description="日志级别", example="INFO"),
        "count": fields.Integer(description="数量", example=100),
    },
)

DashboardChartsTaskStatusItem = ns.model(
    "DashboardChartsTaskStatusItem",
    {
        "status": fields.String(description="任务状态", example="success"),
        "count": fields.Integer(description="数量", example=10),
    },
)

DashboardChartsSyncTrendItem = ns.model(
    "DashboardChartsSyncTrendItem",
    {
        "date": fields.String(description="日期(YYYY-MM-DD)", example="2025-01-01"),
        "count": fields.Integer(description="数量", example=3),
    },
)

DashboardChartsData = ns.model(
    "DashboardChartsData",
    {
        "log_trend": fields.List(
            fields.Nested(DashboardChartsLogTrendItem),
            required=False,
            description="日志趋势",
        ),
        "log_levels": fields.List(
            fields.Nested(DashboardChartsLogLevelItem),
            required=False,
            description="按 level 分布",
        ),
        "task_status": fields.List(
            fields.Nested(DashboardChartsTaskStatusItem),
            required=False,
            description="任务状态分布",
        ),
        "sync_trend": fields.List(
            fields.Nested(DashboardChartsSyncTrendItem),
            required=False,
            description="同步趋势",
        ),
    },
)

DashboardOverviewCount = ns.model(
    "DashboardOverviewCount",
    {
        "total": fields.Integer(description="总数", example=10),
        "active": fields.Integer(description="启用数", example=9),
    },
)

DashboardOverviewAccountsCount = ns.model(
    "DashboardOverviewAccountsCount",
    {
        "total": fields.Integer(description="总数", example=100),
        "active": fields.Integer(description="启用数", example=90),
        "locked": fields.Integer(description="锁定数", example=2),
    },
)

DashboardOverviewClassificationItem = ns.model(
    "DashboardOverviewClassificationItem",
    {
        "name": fields.String(description="分类名称", example="高风险"),
        "display_name": fields.String(description="展示名", example="高风险"),
        "color": fields.String(required=False, description="颜色(可选)", example="#FF0000"),
        "priority": fields.Integer(required=False, description="优先级(可选)", example=10),
        "count": fields.Integer(description="数量", example=12),
    },
)

DashboardOverviewClassifiedAccounts = ns.model(
    "DashboardOverviewClassifiedAccounts",
    {
        "total": fields.Integer(description="已分类账号总数", example=80),
        "auto": fields.Integer(description="自动分类账号数", example=60),
        "classifications": fields.List(
            fields.Nested(DashboardOverviewClassificationItem),
            description="分类分布",
        ),
    },
)

DashboardOverviewCapacity = ns.model(
    "DashboardOverviewCapacity",
    {
        "total_gb": fields.Float(description="总容量(GB)", example=123.4),
        "usage_percent": fields.Integer(description="使用率(百分比)", example=75),
    },
)

DashboardOverviewDatabases = ns.model(
    "DashboardOverviewDatabases",
    {
        "total": fields.Integer(description="总数", example=120),
        "active": fields.Integer(description="启用数", example=110),
        "inactive": fields.Integer(description="停用数", example=10),
    },
)

DashboardOverviewData = ns.model(
    "DashboardOverviewData",
    {
        "users": fields.Nested(DashboardOverviewCount, description="用户统计"),
        "instances": fields.Nested(DashboardOverviewCount, description="实例统计"),
        "accounts": fields.Nested(DashboardOverviewAccountsCount, description="账号统计"),
        "classified_accounts": fields.Nested(DashboardOverviewClassifiedAccounts, description="分类账号统计"),
        "capacity": fields.Nested(DashboardOverviewCapacity, description="容量统计"),
        "databases": fields.Nested(DashboardOverviewDatabases, description="数据库统计"),
    },
)

DashboardStatusMemory = ns.model(
    "DashboardStatusMemory",
    {
        "used": fields.Integer(description="已用(MB)", example=1024),
        "total": fields.Integer(description="总量(MB)", example=2048),
        "percent": fields.Float(description="使用率(0-100)", example=50.0),
    },
)

DashboardStatusDisk = ns.model(
    "DashboardStatusDisk",
    {
        "used": fields.Integer(description="已用(GB)", example=100),
        "total": fields.Integer(description="总量(GB)", example=200),
        "percent": fields.Float(description="使用率(0-100)", example=50.0),
    },
)

DashboardStatusSystem = ns.model(
    "DashboardStatusSystem",
    {
        "cpu": fields.Float(description="CPU 使用率(0-100)", example=12.5),
        "memory": fields.Nested(DashboardStatusMemory, description="内存使用情况"),
        "disk": fields.Nested(DashboardStatusDisk, description="磁盘使用情况"),
    },
)

DashboardStatusServices = ns.model(
    "DashboardStatusServices",
    {
        "database": fields.String(description="数据库服务状态", example="connected"),
        "redis": fields.String(description="Redis 服务状态", example="connected"),
    },
)

DashboardStatusData = ns.model(
    "DashboardStatusData",
    {
        "system": fields.Nested(DashboardStatusSystem, description="系统状态"),
        "services": fields.Nested(DashboardStatusServices, description="依赖服务状态"),
        "uptime": fields.String(description="运行时长", example="3 days"),
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

_dashboard_charts_query_parser = new_parser()
_dashboard_charts_query_parser.add_argument("type", type=str, default="all", location="args")

DashboardActivitiesSuccessEnvelope = make_success_envelope_model(
    ns,
    "DashboardActivitiesSuccessEnvelope",
)


@ns.route("/overview")
class DashboardOverviewResource(BaseResource):
    """仪表板概览资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", DashboardOverviewSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取系统概览."""

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
    """仪表板图表资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", DashboardChartsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_dashboard_charts_query_parser)
    def get(self):
        """获取仪表板图表数据."""

        def _execute():
            args = _dashboard_charts_query_parser.parse_args()
            raw_type = args.get("type")
            chart_type = raw_type.strip() if isinstance(raw_type, str) else ""
            if not chart_type:
                chart_type = "all"
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
        )


@ns.route("/activities")
class DashboardActivitiesResource(BaseResource):
    """仪表板活动资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", DashboardActivitiesSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取仪表板活动."""

        def _execute():
            activities: list[dict[str, object]] = []
            return self.success(data=activities, message=SuccessMessages.OPERATION_SUCCESS)

        return self.safe_call(
            _execute,
            module="dashboard",
            action="list_dashboard_activities",
            public_error="获取仪表板活动失败",
        )


@ns.route("/status")
class DashboardStatusResource(BaseResource):
    """仪表板状态资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", DashboardStatusSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取系统状态."""

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
