"""Credentials namespace (Phase 2 核心域迁移)."""

from __future__ import annotations

from typing import Any, ClassVar, cast

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import new_parser
from app.api.v1.restx_models.credentials import CREDENTIAL_LIST_ITEM_FIELDS
from app.constants import HttpStatus
from app.constants.system_constants import SuccessMessages
from app.errors import NotFoundError
from app.services.credentials import CredentialDetailReadService, CredentialsListService, CredentialWriteService
from app.types.credentials import CredentialListFilters
from app.utils.decorators import require_csrf

ns = Namespace("credentials", description="凭据管理")

ErrorEnvelope = get_error_envelope_model(ns)

CredentialCreatePayload = ns.model(
    "CredentialCreatePayload",
    {
        "name": fields.String(required=True, description="凭据名称", example="prod-db-user"),
        "credential_type": fields.String(required=True, description="凭据类型", example="password"),
        "db_type": fields.String(required=False, description="数据库类型(可选)", example="mysql"),
        "username": fields.String(required=True, description="用户名", example="db_user"),
        "password": fields.String(required=True, description="密码", example="your_password"),
        "description": fields.String(required=False, description="描述(可选)", example="用于生产环境"),
        "is_active": fields.Boolean(required=False, description="是否启用(可选)", example=True),
    },
)

CredentialUpdatePayload = ns.model(
    "CredentialUpdatePayload",
    {
        "name": fields.String(required=True, description="凭据名称", example="prod-db-user"),
        "credential_type": fields.String(required=True, description="凭据类型", example="password"),
        "db_type": fields.String(required=False, description="数据库类型(可选)", example="mysql"),
        "username": fields.String(required=True, description="用户名", example="db_user"),
        "password": fields.String(required=False, description="密码(可选)", example="new_password"),
        "description": fields.String(required=False, description="描述(可选)", example="用于生产环境"),
        "is_active": fields.Boolean(required=False, description="是否启用(可选)", example=True),
    },
)

CredentialListItemModel = ns.model("CredentialListItem", CREDENTIAL_LIST_ITEM_FIELDS)

CredentialsListData = ns.model(
    "CredentialsListData",
    {
        "items": fields.List(fields.Nested(CredentialListItemModel), description="凭据列表"),
        "total": fields.Integer(description="总数", example=1),
        "page": fields.Integer(description="页码", example=1),
        "pages": fields.Integer(description="总页数", example=1),
        "limit": fields.Integer(description="分页大小", example=20),
    },
)

CredentialsListSuccessEnvelope = make_success_envelope_model(ns, "CredentialsListSuccessEnvelope", CredentialsListData)

CredentialDetailData = ns.model(
    "CredentialDetailData",
    {
        "credential": fields.Raw(description="凭据详情"),
    },
)

CredentialDetailSuccessEnvelope = make_success_envelope_model(
    ns, "CredentialDetailSuccessEnvelope", CredentialDetailData
)

CredentialWriteSuccessEnvelope = CredentialDetailSuccessEnvelope

CredentialDeleteData = ns.model(
    "CredentialDeleteData",
    {
        "credential_id": fields.Integer(description="凭据 ID", example=1),
    },
)

CredentialDeleteSuccessEnvelope = make_success_envelope_model(
    ns, "CredentialDeleteSuccessEnvelope", CredentialDeleteData
)

_credentials_list_query_parser = new_parser()
_credentials_list_query_parser.add_argument("page", type=int, default=1, location="args")
_credentials_list_query_parser.add_argument("limit", type=int, default=20, location="args")
_credentials_list_query_parser.add_argument("search", type=str, default="", location="args")
_credentials_list_query_parser.add_argument("credential_type", type=str, default="", location="args")
_credentials_list_query_parser.add_argument("db_type", type=str, default="", location="args")
_credentials_list_query_parser.add_argument("status", type=str, default="", location="args")
_credentials_list_query_parser.add_argument("tags", type=str, action="append", location="args")
_credentials_list_query_parser.add_argument("sort", type=str, default="created_at", location="args")
_credentials_list_query_parser.add_argument("order", type=str, default="desc", location="args")


def _normalize_choice(raw_value: str) -> str | None:
    value = (raw_value or "").strip()
    if not value or value.lower() == "all":
        return None
    return value


def _normalize_status(raw_value: str) -> str | None:
    value = (raw_value or "").strip().lower()
    if value in {"active", "inactive"}:
        return value
    return None


def _parse_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _build_filters(parsed: dict[str, object], *, allow_sort: bool) -> CredentialListFilters:
    raw_page = parsed.get("page")
    page = max(int(raw_page) if isinstance(raw_page, int) else 1, 1)

    raw_limit = parsed.get("limit")
    limit = int(raw_limit) if isinstance(raw_limit, int) else 20
    limit = max(min(limit, 200), 1)

    search = cast(str, parsed.get("search") or "").strip()
    credential_type = _normalize_choice(cast(str, parsed.get("credential_type") or ""))
    db_type = _normalize_choice(cast(str, parsed.get("db_type") or ""))
    status = _normalize_status(cast(str, parsed.get("status") or ""))

    raw_tags = parsed.get("tags")
    tags: list[str] = []
    if isinstance(raw_tags, list):
        tags = [item.strip() for item in raw_tags if isinstance(item, str) and item.strip()]
    elif isinstance(raw_tags, str) and raw_tags.strip():
        tags = [raw_tags.strip()]

    sort_field = "created_at"
    sort_order = "desc"
    if allow_sort:
        sort_field = cast(str, parsed.get("sort") or "created_at").lower()
        sort_order_candidate = cast(str, parsed.get("order") or "desc").lower()
        sort_order = sort_order_candidate if sort_order_candidate in {"asc", "desc"} else "desc"

    return CredentialListFilters(
        page=page,
        limit=limit,
        search=search,
        credential_type=credential_type,
        db_type=db_type,
        status=status,
        tags=tags,
        sort_field=sort_field,
        sort_order=sort_order,
    )


@ns.route("")
class CredentialsResource(BaseResource):
    """凭据列表资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", CredentialsListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_credentials_list_query_parser)
    @api_permission_required("view")
    def get(self):
        """获取凭据列表."""
        parsed = cast("dict[str, object]", _credentials_list_query_parser.parse_args())
        filters = _build_filters(parsed, allow_sort=True)

        def _execute():
            result = CredentialsListService().list_credentials(filters)
            items = marshal(result.items, CREDENTIAL_LIST_ITEM_FIELDS)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                    "limit": result.limit,
                },
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="credentials",
            action="list_credentials",
            public_error="获取凭据列表失败",
            context={
                "search": filters.search,
                "credential_type": filters.credential_type,
                "db_type": filters.db_type,
                "status": filters.status,
                "tags": filters.tags,
                "sort": filters.sort_field,
                "order": filters.sort_order,
                "page": filters.page,
                "limit": filters.limit,
            },
        )

    @ns.expect(CredentialCreatePayload, validate=False)
    @ns.response(201, "Created", CredentialWriteSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("create")
    @require_csrf
    def post(self):
        """创建凭据."""
        payload = _parse_payload()
        operator_id = getattr(current_user, "id", None)

        def _execute():
            credential = CredentialWriteService().create(payload, operator_id=operator_id)
            return self.success(
                data={"credential": credential.to_dict()},
                message=SuccessMessages.DATA_SAVED,
                status=HttpStatus.CREATED,
            )

        return self.safe_call(
            _execute,
            module="credentials",
            action="create_credential_rest",
            public_error="创建凭据失败",
            context={"credential_name": payload.get("name")},
        )


@ns.route("/<int:credential_id>")
class CredentialDetailResource(BaseResource):
    """凭据详情资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", CredentialDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, credential_id: int):
        """获取凭据详情."""

        def _execute():
            credential = CredentialDetailReadService().get_credential_or_error(credential_id)
            return self.success(
                data={"credential": credential.to_dict()},
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="credentials",
            action="get_credential",
            public_error="获取凭据详情失败",
            context={"credential_id": credential_id},
            expected_exceptions=(NotFoundError,),
        )

    @ns.expect(CredentialUpdatePayload, validate=False)
    @ns.response(200, "OK", CredentialWriteSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("update")
    @require_csrf
    def put(self, credential_id: int):
        """更新凭据."""
        payload = _parse_payload()
        operator_id = getattr(current_user, "id", None)

        def _execute():
            credential = CredentialWriteService().update(credential_id, payload, operator_id=operator_id)
            return self.success(
                data={"credential": credential.to_dict()},
                message=SuccessMessages.DATA_UPDATED,
            )

        return self.safe_call(
            _execute,
            module="credentials",
            action="update_credential_rest",
            public_error="更新凭据失败",
            context={"credential_id": credential_id},
        )

    @ns.response(200, "OK", CredentialDeleteSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def delete(self, credential_id: int):
        """删除凭据."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            CredentialWriteService().delete(credential_id, operator_id=operator_id)
            return self.success(
                data={"credential_id": credential_id},
                message=SuccessMessages.DATA_DELETED,
            )

        return self.safe_call(
            _execute,
            module="credentials",
            action="delete_credential",
            public_error="删除凭据失败",
            context={"credential_id": credential_id},
        )
