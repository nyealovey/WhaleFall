"""Instances namespace (Phase 2 核心域迁移)."""

from __future__ import annotations

from datetime import date
from typing import Any

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.constants import HttpStatus
from app.errors import ValidationError
from app.routes.instances.restx_models import (
    INSTANCE_ACCOUNT_CHANGE_HISTORY_ACCOUNT_FIELDS,
    INSTANCE_ACCOUNT_CHANGE_HISTORY_RESPONSE_FIELDS,
    INSTANCE_ACCOUNT_CHANGE_LOG_FIELDS,
    INSTANCE_ACCOUNT_INFO_FIELDS,
    INSTANCE_ACCOUNT_LIST_ITEM_FIELDS,
    INSTANCE_ACCOUNT_PERMISSIONS_FIELDS,
    INSTANCE_ACCOUNT_PERMISSIONS_RESPONSE_FIELDS,
    INSTANCE_ACCOUNT_SUMMARY_FIELDS,
    INSTANCE_DATABASE_SIZE_ENTRY_FIELDS,
    INSTANCE_LIST_ITEM_FIELDS,
    INSTANCE_TAG_FIELDS,
)
from app.services.instances.instance_accounts_service import InstanceAccountsService
from app.services.instances.instance_database_sizes_service import InstanceDatabaseSizesService
from app.services.instances.instance_detail_read_service import InstanceDetailReadService
from app.services.instances.instance_list_service import InstanceListService
from app.services.instances.instance_write_service import InstanceWriteService
from app.types.instance_accounts import InstanceAccountListFilters
from app.types.instance_database_sizes import InstanceDatabaseSizesQuery
from app.types.instances import InstanceListFilters
from app.utils.decorators import require_csrf
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.time_utils import time_utils

ns = Namespace("instances", description="实例管理")

ErrorEnvelope = get_error_envelope_model(ns)

InstanceWritePayload = ns.model(
    "InstanceWritePayload",
    {
        "name": fields.String(required=True),
        "db_type": fields.String(required=True),
        "host": fields.String(required=True),
        "port": fields.Integer(required=True),
        "database_name": fields.String(required=False),
        "credential_id": fields.Integer(required=False),
        "description": fields.String(required=False),
        "is_active": fields.Boolean(required=False),
        "tag_names": fields.List(fields.String, required=False),
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


def _parse_instance_filters() -> InstanceListFilters:
    args = request.args
    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=20,
        minimum=1,
        maximum=100,
        module="instances",
        action="list_instances",
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
        module="instances",
        action="list_instance_accounts",
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", InstancesListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", InstanceDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int):
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


@ns.route("/<int:instance_id>/delete")
class InstanceDeleteResource(BaseResource):
    method_decorators = [api_login_required]

    @ns.response(200, "OK", InstanceDeleteSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def post(self, instance_id: int):
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", InstanceDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("update")
    @require_csrf
    def post(self, instance_id: int):
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", InstanceAccountsListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int):
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", InstanceAccountPermissionsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int, account_id: int):
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", InstanceAccountChangeHistorySuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int, account_id: int):
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", InstanceDatabaseSizesSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, instance_id: int):
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
            try:
                return int(value)
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
