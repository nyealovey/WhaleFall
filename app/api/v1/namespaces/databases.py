"""Databases namespace (Phase 2 核心域迁移 - Ledgers)."""

from __future__ import annotations

from typing import ClassVar

from flask import Response, request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

import app.services.database_sync as database_sync_module
from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import bool_with_default, new_parser
from app.api.v1.restx_models.databases import (
    DATABASE_OPTION_ITEM_FIELDS,
    DATABASES_OPTIONS_RESPONSE_FIELDS,
)
from app.api.v1.restx_models.instances import (
    INSTANCE_DATABASE_SIZE_ENTRY_FIELDS,
    INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS,
)
from app.core.constants import HttpStatus
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.databases_query import (
    DatabaseLedgersExportQuery,
    DatabaseLedgersQuery,
    DatabasesOptionsQuery,
    DatabasesSizesQuery,
    DatabaseTableSizesQuery,
)
from app.schemas.validation import validate_or_raise
from app.services.capacity.capacity_collection_actions_service import CapacityCollectionActionsService
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
from app.utils.structlog_config import log_info

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
DatabasesOptionsSuccessEnvelope = make_success_envelope_model(
    ns, "DatabasesOptionsSuccessEnvelope", DatabasesOptionsData
)

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

DatabaseLedgersSyncAllData = ns.model(
    "DatabaseLedgersSyncAllData",
    {
        "run_id": fields.String(
            required=True,
            description="任务运行 ID",
            example="a1b2c3d4-e5f6-7890-1234-567890abcdef",
        ),
    },
)
DatabaseLedgersSyncAllSuccessEnvelope = make_success_envelope_model(
    ns,
    "DatabaseLedgersSyncAllSuccessEnvelope",
    DatabaseLedgersSyncAllData,
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

_database_table_sizes_query_parser = new_parser()
_database_table_sizes_query_parser.add_argument("schema_name", type=str, location="args")
_database_table_sizes_query_parser.add_argument("table_name", type=str, location="args")
_database_table_sizes_query_parser.add_argument("page", type=int, default=1, location="args")
_database_table_sizes_query_parser.add_argument("limit", type=int, default=200, location="args")


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
            parsed = dict(_databases_options_query_parser.parse_args())
            query = validate_or_raise(DatabasesOptionsQuery, parsed)

            instance = InstanceDetailReadService().get_instance_by_id(query.instance_id)
            if instance is None:
                raise NotFoundError("实例不存在")

            options = query.to_filters(resolved_instance_id=int(instance.id))

            result = FilterOptionsService().get_common_databases_options(
                options,
            )
            raw_total_count = getattr(result, "total_count", 0)
            total_count = int(raw_total_count) if raw_total_count is not None else 0
            pages = (total_count + query.limit - 1) // query.limit if total_count else 0
            payload = marshal(
                {
                    "databases": getattr(result, "databases", []),
                    "total_count": total_count,
                    "page": query.page,
                    "pages": pages,
                    "limit": query.limit,
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
            parsed = dict(_database_ledgers_query_parser.parse_args())
            query = validate_or_raise(DatabaseLedgersQuery, parsed)

            result = DatabaseLedgerService().get_ledger(
                search=query.search,
                db_type=query.db_type,
                instance_id=query.instance_id,
                tags=query.tags,
                page=query.page,
                per_page=query.limit,
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
            parsed = dict(_database_ledgers_export_query_parser.parse_args())
            query = validate_or_raise(DatabaseLedgersExportQuery, parsed)

            result = DatabaseLedgerExportService().export_database_ledger_csv(
                search=query.search,
                db_type=query.db_type,
                instance_id=query.instance_id,
                tags=query.tags,
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


@ns.route("/ledgers/actions/sync-all")
class DatabaseLedgersSyncAllActionResource(BaseResource):
    """数据库台账同步动作资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("update")]

    @ns.response(200, "OK", DatabaseLedgersSyncAllSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """触发数据库台账同步(容量同步)."""
        created_by = getattr(current_user, "id", None)
        actions_service = CapacityCollectionActionsService()
        prepared = None

        def _execute():
            nonlocal prepared
            prepared = actions_service.prepare_background_collection(created_by=created_by)
            return self.success(
                data={"run_id": prepared.run_id},
                message="数据库台账同步任务已在后台启动,请稍后在运行中心查看进度.",
            )

        response = self.safe_call(
            _execute,
            module="databases_ledgers",
            action="sync_all_databases",
            public_error="触发数据库台账同步失败,请稍后重试",
            context={"scope": "all_instances"},
        )

        if prepared is not None:
            launch_result = actions_service.launch_background_collection(created_by=created_by, prepared=prepared)
            log_info(
                "数据库台账同步任务已在后台启动",
                module="databases_ledgers",
                run_id=launch_result.run_id,
                thread_name=launch_result.thread_name,
                active_instance_count=launch_result.active_instance_count,
            )
        return response


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
            parsed = dict(_databases_sizes_query_parser.parse_args())
            query = validate_or_raise(DatabasesSizesQuery, parsed)

            InstanceDetailReadService().get_active_instance(query.instance_id)

            options = query.to_options()
            result = InstanceDatabaseSizesService().fetch_sizes(options, latest_only=query.latest_only)
            databases = marshal(result.databases, INSTANCE_DATABASE_SIZE_ENTRY_FIELDS)

            total = int(result.total) if result.total is not None else 0
            resolved_limit = int(result.limit) if isinstance(result.limit, int) and result.limit > 0 else query.limit
            pages = (total + resolved_limit - 1) // resolved_limit if total else 0

            payload: dict[str, object] = {
                "total": total,
                "limit": resolved_limit,
                "page": query.page,
                "pages": pages,
                "databases": databases,
            }

            if query.latest_only:
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
            parsed = dict(_database_table_sizes_query_parser.parse_args())
            query = validate_or_raise(DatabaseTableSizesQuery, parsed)

            record = InstanceDatabaseDetailReadService().get_by_id_or_error(database_id)

            InstanceDetailReadService().get_active_instance(record.instance_id)

            options = query.to_options(instance_id=record.instance_id, database_name=record.database_name)

            result = InstanceDatabaseTableSizesService().fetch_snapshot(options)
            tables = marshal(result.tables, INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS, skip_none=True)

            total = int(result.total) if result.total is not None else 0
            resolved_limit = int(result.limit) if isinstance(result.limit, int) and result.limit > 0 else query.limit
            pages = (total + resolved_limit - 1) // resolved_limit if total else 0

            payload: dict[str, object] = {
                "total": total,
                "limit": resolved_limit,
                "page": query.page,
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
            parsed = dict(_database_table_sizes_query_parser.parse_args())
            query = validate_or_raise(DatabaseTableSizesQuery, parsed)

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
                    error_message = str(exc).strip()
                    if not error_message:
                        error_message = "表容量采集失败"
                    return self.error_message(
                        error_message,
                        status=HttpStatus.CONFLICT,
                        message_key="SYNC_DATA_ERROR",
                        extra={"instance_id": instance.id, "database_name": record.database_name},
                    )

                options = query.to_options(instance_id=instance.id, database_name=record.database_name)
                result = InstanceDatabaseTableSizesService().fetch_snapshot(options)
                tables = marshal(result.tables, INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS, skip_none=True)

                total = int(result.total) if result.total is not None else 0
                resolved_limit = (
                    int(result.limit) if isinstance(result.limit, int) and result.limit > 0 else query.limit
                )
                pages = (total + resolved_limit - 1) // resolved_limit if total else 0

                payload: dict[str, object] = {
                    "total": total,
                    "limit": resolved_limit,
                    "page": query.page,
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
