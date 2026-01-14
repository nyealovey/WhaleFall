"""Databases namespace (Phase 2 核心域迁移 - Ledgers)."""

from __future__ import annotations

from datetime import date
from typing import ClassVar, cast

from flask import Response, request
from flask_restx import Namespace, fields, marshal

import app.services.database_sync as database_sync_module
from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import bool_with_default, new_parser, split_comma_separated
from app.api.v1.restx_models.databases import (
    DATABASE_OPTION_ITEM_FIELDS,
    DATABASES_OPTIONS_RESPONSE_FIELDS,
)
from app.api.v1.restx_models.instances import (
    INSTANCE_DATABASE_SIZE_ENTRY_FIELDS,
    INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS,
)
from app.core.constants import HttpStatus
from app.core.constants.validation_limits import DATABASE_TABLE_SIZES_LIMIT_MAX
from app.core.exceptions import NotFoundError, ValidationError
from app.core.types.common_filter_options import CommonDatabasesOptionsFilters
from app.core.types.instance_database_sizes import InstanceDatabaseSizesQuery
from app.core.types.instance_database_table_sizes import InstanceDatabaseTableSizesQuery
from app.services.common.filter_options_service import FilterOptionsService
from app.services.files.database_ledger_export_service import DatabaseLedgerExportService
from app.services.instances.instance_database_detail_read_service import (
    InstanceDatabaseDetailReadService,
)
from app.services.instances.instance_database_sizes_service import InstanceDatabaseSizesService
from app.services.instances.instance_database_table_sizes_service import (
    InstanceDatabaseTableSizesService,
)
from app.services.instances.instance_detail_read_service import InstanceDetailReadService
from app.services.ledgers.database_ledger_service import DatabaseLedgerService
from app.utils.decorators import require_csrf
from app.utils.time_utils import time_utils

ns = Namespace("databases", description="数据库管理")

ErrorEnvelope = get_error_envelope_model(ns)

DatabaseOptionItemModel = ns.model("DatabaseOptionItem", DATABASE_OPTION_ITEM_FIELDS)
DatabasesOptionsData = ns.model(
    "DatabasesOptionsData",
    {
        "databases": fields.List(fields.Nested(DatabaseOptionItemModel)),
        "total_count": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
    },
)
DatabasesOptionsSuccessEnvelope = make_success_envelope_model(ns, "DatabasesOptionsSuccessEnvelope", DatabasesOptionsData)

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
        "limit": fields.Integer(description="分页大小", example=20),
    },
)

DatabaseLedgersListSuccessEnvelope = make_success_envelope_model(
    ns,
    "DatabaseLedgersListSuccessEnvelope",
    DatabaseLedgersListData,
)

DatabaseSizeEntryModel = ns.model("DatabaseSizeEntry", INSTANCE_DATABASE_SIZE_ENTRY_FIELDS)

DatabasesSizesData = ns.model(
    "DatabasesSizesData",
    {
        "total": fields.Integer(),
        "limit": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
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
        "page": fields.Integer(),
        "pages": fields.Integer(),
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


_databases_options_query_parser = new_parser()
_databases_options_query_parser.add_argument("instance_id", type=int, location="args")
_databases_options_query_parser.add_argument("page", type=int, default=1, location="args")
_databases_options_query_parser.add_argument("limit", type=int, default=100, location="args")
_databases_options_query_parser.add_argument("offset", type=str, location="args")

_database_ledgers_query_parser = new_parser()
_database_ledgers_query_parser.add_argument("search", type=str, default="", location="args")
_database_ledgers_query_parser.add_argument("db_type", type=str, default="all", location="args")
_database_ledgers_query_parser.add_argument("instance_id", type=int, location="args")
_database_ledgers_query_parser.add_argument("tags", type=str, action="append", location="args")
_database_ledgers_query_parser.add_argument("page", type=int, default=1, location="args")
_database_ledgers_query_parser.add_argument("limit", type=int, default=20, location="args")

_database_ledgers_export_query_parser = new_parser()
_database_ledgers_export_query_parser.add_argument("search", type=str, default="", location="args")
_database_ledgers_export_query_parser.add_argument("db_type", type=str, default="all", location="args")
_database_ledgers_export_query_parser.add_argument("instance_id", type=int, location="args")
_database_ledgers_export_query_parser.add_argument("tags", type=str, action="append", location="args")

_databases_sizes_query_parser = new_parser()
_databases_sizes_query_parser.add_argument("instance_id", type=int, location="args")
_databases_sizes_query_parser.add_argument("start_date", type=str, location="args")
_databases_sizes_query_parser.add_argument("end_date", type=str, location="args")
_databases_sizes_query_parser.add_argument("database_name", type=str, location="args")
_databases_sizes_query_parser.add_argument("latest_only", type=bool_with_default(False), default=False, location="args")
_databases_sizes_query_parser.add_argument(
    "include_inactive",
    type=bool_with_default(False),
    default=False,
    location="args",
)
_databases_sizes_query_parser.add_argument("page", type=int, default=1, location="args")
_databases_sizes_query_parser.add_argument("limit", type=int, default=100, location="args")
_databases_sizes_query_parser.add_argument("offset", type=str, location="args")

_database_table_sizes_query_parser = new_parser()
_database_table_sizes_query_parser.add_argument("schema_name", type=str, location="args")
_database_table_sizes_query_parser.add_argument("table_name", type=str, location="args")
_database_table_sizes_query_parser.add_argument("page", type=int, default=1, location="args")
_database_table_sizes_query_parser.add_argument("limit", type=int, default=200, location="args")
_database_table_sizes_query_parser.add_argument("offset", type=str, location="args")


def _parse_tags(raw_tags: list[str] | None) -> list[str]:
    return split_comma_separated(raw_tags)


def _parse_optional_date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        parsed_dt = time_utils.to_china(value + "T00:00:00")
        return parsed_dt.date() if parsed_dt else None
    except Exception as exc:
        raise ValidationError(f"{field} 格式错误,应为 YYYY-MM-DD") from exc


@ns.route("/options")
class DatabasesOptionsResource(BaseResource):
    """数据库选项资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", DatabasesOptionsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_databases_options_query_parser)
    @api_permission_required("view")
    def get(self):
        """获取数据库选项."""

        def _execute():
            parsed = cast("dict[str, object]", _databases_options_query_parser.parse_args())

            if parsed.get("offset") is not None:
                raise ValidationError("分页参数已统一为 page/limit，不支持 offset")

            instance_id = parsed.get("instance_id")
            if not isinstance(instance_id, int) or instance_id <= 0:
                raise ValidationError("instance_id 为必填参数")

            instance = InstanceDetailReadService().get_instance_by_id(instance_id)
            if instance is None:
                raise NotFoundError("实例不存在")

            raw_page = parsed.get("page")
            page = max(int(raw_page) if isinstance(raw_page, int) else 1, 1)

            raw_limit = parsed.get("limit")
            limit = int(raw_limit) if isinstance(raw_limit, int) else 100
            limit = max(min(limit, 1000), 1)
            offset = (page - 1) * limit

            result = FilterOptionsService().get_common_databases_options(
                CommonDatabasesOptionsFilters(
                    instance_id=int(instance.id),
                    limit=limit,
                    offset=offset,
                ),
            )
            total_count = int(getattr(result, "total_count", 0) or 0)
            pages = (total_count + limit - 1) // limit if total_count else 0
            payload = marshal(
                {
                    "databases": getattr(result, "databases", []),
                    "total_count": total_count,
                    "page": page,
                    "pages": pages,
                    "limit": limit,
                },
                DATABASES_OPTIONS_RESPONSE_FIELDS,
            )
            return self.success(data=payload, message="数据库选项获取成功")

        return self.safe_call(
            _execute,
            module="databases",
            action="get_database_options",
            public_error="获取实例数据库列表失败",
            expected_exceptions=(ValidationError, NotFoundError),
        )


@ns.route("/ledgers")
class DatabaseLedgersResource(BaseResource):
    """数据库台账资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", DatabaseLedgersListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_database_ledgers_query_parser)
    def get(self):
        """获取数据库台账."""
        query_snapshot = request.args.to_dict(flat=False)

        def _execute():
            parsed = cast("dict[str, object]", _database_ledgers_query_parser.parse_args())
            search = str(parsed.get("search") or "").strip()
            db_type = str(parsed.get("db_type") or "all").strip() or "all"
            raw_instance_id = parsed.get("instance_id")
            instance_id = raw_instance_id if isinstance(raw_instance_id, int) else None

            raw_tags = parsed.get("tags")
            tags = _parse_tags(raw_tags if isinstance(raw_tags, list) else None)

            raw_page = parsed.get("page")
            page = max(int(raw_page) if isinstance(raw_page, int) else 1, 1)

            raw_limit = parsed.get("limit")
            limit = int(raw_limit) if isinstance(raw_limit, int) else 20
            limit = max(min(limit, 200), 1)

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
                    "limit": result.limit,
                },
                message="获取数据库台账成功",
            )

        return self.safe_call(
            _execute,
            module="databases_ledgers",
            action="fetch_ledger",
            public_error="获取数据库台账失败",
            context={
                "query_params": query_snapshot,
            },
        )


@ns.route("/ledgers/exports")
class DatabaseLedgersExportResource(BaseResource):
    """数据库台账导出资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK")
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_database_ledgers_export_query_parser)
    @api_permission_required("view")
    def get(self):
        """导出数据库台账."""
        query_snapshot = request.args.to_dict(flat=False)

        def _execute() -> Response:
            parsed = cast("dict[str, object]", _database_ledgers_export_query_parser.parse_args())
            search = str(parsed.get("search") or "").strip()
            db_type = str(parsed.get("db_type") or "all").strip() or "all"
            raw_instance_id = parsed.get("instance_id")
            instance_id = raw_instance_id if isinstance(raw_instance_id, int) else None

            raw_tags = parsed.get("tags")
            tags = _parse_tags(raw_tags if isinstance(raw_tags, list) else None)

            result = DatabaseLedgerExportService().export_database_ledger_csv(
                search=search,
                db_type=db_type,
                instance_id=instance_id,
                tags=tags,
            )
            return Response(
                result.content,
                mimetype=result.mimetype,
                headers={"Content-Disposition": f"attachment; filename={result.filename}"},
            )

        return self.safe_call(
            _execute,
            module="databases_ledgers",
            action="export_database_ledger",
            public_error="导出数据库台账失败",
            context={
                "query_params": query_snapshot,
            },
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
    @ns.expect(_databases_sizes_query_parser)
    @api_permission_required("view")
    def get(self):
        """获取实例数据库大小数据."""
        query_snapshot = request.args.to_dict(flat=False)

        def _execute():
            parsed = cast("dict[str, object]", _databases_sizes_query_parser.parse_args())

            if parsed.get("offset") is not None:
                raise ValidationError("分页参数已统一为 page/limit，不支持 offset")

            instance_id = parsed.get("instance_id")
            if not isinstance(instance_id, int) or instance_id <= 0:
                raise ValidationError("缺少 instance_id")

            InstanceDetailReadService().get_active_instance(instance_id)

            raw_start_date = parsed.get("start_date")
            start_date_raw = raw_start_date if isinstance(raw_start_date, str) else None
            raw_end_date = parsed.get("end_date")
            end_date_raw = raw_end_date if isinstance(raw_end_date, str) else None
            raw_database_name = parsed.get("database_name")
            database_name = raw_database_name if isinstance(raw_database_name, str) else None
            latest_only = bool(parsed.get("latest_only") or False)
            include_inactive = bool(parsed.get("include_inactive") or False)

            raw_page = parsed.get("page")
            page = max(int(raw_page) if isinstance(raw_page, int) else 1, 1)

            raw_limit = parsed.get("limit")
            limit = int(raw_limit) if isinstance(raw_limit, int) else 100
            if limit < 1:
                limit = 100
            offset = (page - 1) * limit

            options = InstanceDatabaseSizesQuery(
                instance_id=instance_id,
                database_name=database_name,
                start_date=_parse_optional_date(start_date_raw, "start_date"),
                end_date=_parse_optional_date(end_date_raw, "end_date"),
                include_inactive=include_inactive,
                limit=limit,
                offset=offset,
            )

            result = InstanceDatabaseSizesService().fetch_sizes(options, latest_only=latest_only)
            databases = marshal(result.databases, INSTANCE_DATABASE_SIZE_ENTRY_FIELDS)

            total = int(result.total or 0)
            resolved_limit = int(result.limit or limit)
            pages = (total + resolved_limit - 1) // resolved_limit if total else 0

            payload: dict[str, object] = {
                "total": total,
                "limit": resolved_limit,
                "page": page,
                "pages": pages,
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
            context={"query_params": query_snapshot},
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
    @ns.expect(_database_table_sizes_query_parser)
    @api_permission_required("view")
    def get(self, database_id: int):
        """获取指定数据库的表容量快照."""
        query_snapshot = request.args.to_dict(flat=False)

        def _execute():
            parsed = cast("dict[str, object]", _database_table_sizes_query_parser.parse_args())

            if parsed.get("offset") is not None:
                raise ValidationError("分页参数已统一为 page/limit，不支持 offset")

            record = InstanceDatabaseDetailReadService().get_by_id_or_error(database_id)

            InstanceDetailReadService().get_active_instance(record.instance_id)

            raw_schema_name = parsed.get("schema_name")
            schema_name = raw_schema_name if isinstance(raw_schema_name, str) else None
            raw_table_name = parsed.get("table_name")
            table_name = raw_table_name if isinstance(raw_table_name, str) else None

            raw_page = parsed.get("page")
            page = max(int(raw_page) if isinstance(raw_page, int) else 1, 1)

            raw_limit = parsed.get("limit")
            limit = int(raw_limit) if isinstance(raw_limit, int) else 200
            if limit > DATABASE_TABLE_SIZES_LIMIT_MAX:
                raise ValidationError(f"limit 最大为 {DATABASE_TABLE_SIZES_LIMIT_MAX}")
            if limit < 1:
                limit = 200
            offset = (page - 1) * limit

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

            total = int(result.total or 0)
            resolved_limit = int(result.limit or limit)
            pages = (total + resolved_limit - 1) // resolved_limit if total else 0

            payload: dict[str, object] = {
                "total": total,
                "limit": resolved_limit,
                "page": page,
                "pages": pages,
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
        api_permission_required("update"),
    ]

    @ns.response(200, "OK", DatabaseTableSizesSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_database_table_sizes_query_parser)
    @require_csrf
    def post(self, database_id: int):
        """手动采集并刷新表容量快照."""
        query_snapshot = request.args.to_dict(flat=False)

        def _execute():
            parsed = cast("dict[str, object]", _database_table_sizes_query_parser.parse_args())

            if parsed.get("offset") is not None:
                raise ValidationError("分页参数已统一为 page/limit，不支持 offset")

            raw_schema_name = parsed.get("schema_name")
            schema_name = raw_schema_name if isinstance(raw_schema_name, str) else None
            raw_table_name = parsed.get("table_name")
            table_name = raw_table_name if isinstance(raw_table_name, str) else None

            raw_page = parsed.get("page")
            page = max(int(raw_page) if isinstance(raw_page, int) else 1, 1)

            raw_limit = parsed.get("limit")
            limit = int(raw_limit) if isinstance(raw_limit, int) else 200
            if limit > DATABASE_TABLE_SIZES_LIMIT_MAX:
                raise ValidationError(f"limit 最大为 {DATABASE_TABLE_SIZES_LIMIT_MAX}")
            if limit < 1:
                limit = 200
            offset = (page - 1) * limit

            record = InstanceDatabaseDetailReadService().get_by_id_or_error(database_id)

            instance = InstanceDetailReadService().get_instance_by_id(record.instance_id)
            if instance is None:
                raise NotFoundError("实例不存在", extra={"instance_id": record.instance_id})

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

                total = int(result.total or 0)
                resolved_limit = int(result.limit or limit)
                pages = (total + resolved_limit - 1) // resolved_limit if total else 0

                payload: dict[str, object] = {
                    "total": total,
                    "limit": resolved_limit,
                    "page": page,
                    "pages": pages,
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
