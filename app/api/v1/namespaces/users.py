"""Users namespace."""

from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar, cast

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import new_parser
from app.core.exceptions import NotFoundError
from app.core.types import JsonValue
from app.core.types.users import UserListFilters
from app.services.users import UserDetailReadService, UsersListService, UsersStatsService, UserWriteService
from app.utils.decorators import require_csrf
from app.utils.sensitive_data import scrub_sensitive_fields
from app.utils.structlog_config import log_info

ns = Namespace("users", description="用户管理")

ErrorEnvelope = get_error_envelope_model(ns)


USER_ITEM_FIELDS: dict[str, fields.Raw] = {
    "id": fields.Integer(),
    "username": fields.String(),
    "role": fields.String(),
    "created_at": fields.String(),
    "created_at_display": fields.String(),
    "last_login": fields.String(),
    "is_active": fields.Boolean(),
}

UserItemModel = ns.model(
    "UserItem",
    {
        "id": fields.Integer(required=True, description="用户 ID", example=1),
        "username": fields.String(required=True, description="用户名", example="alice"),
        "role": fields.String(required=True, description="角色(admin/user)", example="admin"),
        "created_at": fields.String(required=False, description="创建日期(YYYY-MM-DD)", example="2025-01-01"),
        "created_at_display": fields.String(required=False, description="创建日期展示字段", example="2025-01-01"),
        "last_login": fields.String(required=False, description="最后登录时间(ISO8601)", example="2025-01-01T00:00:00"),
        "is_active": fields.Boolean(required=True, description="是否启用", example=True),
    },
)

UsersListData = ns.model(
    "UsersListData",
    {
        "items": fields.List(fields.Nested(UserItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
    },
)

UsersListSuccessEnvelope = make_success_envelope_model(ns, "UsersListSuccessEnvelope", UsersListData)

UserDetailData = ns.model(
    "UserDetailData",
    {
        "user": fields.Nested(UserItemModel),
    },
)

UserDetailSuccessEnvelope = make_success_envelope_model(ns, "UserDetailSuccessEnvelope", UserDetailData)

UserDeleteSuccessEnvelope = make_success_envelope_model(ns, "UserDeleteSuccessEnvelope")

UsersStatsData = ns.model(
    "UsersStatsData",
    {
        "total": fields.Integer(required=True, description="用户总数", example=10),
        "active": fields.Integer(required=True, description="活跃用户数", example=9),
        "inactive": fields.Integer(required=True, description="停用用户数", example=1),
        "admin": fields.Integer(required=True, description="管理员用户数", example=1),
        "user": fields.Integer(required=True, description="普通用户数", example=9),
    },
)

UsersStatsSuccessEnvelope = make_success_envelope_model(ns, "UsersStatsSuccessEnvelope", UsersStatsData)

UserCreatePayload = ns.model(
    "UserCreatePayload",
    {
        "username": fields.String(required=True, description="用户名(3-20位,字母数字下划线)"),
        "role": fields.String(required=True, description="角色(admin/user)"),
        "password": fields.String(required=True, description="初始密码(需包含大小写与数字)"),
        "is_active": fields.Boolean(required=False, description="是否启用", example=True),
    },
)

UserUpdatePayload = ns.model(
    "UserUpdatePayload",
    {
        "username": fields.String(required=True, description="用户名(3-20位,字母数字下划线)"),
        "role": fields.String(required=True, description="角色(admin/user)"),
        "password": fields.String(required=False, description="新密码(可选)"),
        "is_active": fields.Boolean(required=True, description="是否启用"),
    },
)


_users_list_query_parser = new_parser()
_users_list_query_parser.add_argument("page", type=int, default=1, location="args")
_users_list_query_parser.add_argument("limit", type=int, default=10, location="args")
_users_list_query_parser.add_argument("sort", type=str, default="created_at", location="args")
_users_list_query_parser.add_argument("order", type=str, default="desc", location="args")
_users_list_query_parser.add_argument("search", type=str, default="", location="args")
_users_list_query_parser.add_argument("role", type=str, default="", location="args")
_users_list_query_parser.add_argument("status", type=str, default="", location="args")


def _parse_user_list_filters(parsed: Mapping[str, object]) -> UserListFilters:
    raw_page = parsed.get("page")
    page = max(int(raw_page) if isinstance(raw_page, int) else 1, 1)

    raw_limit = parsed.get("limit")
    limit = int(raw_limit) if isinstance(raw_limit, int) else 10
    limit = max(min(limit, 200), 1)
    sort_field = str(parsed.get("sort") or "created_at").lower()
    sort_order = str(parsed.get("order") or "desc").lower()
    if sort_order not in {"asc", "desc"}:
        sort_order = "desc"
    search = str(parsed.get("search") or "")
    role_filter = str(parsed.get("role") or "")
    status_filter = str(parsed.get("status") or "")

    return UserListFilters(
        page=page,
        limit=limit,
        search=search,
        role=role_filter if role_filter else None,
        status=status_filter if status_filter else None,
        sort_field=sort_field,
        sort_order=sort_order,
    )


def _get_raw_payload() -> object:
    if request.is_json:
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}
    return request.form


def _get_user_or_error(user_id: int) -> dict[str, object]:
    user = UserDetailReadService().get_user_or_error(user_id)
    return user.to_dict()


def _build_user_write_service() -> UserWriteService:
    return UserWriteService()


@ns.route("")
class UsersResource(BaseResource):
    """用户列表资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", UsersListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_users_list_query_parser)
    @api_permission_required("view")
    def get(self):
        """获取用户列表."""
        query_snapshot = request.args.to_dict(flat=False)

        def _execute():
            parsed = cast("dict[str, object]", _users_list_query_parser.parse_args())
            filters = _parse_user_list_filters(parsed)
            result = UsersListService().list_users(filters)
            items = marshal(result.items, USER_ITEM_FIELDS)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                    "limit": result.limit,
                },
                message="获取用户列表成功",
            )

        return self.safe_call(
            _execute,
            module="users",
            action="list_users",
            public_error="获取用户列表失败",
            context={
                "query_params": query_snapshot,
            },
        )

    @ns.expect(UserCreatePayload, validate=False)
    @ns.response(201, "Created", UserDetailSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("create")
    @require_csrf
    def post(self):
        """创建用户."""
        payload = cast("Mapping[str, JsonValue]", _get_raw_payload())
        sanitized = scrub_sensitive_fields(payload)

        log_info(
            "创建用户请求",
            module="users",
            user_id=current_user.id,
            request_data=sanitized,
        )

        def _execute():
            user = _build_user_write_service().create(payload, operator_id=current_user.id)
            return self.success(
                data={"user": user.to_dict()},
                message="用户创建成功",
                status=201,
            )

        return self.safe_call(
            _execute,
            module="users",
            action="create_user",
            public_error="用户创建失败",
            context={"target_username": cast("str | None", payload.get("username"))},
        )


@ns.route("/<int:user_id>")
class UserDetailResource(BaseResource):
    """用户详情资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", UserDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, user_id: int):
        """获取用户信息."""

        def _execute():
            data = _get_user_or_error(user_id)
            return self.success(data={"user": data}, message="获取用户信息成功")

        return self.safe_call(
            _execute,
            module="users",
            action="get_user",
            public_error="获取用户信息失败",
            context={"user_id": user_id},
            expected_exceptions=(NotFoundError,),
        )

    @ns.expect(UserUpdatePayload, validate=False)
    @ns.response(200, "OK", UserDetailSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("update")
    @require_csrf
    def put(self, user_id: int):
        """更新用户."""
        payload = cast("Mapping[str, JsonValue]", _get_raw_payload())
        sanitized = scrub_sensitive_fields(payload)

        log_info(
            "更新用户请求",
            module="users",
            user_id=current_user.id,
            target_user_id=user_id,
            request_data=sanitized,
        )

        def _execute():
            user = _build_user_write_service().update(user_id, payload, operator_id=current_user.id)
            return self.success(
                data={"user": user.to_dict()},
                message="用户更新成功",
            )

        return self.safe_call(
            _execute,
            module="users",
            action="update_user",
            public_error="用户更新失败",
            context={"target_user_id": user_id},
        )

    @ns.response(200, "OK", UserDeleteSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def delete(self, user_id: int):
        """删除用户."""

        def _execute():
            _build_user_write_service().delete(user_id, operator_id=current_user.id)
            return self.success(message="用户删除成功")

        return self.safe_call(
            _execute,
            module="users",
            action="delete_user",
            public_error="删除用户失败",
            context={"target_user_id": user_id},
        )


@ns.route("/stats")
class UsersStatsResource(BaseResource):
    """用户统计资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", UsersStatsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
        """获取用户统计."""

        def _execute():
            data = UsersStatsService().get_stats()
            return self.success(data=data, message="获取用户统计成功")

        return self.safe_call(
            _execute,
            module="users",
            action="get_user_stats",
            public_error="获取用户统计信息失败",
        )
