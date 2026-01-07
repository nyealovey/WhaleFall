"""Databases namespace (Phase 2 核心域迁移 - Ledgers)."""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import ClassVar

from flask import Response, request
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.restx_models.instances import (
    INSTANCE_DATABASE_SIZE_ENTRY_FIELDS,
    INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS,
)
from app.constants import HttpStatus
from app.errors import NotFoundError, ValidationError
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.services.instances.instance_database_sizes_service import InstanceDatabaseSizesService
from app.services.instances.instance_database_table_sizes_service import (
    InstanceDatabaseTableSizesService,
)
from app.services.instances.instance_detail_read_service import InstanceDetailReadService
from app.services.ledgers.database_ledger_service import DatabaseLedgerService
from app.types.instance_database_sizes import InstanceDatabaseSizesQuery
from app.types.instance_database_table_sizes import InstanceDatabaseTableSizesQuery
from app.utils.decorators import require_csrf
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.spreadsheet_formula_safety import sanitize_csv_row
from app.utils.time_utils import time_utils

import app.services.database_sync as database_sync_module

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

DatabaseSizeEntryModel = ns.model("DatabaseSizeEntry", INSTANCE_DATABASE_SIZE_ENTRY_FIELDS)

DatabasesSizesData = ns.model(
    "DatabasesSizesData",
    {
        "total": fields.Integer(),
        "limit": fields.Integer(),
        "offset": fields.Integer(),
        "active_count": fields.Integer(required=False),
        "filtered_count": fields.Integer(required=False),
        "total_size_mb": fields.Raw(required=False),
        "databases": fields.List(fields.Nested(DatabaseSizeEntryModel)),
    },
)
DatabasesSizesSuccessEnvelope = make_success_envelope_model(
    ns,
    "DatabasesSizesSuccessEnvelope",
    DatabasesSizesData,
)

DatabaseTableSizeEntryModel = ns.model("DatabaseTableSizeEntry", INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS)

DatabaseTableSizesData = ns.model(
    "DatabaseTableSizesData",
    {
        "total": fields.Integer(),
        "limit": fields.Integer(),
        "offset": fields.Integer(),
        "collected_at": fields.String(required=False),
        "tables": fields.List(fields.Nested(DatabaseTableSizeEntryModel)),
        "saved_count": fields.Integer(required=False),
        "deleted_count": fields.Integer(required=False),
        "elapsed_ms": fields.Integer(required=False),
    },
)
DatabaseTableSizesSuccessEnvelope = make_success_envelope_model(
    ns,
    "DatabaseTableSizesSuccessEnvelope",
    DatabaseTableSizesData,
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
        instance_id = request.args.get("instance_id", type=int)
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
                instance_id=instance_id,
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
                "instance_id": instance_id,
                "tags_count": len(tags),
                "page": page,
                "limit": limit,
            },
        )


@ns.route("/ledgers/export")
class DatabaseLedgersExportResource(BaseResource):
    """数据库台账导出资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK")
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("database_ledger.view")
    def get(self):
        """导出数据库台账."""
        search = (request.args.get("search", "", type=str) or "").strip()
        db_type = request.args.get("db_type", "all", type=str)
        instance_id = request.args.get("instance_id", type=int)
        tags = [tag.strip() for tag in request.args.getlist("tags") if tag.strip()]
        if not tags:
            raw_tags = request.args.get("tags", "")
            if raw_tags:
                tags = [item.strip() for item in raw_tags.split(",") if item.strip()]

        def _execute() -> Response:
            service = DatabaseLedgerService()
            rows = service.iterate_all(search=search, db_type=db_type, instance_id=instance_id, tags=tags)

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "数据库名称",
                    "实例名称",
                    "主机",
                    "数据库类型",
                    "标签",
                    "最新容量",
                    "最后采集时间",
                    "同步状态",
                ],
            )

            for row in rows:
                instance = row.instance
                capacity = row.capacity
                status = row.sync_status
                tag_labels = ", ".join((tag.display_name or tag.name) for tag in row.tags).strip(", ")
                writer.writerow(
                    sanitize_csv_row(
                        [
                            row.database_name or "-",
                            instance.name or "-",
                            instance.host or "-",
                            row.db_type or "-",
                            tag_labels or "-",
                            capacity.label or "未采集",
                            capacity.collected_at or "无",
                            status.label or "未知",
                        ],
                    ),
                )

            output.seek(0)
            timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
            filename = f"database_ledger_{timestamp}.csv"
            return Response(
                output.getvalue(),
                mimetype="text/csv; charset=utf-8",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        return self.safe_call(
            _execute,
            module="databases_ledgers",
            action="export_database_ledger",
            public_error="导出数据库台账失败",
            context={
                "search": search,
                "db_type": db_type,
                "tags_count": len(tags),
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


@ns.route("/sizes")
class DatabasesSizesResource(BaseResource):
    """数据库大小资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", DatabasesSizesSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
        """获取实例数据库大小数据."""
        query_snapshot = request.args.to_dict(flat=False)

        instance_id = request.args.get("instance_id", type=int)
        if not instance_id:
            raise ValidationError("缺少 instance_id")

        def _parse_date(value: str | None, field: str) -> date | None:
            if not value:
                return None
            try:
                parsed_dt = time_utils.to_china(value + "T00:00:00")
                return parsed_dt.date() if parsed_dt else None
            except Exception as exc:
                raise ValidationError(f"{field} 格式错误,应为 YYYY-MM-DD") from exc

        def _parse_int(value: object | None, *, field: str, default: int) -> int:
            if value is None or value == "":
                return default

            def _convert() -> int:
                if isinstance(value, (bool, int, float, str)):
                    return int(value)
                raise TypeError

            try:
                return _convert()
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"{field} 必须为整数") from exc

        def _execute():
            InstanceDetailReadService().get_active_instance(instance_id)

            start_date_raw = request.args.get("start_date")
            end_date_raw = request.args.get("end_date")
            database_name = request.args.get("database_name")
            latest_only = request.args.get("latest_only", "false").lower() == "true"
            include_inactive = request.args.get("include_inactive", "false").lower() == "true"

            limit = _parse_int(request.args.get("limit"), field="limit", default=100)
            offset = _parse_int(request.args.get("offset"), field="offset", default=0)

            options = InstanceDatabaseSizesQuery(
                instance_id=instance_id,
                database_name=database_name,
                start_date=_parse_date(start_date_raw, "start_date"),
                end_date=_parse_date(end_date_raw, "end_date"),
                include_inactive=include_inactive,
                limit=limit,
                offset=offset,
            )

            result = InstanceDatabaseSizesService().fetch_sizes(options, latest_only=latest_only)
            databases = marshal(result.databases, INSTANCE_DATABASE_SIZE_ENTRY_FIELDS)

            payload: dict[str, object] = {
                "total": result.total,
                "limit": result.limit,
                "offset": result.offset,
                "databases": databases,
            }

            if latest_only:
                payload.update(
                    {
                        "active_count": getattr(result, "active_count", 0),
                        "filtered_count": getattr(result, "filtered_count", 0),
                        "total_size_mb": getattr(result, "total_size_mb", 0),
                    },
                )

            return self.success(data=payload, message="数据库大小数据获取成功")

        return self.safe_call(
            _execute,
            module="database_aggregations",
            action="get_database_sizes",
            public_error="获取数据库大小历史数据失败",
            expected_exceptions=(ValidationError,),
            context={"instance_id": instance_id, "query_params": query_snapshot},
        )


@ns.route("/<int:database_id>/tables/sizes")
class DatabaseTableSizesSnapshotResource(BaseResource):
    """数据库表容量快照资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", DatabaseTableSizesSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, database_id: int):
        """获取指定数据库的表容量快照."""
        query_snapshot = request.args.to_dict(flat=False)

        def _parse_int(value: object | None, *, field: str, default: int) -> int:
            if value is None or value == "":
                return default

            def _convert() -> int:
                if isinstance(value, (bool, int, float, str)):
                    return int(value)
                raise TypeError

            try:
                return _convert()
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"{field} 必须为整数") from exc

        def _execute():
            record = InstanceDatabase.query.filter_by(id=database_id).first()
            if record is None:
                raise NotFoundError("数据库不存在")

            InstanceDetailReadService().get_active_instance(record.instance_id)

            schema_name = request.args.get("schema_name")
            table_name = request.args.get("table_name")

            limit = _parse_int(request.args.get("limit"), field="limit", default=200)
            if limit > 2000:
                raise ValidationError("limit 最大为 2000")
            offset = _parse_int(request.args.get("offset"), field="offset", default=0)

            options = InstanceDatabaseTableSizesQuery(
                instance_id=record.instance_id,
                database_name=record.database_name,
                schema_name=schema_name,
                table_name=table_name,
                limit=limit,
                offset=offset,
            )

            result = InstanceDatabaseTableSizesService().fetch_snapshot(options)
            tables = marshal(result.tables, INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS, skip_none=True)

            payload: dict[str, object] = {
                "total": result.total,
                "limit": result.limit,
                "offset": result.offset,
                "collected_at": result.collected_at,
                "tables": tables,
            }
            return self.success(data=payload, message="表容量快照获取成功")

        return self.safe_call(
            _execute,
            module="databases",
            action="get_database_table_sizes_snapshot",
            public_error="获取表容量快照失败",
            expected_exceptions=(ValidationError,),
            context={"database_id": database_id, "query_params": query_snapshot},
        )


@ns.route("/<int:database_id>/tables/sizes/actions/refresh")
class DatabaseTableSizesRefreshResource(BaseResource):
    """数据库表容量刷新动作资源."""

    method_decorators: ClassVar[list] = [
        api_login_required,
        api_permission_required("instance_management.instance_list.sync_capacity"),
    ]

    @ns.response(200, "OK", DatabaseTableSizesSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self, database_id: int):
        """手动采集并刷新表容量快照."""
        query_snapshot = request.args.to_dict(flat=False)

        def _parse_int(value: object | None, *, field: str, default: int) -> int:
            if value is None or value == "":
                return default

            def _convert() -> int:
                if isinstance(value, (bool, int, float, str)):
                    return int(value)
                raise TypeError

            try:
                return _convert()
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"{field} 必须为整数") from exc

        def _execute():
            record = InstanceDatabase.query.filter_by(id=database_id).first()
            if record is None:
                raise NotFoundError("数据库不存在")

            instance = Instance.query.filter_by(id=record.instance_id).first()
            if instance is None:
                raise NotFoundError("实例不存在")

            coordinator = database_sync_module.TableSizeCoordinator(instance)
            if not coordinator.connect(record.database_name):
                return self.error_message(
                    f"无法连接到实例 {instance.name}",
                    status=HttpStatus.CONFLICT,
                    message_key="DATABASE_CONNECTION_ERROR",
                    extra={"instance_id": instance.id, "database_name": record.database_name},
                )

            try:
                try:
                    outcome = coordinator.refresh_snapshot(record.database_name)
                except (ValueError, RuntimeError, ConnectionError, TimeoutError, OSError) as exc:
                    return self.error_message(
                        str(exc) or "表容量采集失败",
                        status=HttpStatus.CONFLICT,
                        message_key="SYNC_DATA_ERROR",
                        extra={"instance_id": instance.id, "database_name": record.database_name},
                    )

                schema_name = request.args.get("schema_name")
                table_name = request.args.get("table_name")
                limit = _parse_int(request.args.get("limit"), field="limit", default=200)
                if limit > 2000:
                    raise ValidationError("limit 最大为 2000")
                offset = _parse_int(request.args.get("offset"), field="offset", default=0)

                options = InstanceDatabaseTableSizesQuery(
                    instance_id=instance.id,
                    database_name=record.database_name,
                    schema_name=schema_name,
                    table_name=table_name,
                    limit=limit,
                    offset=offset,
                )
                result = InstanceDatabaseTableSizesService().fetch_snapshot(options)
                tables = marshal(result.tables, INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS, skip_none=True)

                payload: dict[str, object] = {
                    "total": result.total,
                    "limit": result.limit,
                    "offset": result.offset,
                    "collected_at": result.collected_at,
                    "tables": tables,
                    "saved_count": outcome.saved_count,
                    "deleted_count": outcome.deleted_count,
                    "elapsed_ms": outcome.elapsed_ms,
                }
                return self.success(data=payload, message="表容量快照刷新成功")
            finally:
                coordinator.disconnect()

        return self.safe_call(
            _execute,
            module="databases",
            action="refresh_database_table_sizes",
            public_error="刷新表容量快照失败",
            expected_exceptions=(ValidationError,),
            context={"database_id": database_id, "query_params": query_snapshot},
        )
