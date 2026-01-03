"""Databases namespace (Phase 2 核心域迁移 - Ledgers)."""

from __future__ import annotations

from typing import ClassVar

from flask import request
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.services.ledgers.database_ledger_service import DatabaseLedgerService
from app.utils.pagination_utils import resolve_page, resolve_page_size

ns = Namespace("databases", description="数据库管理")

ErrorEnvelope = get_error_envelope_model(ns)

DatabaseLedgerTagModel = ns.model(
    "DatabaseLedgerTag",
    {
        "name": fields.String(description="标签代码", example="prod"),
        "display_name": fields.String(description="标签展示名", example="生产"),
        "color": fields.String(description="颜色 key", example="red"),
    },
)

DatabaseLedgerInstanceModel = ns.model(
    "DatabaseLedgerInstance",
    {
        "id": fields.Integer(description="实例 ID", example=1),
        "name": fields.String(description="实例名称", example="prod-mysql-1"),
        "host": fields.String(description="主机", example="127.0.0.1"),
        "db_type": fields.String(description="数据库类型", example="mysql"),
    },
)

DatabaseLedgerCapacityModel = ns.model(
    "DatabaseLedgerCapacity",
    {
        "size_mb": fields.Integer(description="容量(MB)", example=1024),
        "size_bytes": fields.Integer(description="容量(Bytes)", example=1073741824),
        "label": fields.String(description="展示标签", example="1.0 GB"),
        "collected_at": fields.String(description="采集时间(ISO8601)", example="2025-01-01T00:00:00"),
    },
)

DatabaseLedgerSyncStatusModel = ns.model(
    "DatabaseLedgerSyncStatus",
    {
        "value": fields.String(description="状态值", example="ok"),
        "label": fields.String(description="状态展示", example="正常"),
        "variant": fields.String(description="UI variant", example="success"),
    },
)

DatabaseLedgerItemModel = ns.model(
    "DatabaseLedgerItem",
    {
        "id": fields.Integer(description="数据库 ID", example=1),
        "database_name": fields.String(description="数据库名称", example="app_db"),
        "instance": fields.Nested(DatabaseLedgerInstanceModel, description="实例信息"),
        "db_type": fields.String(description="数据库类型", example="mysql"),
        "capacity": fields.Nested(DatabaseLedgerCapacityModel, description="容量信息"),
        "sync_status": fields.Nested(DatabaseLedgerSyncStatusModel, description="同步状态"),
        "tags": fields.List(fields.Nested(DatabaseLedgerTagModel), description="标签列表"),
    },
)

DatabaseLedgersListData = ns.model(
    "DatabaseLedgersListData",
    {
        "items": fields.List(fields.Nested(DatabaseLedgerItemModel), description="数据库台账列表"),
        "total": fields.Integer(description="总数", example=1),
        "page": fields.Integer(description="页码", example=1),
        "per_page": fields.Integer(description="分页大小", example=20),
    },
)

DatabaseLedgersListSuccessEnvelope = make_success_envelope_model(
    ns,
    "DatabaseLedgersListSuccessEnvelope",
    DatabaseLedgersListData,
)

DatabaseCapacityTrendPointModel = ns.model(
    "DatabaseCapacityTrendPoint",
    {
        "collected_at": fields.String(description="采集时间(ISO8601)", example="2025-01-01T00:00:00"),
        "collected_date": fields.String(description="采集日期(YYYY-MM-DD)", example="2025-01-01"),
        "size_mb": fields.Integer(description="容量(MB)", example=1024),
        "size_bytes": fields.Integer(description="容量(Bytes)", example=1073741824),
        "label": fields.String(description="展示标签", example="1.0 GB"),
    },
)

DatabaseCapacityTrendDatabaseModel = ns.model(
    "DatabaseCapacityTrendDatabase",
    {
        "id": fields.Integer(description="数据库 ID", example=1),
        "name": fields.String(description="数据库名称", example="app_db"),
        "instance_id": fields.Integer(description="实例 ID", example=1),
        "instance_name": fields.String(description="实例名称", example="prod-mysql-1"),
        "db_type": fields.String(description="数据库类型", example="mysql"),
    },
)

DatabaseCapacityTrendData = ns.model(
    "DatabaseCapacityTrendData",
    {
        "database": fields.Nested(DatabaseCapacityTrendDatabaseModel, description="数据库信息"),
        "points": fields.List(fields.Nested(DatabaseCapacityTrendPointModel), description="趋势点列表"),
    },
)

DatabaseCapacityTrendSuccessEnvelope = make_success_envelope_model(
    ns,
    "DatabaseCapacityTrendSuccessEnvelope",
    DatabaseCapacityTrendData,
)


def _parse_tags() -> list[str]:
    return [tag.strip() for tag in request.args.getlist("tags") if tag and tag.strip()]


@ns.route("/ledgers")
class DatabaseLedgersResource(BaseResource):
    """数据库台账资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("database_ledger.view")]

    @ns.response(200, "OK", DatabaseLedgersListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取数据库台账."""
        search = (request.args.get("search") or "").strip()
        db_type = request.args.get("db_type", "all")
        tags = _parse_tags()
        page = resolve_page(request.args, default=1, minimum=1)
        limit = resolve_page_size(
            request.args,
            default=20,
            minimum=1,
            maximum=200,
        )

        def _execute():
            result = DatabaseLedgerService().get_ledger(
                search=search,
                db_type=db_type,
                tags=tags,
                page=page,
                per_page=limit,
            )
            items = marshal(result.items, DatabaseLedgerItemModel)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "per_page": result.limit,
                },
                message="获取数据库台账成功",
            )

        return self.safe_call(
            _execute,
            module="databases_ledgers",
            action="fetch_ledger",
            public_error="获取数据库台账失败",
            context={
                "search": search,
                "db_type": db_type,
                "tags_count": len(tags),
                "page": page,
                "limit": limit,
            },
        )


@ns.route("/ledgers/<int:database_id>/capacity-trend")
class DatabaseLedgerCapacityTrendResource(BaseResource):
    """数据库容量走势资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("database_ledger.view")]

    @ns.response(200, "OK", DatabaseCapacityTrendSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, database_id: int):
        """获取数据库容量走势."""
        days = request.args.get("days", DatabaseLedgerService.DEFAULT_TREND_DAYS, type=int)

        def _execute():
            result = DatabaseLedgerService().get_capacity_trend(database_id, days=days)
            payload = marshal(result, DatabaseCapacityTrendData)
            return self.success(data=payload, message="获取容量走势成功")

        return self.safe_call(
            _execute,
            module="databases_ledgers",
            action="fetch_capacity_trend",
            public_error="获取容量走势失败",
            context={"database_id": database_id, "days": days},
        )
