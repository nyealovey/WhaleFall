"""Instances namespace (Phase 2 核心域迁移)."""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from typing import Any, ClassVar, cast

from flask import Response, request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import bool_with_default, new_parser
from app.api.v1.restx_models.instances import (
    INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS,
    INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS,
    INSTANCE_ACCOUNT_INFO_FIELDS,
    INSTANCE_ACCOUNT_LIST_ITEM_FIELDS,
    INSTANCE_ACCOUNT_PERMISSIONS_FIELDS,
    INSTANCE_ACCOUNT_SUMMARY_FIELDS,
    INSTANCE_DATABASE_SIZE_ENTRY_FIELDS,
    INSTANCE_DATABASE_TABLE_SIZE_ENTRY_FIELDS,
    INSTANCE_LIST_ITEM_FIELDS,
    INSTANCE_OPTION_ITEM_FIELDS,
    INSTANCE_STATISTICS_FIELDS,
    INSTANCE_TAG_FIELDS,
    INSTANCES_OPTIONS_RESPONSE_FIELDS,
)
from app.core.constants import HttpHeaders, HttpStatus
from app.core.constants.import_templates import (
    INSTANCE_IMPORT_REQUIRED_FIELDS,
    INSTANCE_IMPORT_TEMPLATE_HEADERS,
)
from app.core.exceptions import ValidationError
from app.core.types.instances import InstanceListFilters
from app.services.capacity.instance_capacity_sync_actions_service import InstanceCapacitySyncActionsService
from app.services.common.filter_options_service import FilterOptionsService
from app.services.files.instances_export_service import InstancesExportService
from app.services.files.instances_import_template_service import InstancesImportTemplateService
from app.services.instances.batch_service import InstanceBatchCreationService, InstanceBatchDeletionService
from app.services.instances.instance_detail_read_service import InstanceDetailReadService
from app.services.instances.instance_list_service import InstanceListService
from app.services.instances.instance_statistics_read_service import InstanceStatisticsReadService
from app.services.instances.instance_write_service import InstanceWriteService
from app.utils.decorators import require_csrf

ns = Namespace("instances", description="实例管理")

ErrorEnvelope = get_error_envelope_model(ns)
_instances_export_service = InstancesExportService()

InstanceOptionItemModel = ns.model("InstanceOptionItem", INSTANCE_OPTION_ITEM_FIELDS)
InstancesOptionsData = ns.model(
    "InstancesOptionsData",
    {
        "instances": fields.List(fields.Nested(InstanceOptionItemModel)),
    },
)
InstancesOptionsSuccessEnvelope = make_success_envelope_model(ns, "InstancesOptionsSuccessEnvelope", InstancesOptionsData)

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

_instances_list_query_parser = new_parser()
_instances_list_query_parser.add_argument("page", type=int, default=1, location="args")
_instances_list_query_parser.add_argument("limit", type=int, default=20, location="args")
_instances_list_query_parser.add_argument("sort", type=str, default="id", location="args")
_instances_list_query_parser.add_argument("order", type=str, default="desc", location="args")
_instances_list_query_parser.add_argument("search", type=str, default="", location="args")
_instances_list_query_parser.add_argument("db_type", type=str, default="", location="args")
_instances_list_query_parser.add_argument("status", type=str, default="", location="args")
_instances_list_query_parser.add_argument("tags", type=str, action="append", location="args")
_instances_list_query_parser.add_argument(
    "include_deleted",
    type=bool_with_default(False),
    default=False,
    location="args",
)

_instances_options_query_parser = new_parser()
_instances_options_query_parser.add_argument("db_type", type=str, location="args")

_instances_export_query_parser = new_parser()
_instances_export_query_parser.add_argument("search", type=str, default="", location="args")
_instances_export_query_parser.add_argument("db_type", type=str, default="", location="args")


def _parse_instance_filters(parsed: dict[str, object]) -> InstanceListFilters:
    raw_page = parsed.get("page")
    page = max(int(raw_page) if isinstance(raw_page, int) else 1, 1)

    raw_limit = parsed.get("limit")
    limit = int(raw_limit) if isinstance(raw_limit, int) else 20
    limit = max(min(limit, 100), 1)
    sort_field = str(parsed.get("sort") or "id").lower()
    sort_order = str(parsed.get("order") or "desc").lower()
    if sort_order not in {"asc", "desc"}:
        sort_order = "desc"

    search = str(parsed.get("search") or "").strip()
    db_type = str(parsed.get("db_type") or "").strip()
    status_value = str(parsed.get("status") or "").strip()

    raw_tags = parsed.get("tags")
    tags: list[str] = []
    if isinstance(raw_tags, list):
        tags = [item.strip() for item in raw_tags if isinstance(item, str) and item.strip()]
    elif isinstance(raw_tags, str) and raw_tags.strip():
        tags = [raw_tags.strip()]

    include_deleted = bool(parsed.get("include_deleted") or False)

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


def _get_raw_payload() -> object:
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


@ns.route("/options")
class InstancesOptionsResource(BaseResource):
    """实例选项资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstancesOptionsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_instances_options_query_parser)
    @api_permission_required("view")
    def get(self):
        """获取实例选项."""
        parsed = _instances_options_query_parser.parse_args()
        db_type = str(parsed.get("db_type") or "").strip() or None

        def _execute():
            result = FilterOptionsService().get_common_instances_options(db_type=db_type)
            payload = marshal(result, INSTANCES_OPTIONS_RESPONSE_FIELDS)
            return self.success(data=payload, message="实例选项获取成功")

        return self.safe_call(
            _execute,
            module="instances",
            action="get_instance_options",
            public_error="加载实例选项失败",
            context={"db_type": db_type},
        )


@ns.route("")
class InstancesResource(BaseResource):
    """实例列表资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", InstancesListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_instances_list_query_parser)
    @api_permission_required("view")
    def get(self):
        """获取实例列表."""
        parsed = cast("dict[str, object]", _instances_list_query_parser.parse_args())
        filters = _parse_instance_filters(parsed)

        def _execute():
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
                "search": filters.search,
                "status": filters.status,
                "include_deleted": filters.include_deleted,
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
        payload: Any = _get_raw_payload()
        operator_id = getattr(current_user, "id", None)
        credential_context_raw = payload.get("credential_id")
        db_type_context_raw = payload.get("db_type")

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


@ns.route("/exports")
class InstancesExportResource(BaseResource):
    """实例导出资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK")
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_instances_export_query_parser)
    @api_permission_required("view")
    def get(self):
        """导出实例."""
        parsed = _instances_export_query_parser.parse_args()
        search = str(parsed.get("search") or "")
        db_type = str(parsed.get("db_type") or "")

        def _execute() -> Response:
            result = _instances_export_service.export_instances_csv(search=search, db_type=db_type)
            return Response(
                result.content,
                mimetype=result.mimetype,
                headers={"Content-Disposition": f"attachment; filename={result.filename}"},
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="export_instances",
            public_error="导出实例失败",
            context={"search": search, "db_type": db_type},
        )


@ns.route("/imports/template")
class InstancesImportTemplateResource(BaseResource):
    """实例导入模板资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK")
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
        """下载实例导入模板."""

        def _execute() -> Response:
            result = InstancesImportTemplateService().build_template_csv()
            return Response(
                result.content,
                mimetype=result.mimetype,
                headers={
                    "Content-Disposition": f"attachment; filename={result.filename}",
                    HttpHeaders.CONTENT_TYPE: result.mimetype,
                },
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="download_instances_template",
            public_error="下载模板失败",
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
        payload: Any = _get_raw_payload()
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

    @ns.response(200, "OK", InstanceDeleteSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def delete(self, instance_id: int):
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


@ns.route("/<int:instance_id>/actions/sync-capacity")
class InstanceSyncCapacityActionResource(BaseResource):
    """实例容量同步动作资源."""

    method_decorators: ClassVar[list] = [
        api_login_required,
        api_permission_required("update"),
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
            outcome = InstanceCapacitySyncActionsService().sync_instance_capacity(instance_id=instance_id)
            if outcome.success:
                return self.success(
                    data={"result": outcome.result},
                    message=outcome.message,
                    status=outcome.http_status,
                )
            return self.error_message(
                outcome.message,
                status=outcome.http_status,
                message_key=outcome.message_key,
                extra=outcome.extra,
            )

        return self.safe_call(
            _execute,
            module="databases_capacity",
            action="sync_instance_capacity",
            public_error="同步实例容量失败",
            context={"instance_id": instance_id},
        )

@ns.route("/<int:instance_id>/actions/restore")
class InstanceRestoreActionResource(BaseResource):
    """实例恢复动作资源."""

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
            message = "实例恢复成功" if outcome.restored else "实例未删除，无需恢复"
            return self.success(
                data={"instance": instance.to_dict()},
                message=message,
            )

        return self.safe_call(
            _execute,
            module="instances",
            action="restore_instance",
            public_error="恢复实例失败,请重试",
            context={"instance_id": instance_id},
        )


@ns.route("/actions/batch-create")
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


@ns.route("/actions/batch-delete")
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
        parsed_json = request.get_json(silent=True) if request.is_json else None
        raw = parsed_json if isinstance(parsed_json, dict) else {}
        operator_id = getattr(current_user, "id", None)
        raw_ids = raw.get("instance_ids")
        count = len(raw_ids) if isinstance(raw_ids, list) else 0

        def _execute():
            result = InstanceBatchDeletionService().delete_instances_from_payload(
                raw,
                operator_id=operator_id,
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
            context={"count": count},
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


# 注册 instances 下的连接测试/参数校验/状态查询路由 (side effects only)
from app.api.v1.namespaces import (  # noqa: F401,E402
    instances_accounts_sync as _instances_accounts_sync,
    instances_connections as _instances_connections,
)
