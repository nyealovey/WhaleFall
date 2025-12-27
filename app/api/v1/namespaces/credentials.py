"""Credentials namespace (Phase 2 核心域迁移)."""

from __future__ import annotations

from typing import Any

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.constants import HttpStatus
from app.constants.system_constants import SuccessMessages
from app.errors import NotFoundError
from app.repositories.credentials_repository import CredentialsRepository
from app.routes.credentials_restx_models import CREDENTIAL_LIST_ITEM_FIELDS
from app.services.credentials import CredentialWriteService, CredentialsListService
from app.types.credentials import CredentialListFilters
from app.utils.decorators import require_csrf
from app.utils.pagination_utils import resolve_page, resolve_page_size

ns = Namespace("credentials", description="凭据管理")

ErrorEnvelope = get_error_envelope_model(ns)

CredentialCreatePayload = ns.model(
    "CredentialCreatePayload",
    {
        "name": fields.String(required=True),
        "credential_type": fields.String(required=True),
        "db_type": fields.String(required=False),
        "username": fields.String(required=True),
        "password": fields.String(required=True),
        "description": fields.String(required=False),
        "is_active": fields.Boolean(required=False),
    },
)

CredentialUpdatePayload = ns.model(
    "CredentialUpdatePayload",
    {
        "name": fields.String(required=True),
        "credential_type": fields.String(required=True),
        "db_type": fields.String(required=False),
        "username": fields.String(required=True),
        "password": fields.String(required=False),
        "description": fields.String(required=False),
        "is_active": fields.Boolean(required=False),
    },
)

CredentialListItemModel = ns.model(
    "CredentialListItem",
    {
        "id": fields.Integer(),
        "name": fields.String(),
        "credential_type": fields.String(),
        "db_type": fields.String(),
        "username": fields.String(),
        "category_id": fields.Integer(),
        "created_at": fields.String(),
        "updated_at": fields.String(),
        "password": fields.String(),
        "description": fields.String(),
        "is_active": fields.Boolean(),
        "instance_count": fields.Integer(),
        "created_at_display": fields.String(),
    },
)

CredentialsListData = ns.model(
    "CredentialsListData",
    {
        "items": fields.List(fields.Nested(CredentialListItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
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
        "credential_id": fields.Integer(),
    },
)

CredentialDeleteSuccessEnvelope = make_success_envelope_model(ns, "CredentialDeleteSuccessEnvelope", CredentialDeleteData)


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


def _extract_tags() -> list[str]:
    return [tag.strip() for tag in request.args.getlist("tags") if tag and tag.strip()]


def _parse_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _build_filters(*, allow_sort: bool) -> CredentialListFilters:
    args = request.args
    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=20,
        minimum=1,
        maximum=200,
        module="credentials",
        action="list_credentials",
    )

    search = (args.get("search") or "").strip()
    credential_type = _normalize_choice(args.get("credential_type", "", type=str))
    db_type = _normalize_choice(args.get("db_type", "", type=str))
    status = _normalize_status(args.get("status", "", type=str))
    tags = _extract_tags()

    sort_field = "created_at"
    sort_order = "desc"
    if allow_sort:
        sort_field = (args.get("sort", "created_at", type=str) or "created_at").lower()
        sort_order_candidate = (args.get("order", "desc", type=str) or "desc").lower()
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", CredentialsListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
        filters = _build_filters(allow_sort=True)

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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", CredentialDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, credential_id: int):
        def _execute():
            credential = CredentialsRepository().get_by_id(credential_id)
            if credential is None:
                raise NotFoundError(message="凭据不存在", extra={"credential_id": credential_id})
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


@ns.route("/<int:credential_id>/delete")
class CredentialDeleteResource(BaseResource):
    method_decorators = [api_login_required]

    @ns.response(200, "OK", CredentialDeleteSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def post(self, credential_id: int):
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
