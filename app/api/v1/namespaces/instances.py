"""Instances namespace (Phase 2 核心域迁移)."""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from datetime import date
from typing import Any, ClassVar, Literal, cast

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

import app.services.aggregation as aggregation_module
import app.services.database_sync as database_sync_module
from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.restx_models.instances import (
    INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS,
    INSTANCE_ACCOUNT_CHANGE_HISTORY_RESPONSE_FIELDS,
    INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS,
    INSTANCE_ACCOUNT_INFO_FIELDS,
    INSTANCE_ACCOUNT_LIST_ITEM_FIELDS,
    INSTANCE_ACCOUNT_PERMISSIONS_FIELDS,
    INSTANCE_ACCOUNT_PERMISSIONS_RESPONSE_FIELDS,
    INSTANCE_ACCOUNT_SUMMARY_FIELDS,
    INSTANCE_DATABASE_SIZE_ENTRY_FIELDS,
    INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS,
    INSTANCE_LIST_ITEM_FIELDS,
    INSTANCE_STATISTICS_FIELDS,
    INSTANCE_TAG_FIELDS,
)
from app.constants import HttpStatus
from app.constants.import_templates import INSTANCE_IMPORT_REQUIRED_FIELDS, INSTANCE_IMPORT_TEMPLATE_HEADERS
from app.errors import NotFoundError, ValidationError
from app.models.instance import Instance
from app.services.instances.batch_service import InstanceBatchCreationService, InstanceBatchDeletionService
from app.services.instances.instance_accounts_service import InstanceAccountsService
from app.services.instances.instance_database_sizes_service import InstanceDatabaseSizesService
from app.services.instances.instance_database_table_sizes_service import InstanceDatabaseTableSizesService
from app.services.instances.instance_detail_read_service import InstanceDetailReadService
from app.services.instances.instance_list_service import InstanceListService
from app.services.instances.instance_statistics_read_service import InstanceStatisticsReadService
from app.services.instances.instance_write_service import InstanceWriteService
from app.types.instance_accounts import InstanceAccountListFilters
from app.types.instance_database_sizes import InstanceDatabaseSizesQuery
from app.types.instance_database_table_sizes import InstanceDatabaseTableSizesQuery
from app.types.instances import InstanceListFilters
from app.utils.decorators import require_csrf
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.structlog_config import log_warning
from app.utils.time_utils import time_utils

ns = Namespace("instances", description="实例管理")

ErrorEnvelope = get_error_envelope_model(ns)

InstanceWritePayload = ns.model(
    "InstanceWritePayload",
    {
        "name": fields.String(required=True, description="实例名称", example="prod-mysql-1"),
        "db_type": fields.String(required=True, description="数据库类型", example="mysql"),
        "host": fields.String(required=True, description="主机", example="127.0.0.1"),
        "port": fields.Integer(required=True, description="端口", example=3306),
        "database_name": fields.String(required=False, description="默认数据库名(可选)", example="app_db"),
        "credential_id": fields.Integer(required=False, description="凭据 ID(可选)", example=1),
        "description": fields.String(required=False, description="描述(可选)", example="生产环境实例"),
        "is_active": fields.Boolean(required=False, description="是否启用(可选)", example=True),
        "tag_names": fields.List(
            fields.String,
            required=False,
            description="标签代码列表(可选)",
            example=["prod", "mysql"],
        ),
    },
)

InstanceTagModel = ns.model("InstanceTag", INSTANCE_TAG_FIELDS)

InstanceListItemModel = ns.model(
    "InstanceListItem",
    {
        **INSTANCE_LIST_ITEM_FIELDS,
        "tags": fields.List(fields.Nested(InstanceTagModel)),
    },
)

InstancesListData = ns.model(
    "InstancesListData",
    {
        "items": fields.List(fields.Nested(InstanceListItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
    },
)

InstancesListSuccessEnvelope = make_success_envelope_model(ns, "InstancesListSuccessEnvelope", InstancesListData)

InstanceDetailData = ns.model(
    "InstanceDetailData",
    {
        "instance": fields.Raw(description="实例详情"),
    },
)

InstanceDetailSuccessEnvelope = make_success_envelope_model(ns, "InstanceDetailSuccessEnvelope", InstanceDetailData)

InstanceDeleteData = ns.model(
    "InstanceDeleteData",
    {
        "instance_id": fields.Integer(),
        "deleted_at": fields.String(required=False, description="ISO8601 时间戳"),
        "deletion_mode": fields.String(),
    },
)

InstanceDeleteSuccessEnvelope = make_success_envelope_model(ns, "InstanceDeleteSuccessEnvelope", InstanceDeleteData)

InstanceAccountSummaryModel = ns.model("InstanceAccountSummary", INSTANCE_ACCOUNT_SUMMARY_FIELDS)

InstanceAccountListItemModel = ns.model("InstanceAccountListItem", INSTANCE_ACCOUNT_LIST_ITEM_FIELDS)

InstanceAccountsListData = ns.model(
    "InstanceAccountsListData",
    {
        "items": fields.List(fields.Nested(InstanceAccountListItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
        "summary": fields.Nested(InstanceAccountSummaryModel),
    },
)

InstanceAccountsListSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceAccountsListSuccessEnvelope",
    InstanceAccountsListData,
)

InstanceAccountInfoModel = ns.model("InstanceAccountInfo", INSTANCE_ACCOUNT_INFO_FIELDS)

InstanceAccountPermissionsModel = ns.model("InstanceAccountPermissions", INSTANCE_ACCOUNT_PERMISSIONS_FIELDS)

InstanceAccountPermissionsData = ns.model(
    "InstanceAccountPermissionsData",
    {
        "permissions": fields.Nested(InstanceAccountPermissionsModel),
        "account": fields.Nested(InstanceAccountInfoModel),
    },
)

InstanceAccountPermissionsSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceAccountPermissionsSuccessEnvelope",
    InstanceAccountPermissionsData,
)

InstanceAccountChangeLogModel = ns.model("InstanceAccountChangeLog", INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS)

InstanceAccountChangeHistoryAccountModel = ns.model(
    "InstanceAccountChangeHistoryAccount",
    INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS,
)

InstanceAccountChangeHistoryData = ns.model(
    "InstanceAccountChangeHistoryData",
    {
        "account": fields.Nested(InstanceAccountChangeHistoryAccountModel),
        "history": fields.List(fields.Nested(InstanceAccountChangeLogModel)),
    },
)

InstanceAccountChangeHistorySuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceAccountChangeHistorySuccessEnvelope",
    InstanceAccountChangeHistoryData,
)

InstanceDatabaseSizeEntryModel = ns.model("InstanceDatabaseSizeEntry", INSTANCE_DATABASE_SIZE_ENTRY_FIELDS)

InstanceDatabaseSizesData = ns.model(
    "InstanceDatabaseSizesData",
    {
        "total": fields.Integer(),
        "limit": fields.Integer(),
        "offset": fields.Integer(),
        "active_count": fields.Integer(required=False),
        "filtered_count": fields.Integer(required=False),
        "total_size_mb": fields.Raw(required=False),
        "databases": fields.List(fields.Nested(InstanceDatabaseSizeEntryModel)),
    },
)

InstanceDatabaseSizesSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceDatabaseSizesSuccessEnvelope",
    InstanceDatabaseSizesData,
)

InstanceDatabaseTableSizeEntryModel = ns.model(
    "InstanceDatabaseTableSizeEntry",
    INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS,
)

InstanceDatabaseTableSizesData = ns.model(
    "InstanceDatabaseTableSizesData",
    {
        "total": fields.Integer(),
        "limit": fields.Integer(),
        "offset": fields.Integer(),
        "collected_at": fields.String(required=False),
        "tables": fields.List(fields.Nested(InstanceDatabaseTableSizeEntryModel)),
        "saved_count": fields.Integer(required=False),
        "deleted_count": fields.Integer(required=False),
        "elapsed_ms": fields.Integer(required=False),
    },
)

InstanceDatabaseTableSizesSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceDatabaseTableSizesSuccessEnvelope",
    InstanceDatabaseTableSizesData,
)

InstanceSyncCapacityResultData = ns.model(
    "InstanceSyncCapacityResultData",
    {
        "result": fields.Raw(required=True),
    },
)

InstanceSyncCapacitySuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceSyncCapacitySuccessEnvelope",
    InstanceSyncCapacityResultData,
)

InstancesBatchCreateData = ns.model(
    "InstancesBatchCreateData",
    {
        "created_count": fields.Integer(required=True),
        "errors": fields.List(fields.String, required=False),
        "duplicate_names": fields.List(fields.String, required=False),
        "skipped_existing_names": fields.List(fields.String, required=False),
    },
)

InstancesBatchCreateSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstancesBatchCreateSuccessEnvelope",
    InstancesBatchCreateData,
)

InstancesBatchDeleteData = ns.model(
    "InstancesBatchDeleteData",
    {
        "deleted_count": fields.Integer(required=True),
        "instance_ids": fields.List(fields.Integer, required=False),
        "missing_instance_ids": fields.List(fields.Integer, required=False),
        "deletion_mode": fields.String(required=False),
    },
)

InstancesBatchDeleteSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstancesBatchDeleteSuccessEnvelope",
    InstancesBatchDeleteData,
)

InstanceStatisticsDbTypeStatModel = ns.model(
    "InstanceStatisticsDbTypeStat",
    {
        "db_type": fields.String(),
        "count": fields.Integer(),
    },
)

InstanceStatisticsPortStatModel = ns.model(
    "InstanceStatisticsPortStat",
    {
        "port": fields.Integer(),
        "count": fields.Integer(),
    },
)

InstanceStatisticsVersionStatModel = ns.model(
    "InstanceStatisticsVersionStat",
    {
        "db_type": fields.String(),
        "version": fields.String(),
        "count": fields.Integer(),
    },
)

InstanceStatisticsData = ns.model(
    "InstanceStatisticsData",
    {
        "total_instances": fields.Integer(),
        "active_instances": fields.Integer(),
        "normal_instances": fields.Integer(),
        "disabled_instances": fields.Integer(),
        "deleted_instances": fields.Integer(),
        "inactive_instances": fields.Integer(),
        "db_types_count": fields.Integer(),
        "db_type_stats": fields.List(fields.Nested(InstanceStatisticsDbTypeStatModel)),
        "port_stats": fields.List(fields.Nested(InstanceStatisticsPortStatModel)),
        "version_stats": fields.List(fields.Nested(InstanceStatisticsVersionStatModel)),
    },
)

InstanceStatisticsSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstanceStatisticsSuccessEnvelope",
    InstanceStatisticsData,
)

EXPECTED_INSTANCE_IMPORT_FIELDS = {header.lower() for header in INSTANCE_IMPORT_TEMPLATE_HEADERS}


def _parse_instance_filters() -> InstanceListFilters:
    args = request.args
    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=20,
        minimum=1,
        maximum=100,
    )
    sort_field = (args.get("sort", "id", type=str) or "id").lower()
    sort_order = (args.get("order", "desc", type=str) or "desc").lower()
    if sort_order not in {"asc", "desc"}:
        sort_order = "desc"

    search = (args.get("search") or "").strip()
    db_type = (args.get("db_type") or "").strip()
    status_value = (args.get("status") or "").strip()
    tags = [tag.strip() for tag in args.getlist("tags") if tag and tag.strip()]
    include_deleted_raw = (args.get("include_deleted") or "").strip().lower()
    include_deleted = include_deleted_raw in {"true", "1", "on", "yes"}

    return InstanceListFilters(
        page=page,
        limit=limit,
        sort_field=sort_field,
        sort_order=sort_order,
        search=search,
        db_type=db_type,
        status=status_value,
        tags=tags,
        include_deleted=include_deleted,
    )


def _parse_payload() -> Any:
    if request.is_json:
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}
    return request.form


def _normalize_import_header(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().strip("\ufeff").lower()


def _validate_import_csv_headers(fieldnames: list[str] | None) -> None:
    normalized_headers = {_normalize_import_header(name) for name in (fieldnames or []) if name is not None}
    missing = INSTANCE_IMPORT_REQUIRED_FIELDS - normalized_headers
    if missing:
        missing_label = ", ".join(sorted(missing))
        raise ValidationError(f"CSV文件缺少必填列: {missing_label}")


def _normalize_import_csv_row(row: Mapping[str, object] | None) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for raw_key, raw_value in (row or {}).items():
        field_name = _normalize_import_header(str(raw_key) if raw_key is not None else None)
        if field_name not in EXPECTED_INSTANCE_IMPORT_FIELDS:
            continue

        if isinstance(raw_value, str):
            value = raw_value.strip()
            if not value:
                continue
        else:
            value = raw_value

        if field_name == "db_type" and isinstance(value, str):
            normalized[field_name] = value.lower()
        else:
            normalized[field_name] = value

    return normalized


def _parse_import_csv(file_bytes: bytes) -> list[dict[str, object]]:
    try:
        stream = io.StringIO(file_bytes.decode("utf-8-sig"), newline=None)
        csv_input = csv.DictReader(stream)
        csv_fieldnames = list(csv_input.fieldnames) if csv_input.fieldnames is not None else None
        _validate_import_csv_headers(csv_fieldnames)
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(f"CSV文件处理失败: {exc}") from exc

    instances_data = [normalized_row for row in csv_input if (normalized_row := _normalize_import_csv_row(row))]
    if not instances_data:
        raise ValidationError("CSV文件为空或未包含有效数据")
    return instances_data


def _build_instance_statistics() -> dict[str, object]:
    result = InstanceStatisticsReadService().build_statistics()
    return cast(dict[str, object], marshal(result, INSTANCE_STATISTICS_FIELDS))


def _parse_account_list_filters(instance_id: int) -> InstanceAccountListFilters:
    args = request.args

    include_deleted_raw = (args.get("include_deleted") or "false").strip().lower()
    include_deleted = include_deleted_raw in {"true", "1", "on", "yes"}

    include_permissions_raw = (args.get("include_permissions") or "false").strip().lower()
    include_permissions = include_permissions_raw in {"true", "1", "on", "yes"}

    search = (args.get("search") or "").strip()

    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=20,
        minimum=1,
        maximum=200,
    )

    sort_field = (args.get("sort") or "username").strip().lower()
    sort_order = (args.get("order") or "asc").strip().lower()
    if sort_order not in {"asc", "desc"}:
        sort_order = "asc"

    return InstanceAccountListFilters(
        instance_id=instance_id,
        include_deleted=include_deleted,
        include_permissions=include_permissions,
        search=search,
        page=page,
        limit=limit,
        sort_field=sort_field,
        sort_order=sort_order,
    )


@ns.route("")
class InstancesResource(BaseResource):
    """实例列表资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstancesListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
        """获取实例列表."""

        def _execute():
            filters = _parse_instance_filters()
            result = InstanceListService().list_instances(filters)
            items = marshal(result.items, INSTANCE_LIST_ITEM_FIELDS)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                    "limit": result.limit,
                },
                message="获取实例列表成功",
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="list_instances",
            public_error="获取实例列表失败",
            context={
                "search": request.args.get("search"),
                "status": request.args.get("status"),
                "include_deleted": request.args.get("include_deleted"),
            },
        )

    @ns.expect(InstanceWritePayload, validate=False)
    @ns.response(201, "Created", InstanceDetailSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("create")
    @require_csrf
    def post(self):
        """创建实例."""
        payload = _parse_payload()
        operator_id = getattr(current_user, "id", None)
        credential_context_raw = payload.get("credential_id") if hasattr(payload, "get") else None
        db_type_context_raw = payload.get("db_type") if hasattr(payload, "get") else None

        credential_context: int | None
        if isinstance(credential_context_raw, (str, int)):
            try:
                credential_context = int(credential_context_raw)
            except (TypeError, ValueError):
                credential_context = None
        else:
            credential_context = None

        db_type_context = db_type_context_raw if isinstance(db_type_context_raw, str) else None

        def _execute():
            instance = InstanceWriteService().create(payload, operator_id=operator_id)
            return self.success(
                data={"instance": instance.to_dict()},
                message="实例创建成功",
                status=HttpStatus.CREATED,
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="create_instance",
            public_error="创建实例失败",
            context={"credential_id": credential_context, "db_type": db_type_context},
        )


@ns.route("/<int:instance_id>")
class InstanceDetailResource(BaseResource):
    """实例详情资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstanceDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int):
        """获取实例详情."""

        def _execute():
            instance = InstanceDetailReadService().get_active_instance(instance_id)
            return self.success(
                data={"instance": instance.to_dict()},
                message="获取实例详情成功",
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="get_instance_detail",
            public_error="获取实例详情失败",
            context={"instance_id": instance_id},
        )

    @ns.expect(InstanceWritePayload, validate=False)
    @ns.response(200, "OK", InstanceDetailSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("update")
    @require_csrf
    def put(self, instance_id: int):
        """更新实例."""
        payload = _parse_payload()
        operator_id = getattr(current_user, "id", None)

        def _execute():
            instance = InstanceWriteService().update(instance_id, payload, operator_id=operator_id)
            return self.success(
                data={"instance": instance.to_dict()},
                message="实例更新成功",
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="update_instance_detail",
            public_error="更新实例失败",
            context={"instance_id": instance_id},
        )


@ns.route("/<int:instance_id>/actions/sync-capacity")
class InstanceSyncCapacityActionResource(BaseResource):
    """实例容量同步动作资源."""

    method_decorators: ClassVar[list] = [
        api_login_required,
        api_permission_required("instance_management.instance_list.sync_capacity"),
    ]

    @ns.response(200, "OK", InstanceSyncCapacitySuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self, instance_id: int):
        """执行实例容量同步."""

        def _execute():
            instance = Instance.query.filter_by(id=instance_id).first()
            if instance is None:
                raise NotFoundError("实例不存在")

            coordinator = database_sync_module.CapacitySyncCoordinator(instance)
            if not coordinator.connect():
                return self.error_message(
                    f"无法连接到实例 {instance.name}",
                    status=HttpStatus.CONFLICT,
                    message_key="DATABASE_CONNECTION_ERROR",
                    extra={"instance_id": instance.id},
                )

            try:
                inventory_result = coordinator.synchronize_inventory()
                active_databases = set(inventory_result.get("active_databases", []))

                if not active_databases:
                    normalized = {
                        "status": "completed",
                        "databases": [],
                        "database_count": 0,
                        "total_size_mb": 0,
                        "saved_count": 0,
                        "instance_stat_updated": False,
                        "inventory": inventory_result,
                        "message": "未发现活跃数据库,已仅同步数据库列表",
                    }
                    return self.success(
                        data={"result": normalized},
                        message=f"实例 {instance.name} 的容量同步任务已成功完成",
                    )

                try:
                    databases_data = coordinator.collect_capacity(list(active_databases))
                except (RuntimeError, ConnectionError, TimeoutError, OSError):
                    return self.error_message(
                        "容量采集失败",
                        status=HttpStatus.CONFLICT,
                        message_key="SYNC_DATA_ERROR",
                        extra={"instance_id": instance.id},
                    )
                if not databases_data:
                    return self.error_message(
                        "未采集到任何数据库大小数据",
                        status=HttpStatus.CONFLICT,
                        message_key="SYNC_DATA_ERROR",
                        extra={"instance_id": instance.id},
                    )

                database_count = len(databases_data)
                total_size_mb = sum(int(db.get("size_mb", 0) or 0) for db in databases_data)
                saved_count = coordinator.save_database_stats(databases_data)
                instance_stat_updated = coordinator.update_instance_total_size()

                try:
                    aggregation_service = aggregation_module.AggregationService()
                    aggregation_service.calculate_daily_database_aggregations_for_instance(instance.id)
                    aggregation_service.calculate_daily_aggregations_for_instance(instance.id)
                except Exception as exc:
                    log_warning(
                        "容量同步后触发聚合失败",
                        module="databases_capacity",
                        exception=exc,
                        instance_id=instance.id,
                    )

                normalized = {
                    "status": "completed",
                    "databases": databases_data,
                    "database_count": database_count,
                    "total_size_mb": total_size_mb,
                    "saved_count": saved_count,
                    "instance_stat_updated": instance_stat_updated,
                    "inventory": inventory_result,
                    "message": f"成功采集并保存 {database_count} 个数据库的容量信息",
                }
                return self.success(
                    data={"result": normalized},
                    message=f"实例 {instance.name} 的容量同步任务已成功完成",
                )
            finally:
                coordinator.disconnect()

        return self.safe_call(
            _execute,
            module="databases_capacity",
            action="sync_instance_capacity",
            public_error="同步实例容量失败",
            context={"instance_id": instance_id},
        )


@ns.route("/<int:instance_id>/delete")
class InstanceDeleteResource(BaseResource):
    """实例删除资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstanceDeleteSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def post(self, instance_id: int):
        """将实例移入回收站."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            outcome = InstanceWriteService().soft_delete(instance_id, operator_id=operator_id)
            instance = outcome.instance
            return self.success(
                data={
                    "instance_id": instance.id,
                    "deleted_at": instance.deleted_at.isoformat() if instance.deleted_at else None,
                    "deletion_mode": outcome.deletion_mode,
                },
                message="实例已移入回收站",
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="delete_instance",
            public_error="移入回收站失败,请重试",
            context={"instance_id": instance_id},
        )


@ns.route("/<int:instance_id>/restore")
class InstanceRestoreResource(BaseResource):
    """实例恢复资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstanceDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("update")
    @require_csrf
    def post(self, instance_id: int):
        """恢复实例."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            outcome = InstanceWriteService().restore(instance_id, operator_id=operator_id)
            instance = outcome.instance
            if not outcome.restored:
                return self.success(
                    data={"instance": instance.to_dict()},
                    message="实例未删除，无需恢复",
                )
            return self.success(
                data={"instance": instance.to_dict()},
                message="实例恢复成功",
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="restore_instance",
            public_error="恢复实例失败,请重试",
            context={"instance_id": instance_id},
        )


@ns.route("/<int:instance_id>/accounts")
class InstanceAccountsResource(BaseResource):
    """实例账户列表资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstanceAccountsListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int):
        """获取实例账户列表."""
        filters = _parse_account_list_filters(instance_id)

        def _execute():
            result = InstanceAccountsService().list_accounts(filters)
            items = marshal(result.items, INSTANCE_ACCOUNT_LIST_ITEM_FIELDS, skip_none=True)
            summary = marshal(result.summary, INSTANCE_ACCOUNT_SUMMARY_FIELDS)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                    "limit": result.limit,
                    "summary": summary,
                },
                message="获取实例账户数据成功",
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="list_instance_accounts",
            public_error="获取实例账户数据失败",
            context={
                "instance_id": instance_id,
                "include_deleted": filters.include_deleted,
                "include_permissions": filters.include_permissions,
                "search": filters.search,
                "page": filters.page,
                "limit": filters.limit,
                "sort": filters.sort_field,
                "order": filters.sort_order,
            },
        )


@ns.route("/<int:instance_id>/accounts/<int:account_id>/permissions")
class InstanceAccountPermissionsResource(BaseResource):
    """实例账户权限资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstanceAccountPermissionsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int, account_id: int):
        """获取实例账户权限."""

        def _execute():
            result = InstanceAccountsService().get_account_permissions(instance_id, account_id)
            payload = marshal(result, INSTANCE_ACCOUNT_PERMISSIONS_RESPONSE_FIELDS, skip_none=True)
            return self.success(
                data=payload,
                message="获取账户权限成功",
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="get_account_permissions",
            public_error="获取账户权限失败",
            context={"instance_id": instance_id, "account_id": account_id},
        )


@ns.route("/<int:instance_id>/accounts/<int:account_id>/change-history")
class InstanceAccountChangeHistoryResource(BaseResource):
    """实例账户变更历史资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstanceAccountChangeHistorySuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int, account_id: int):
        """获取账户变更历史."""

        def _execute():
            result = InstanceAccountsService().get_change_history(instance_id, account_id)
            payload = marshal(result, INSTANCE_ACCOUNT_CHANGE_HISTORY_RESPONSE_FIELDS)
            return self.success(
                data=payload,
                message="获取账户变更历史成功",
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="get_account_change_history",
            public_error="获取变更历史失败",
            context={"instance_id": instance_id, "account_id": account_id},
        )


@ns.route("/<int:instance_id>/databases/sizes")
class InstanceDatabaseSizesResource(BaseResource):
    """实例数据库大小资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstanceDatabaseSizesSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int):
        """获取实例数据库大小数据."""
        query_snapshot = request.args.to_dict(flat=False)

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
            action="get_instance_database_sizes",
            public_error="获取数据库大小历史数据失败",
            expected_exceptions=(ValidationError,),
            context={"instance_id": instance_id, "query_params": query_snapshot},
        )


@ns.route("/<int:instance_id>/databases/<string:database_name>/tables/sizes")
class InstanceDatabaseTableSizesSnapshotResource(BaseResource):
    """实例数据库表容量快照资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstanceDatabaseTableSizesSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int, database_name: str):
        """获取实例指定数据库的表容量快照."""
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
            InstanceDetailReadService().get_active_instance(instance_id)

            schema_name = request.args.get("schema_name")
            table_name = request.args.get("table_name")

            limit = _parse_int(request.args.get("limit"), field="limit", default=200)
            if limit > 2000:
                raise ValidationError("limit 最大为 2000")
            offset = _parse_int(request.args.get("offset"), field="offset", default=0)

            options = InstanceDatabaseTableSizesQuery(
                instance_id=instance_id,
                database_name=database_name,
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
            module="instances",
            action="get_instance_database_table_sizes_snapshot",
            public_error="获取表容量快照失败",
            expected_exceptions=(ValidationError,),
            context={
                "instance_id": instance_id,
                "database_name": database_name,
                "query_params": query_snapshot,
            },
        )


@ns.route("/<int:instance_id>/databases/<string:database_name>/tables/sizes/actions/refresh")
class InstanceDatabaseTableSizesRefreshResource(BaseResource):
    """实例数据库表容量刷新动作资源."""

    method_decorators: ClassVar[list] = [
        api_login_required,
        api_permission_required("instance_management.instance_list.sync_capacity"),
    ]

    @ns.response(200, "OK", InstanceDatabaseTableSizesSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self, instance_id: int, database_name: str):
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
            instance = Instance.query.filter_by(id=instance_id).first()
            if instance is None:
                raise NotFoundError("实例不存在")

            coordinator = database_sync_module.TableSizeCoordinator(instance)
            if not coordinator.connect(database_name):
                return self.error_message(
                    f"无法连接到实例 {instance.name}",
                    status=HttpStatus.CONFLICT,
                    message_key="DATABASE_CONNECTION_ERROR",
                    extra={"instance_id": instance.id, "database_name": database_name},
                )

            try:
                try:
                    outcome = coordinator.refresh_snapshot(database_name)
                except (ValueError, RuntimeError, ConnectionError, TimeoutError, OSError) as exc:
                    return self.error_message(
                        str(exc) or "表容量采集失败",
                        status=HttpStatus.CONFLICT,
                        message_key="SYNC_DATA_ERROR",
                        extra={"instance_id": instance.id, "database_name": database_name},
                    )

                schema_name = request.args.get("schema_name")
                table_name = request.args.get("table_name")
                limit = _parse_int(request.args.get("limit"), field="limit", default=200)
                if limit > 2000:
                    raise ValidationError("limit 最大为 2000")
                offset = _parse_int(request.args.get("offset"), field="offset", default=0)

                options = InstanceDatabaseTableSizesQuery(
                    instance_id=instance.id,
                    database_name=database_name,
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
            module="instances",
            action="refresh_instance_database_table_sizes",
            public_error="刷新表容量快照失败",
            expected_exceptions=(ValidationError,),
            context={
                "instance_id": instance_id,
                "database_name": database_name,
                "query_params": query_snapshot,
            },
        )


@ns.route("/batch-create")
class InstancesBatchCreateResource(BaseResource):
    """实例批量创建资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstancesBatchCreateSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("create")
    @require_csrf
    def post(self):
        """批量创建实例."""
        uploaded_file = request.files.get("file")
        operator_id = getattr(current_user, "id", None)

        def _execute():
            if not uploaded_file or not uploaded_file.filename or not uploaded_file.filename.lower().endswith(".csv"):
                raise ValidationError("请上传CSV格式文件")

            file_bytes = uploaded_file.stream.read()
            instances_data = _parse_import_csv(file_bytes)
            result = InstanceBatchCreationService().create_instances(instances_data, operator_id=operator_id)
            message = result.pop("message", f"成功创建 {result.get('created_count', 0)} 个实例")
            return self.success(data=result, message=message)

        return self.safe_call(
            _execute,
            module="instances_batch",
            action="create_instances_batch",
            public_error="批量创建实例失败",
            expected_exceptions=(ValidationError,),
            context={"filename": getattr(uploaded_file, "filename", None)},
        )


BatchDeletePayload = ns.model(
    "BatchDeletePayload",
    {
        "instance_ids": fields.List(fields.Integer, required=True),
        "deletion_mode": fields.String(required=False, description="soft/hard"),
    },
)


@ns.route("/batch-delete")
class InstancesBatchDeleteResource(BaseResource):
    """实例批量删除资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.expect(BatchDeletePayload, validate=False)
    @ns.response(200, "OK", InstancesBatchDeleteSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def post(self):
        """批量删除实例."""
        payload = request.get_json(silent=True) or {}
        operator_id = getattr(current_user, "id", None)

        def _execute():
            instance_ids = payload.get("instance_ids", [])
            deletion_mode_raw = payload.get("deletion_mode")
            deletion_mode: Literal["soft", "hard"] = "soft"
            if isinstance(deletion_mode_raw, str) and deletion_mode_raw in {"soft", "hard"}:
                deletion_mode = cast(Literal["soft", "hard"], deletion_mode_raw)

            result = InstanceBatchDeletionService().delete_instances(
                instance_ids,
                operator_id=operator_id,
                deletion_mode=deletion_mode,
            )
            deleted_count = int(result.get("deleted_count", 0) or 0)
            message = (
                f"成功移入回收站 {deleted_count} 个实例"
                if result.get("deletion_mode") == "soft"
                else f"成功删除 {deleted_count} 个实例"
            )
            return self.success(data=result, message=message)

        return self.safe_call(
            _execute,
            module="instances_batch",
            action="delete_instances_batch",
            public_error="批量删除实例失败",
            expected_exceptions=(ValidationError,),
            context={"count": len(payload.get("instance_ids", []) or [])},
        )


@ns.route("/statistics")
class InstancesStatisticsResource(BaseResource):
    """实例统计资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstanceStatisticsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
        """获取实例统计."""

        def _execute():
            return self.success(
                data=_build_instance_statistics(),
                message="获取实例统计信息成功",
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="get_instance_statistics",
            public_error="获取实例统计信息失败",
        )
