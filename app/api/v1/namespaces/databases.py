"""Databases namespace (Phase 2 核心域迁移 - Ledgers)."""

from __future__ import annotations

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
        "name": fields.String(),
        "display_name": fields.String(),
        "color": fields.String(),
    },
)

DatabaseLedgerInstanceModel = ns.model(
    "DatabaseLedgerInstance",
    {
        "id": fields.Integer(),
        "name": fields.String(),
        "host": fields.String(),
        "db_type": fields.String(),
    },
)

DatabaseLedgerCapacityModel = ns.model(
    "DatabaseLedgerCapacity",
    {
        "size_mb": fields.Integer(),
        "size_bytes": fields.Integer(),
        "label": fields.String(),
        "collected_at": fields.String(),
    },
)

DatabaseLedgerSyncStatusModel = ns.model(
    "DatabaseLedgerSyncStatus",
    {
        "value": fields.String(),
        "label": fields.String(),
        "variant": fields.String(),
    },
)

DatabaseLedgerItemModel = ns.model(
    "DatabaseLedgerItem",
    {
        "id": fields.Integer(),
        "database_name": fields.String(),
        "instance": fields.Nested(DatabaseLedgerInstanceModel),
        "db_type": fields.String(),
        "capacity": fields.Nested(DatabaseLedgerCapacityModel),
        "sync_status": fields.Nested(DatabaseLedgerSyncStatusModel),
        "tags": fields.List(fields.Nested(DatabaseLedgerTagModel)),
    },
)

DatabaseLedgersListData = ns.model(
    "DatabaseLedgersListData",
    {
        "items": fields.List(fields.Nested(DatabaseLedgerItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "per_page": fields.Integer(),
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
        "collected_at": fields.String(),
        "collected_date": fields.String(),
        "size_mb": fields.Integer(),
        "size_bytes": fields.Integer(),
        "label": fields.String(),
    },
)

DatabaseCapacityTrendDatabaseModel = ns.model(
    "DatabaseCapacityTrendDatabase",
    {
        "id": fields.Integer(),
        "name": fields.String(),
        "instance_id": fields.Integer(),
        "instance_name": fields.String(),
        "db_type": fields.String(),
    },
)

DatabaseCapacityTrendData = ns.model(
    "DatabaseCapacityTrendData",
    {
        "database": fields.Nested(DatabaseCapacityTrendDatabaseModel),
        "points": fields.List(fields.Nested(DatabaseCapacityTrendPointModel)),
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
    method_decorators = [api_login_required, api_permission_required("database_ledger.view")]

    @ns.response(200, "OK", DatabaseLedgersListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        search = (request.args.get("search") or "").strip()
        db_type = request.args.get("db_type", "all")
        tags = _parse_tags()
        page = resolve_page(request.args, default=1, minimum=1)
        limit = resolve_page_size(
            request.args,
            default=20,
            minimum=1,
            maximum=200,
            module="databases_ledgers",
            action="fetch_ledger",
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
    method_decorators = [api_login_required, api_permission_required("database_ledger.view")]

    @ns.response(200, "OK", DatabaseCapacityTrendSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, database_id: int):
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

