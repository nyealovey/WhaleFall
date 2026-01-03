"""Users namespace."""

from __future__ import annotations

from typing import ClassVar, cast

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.errors import NotFoundError
from app.repositories.users_repository import UsersRepository
from app.services.users import UsersListService, UsersStatsService, UserWriteService
from app.types import ResourcePayload
from app.types.users import UserListFilters
from app.utils.decorators import require_csrf
from app.utils.pagination_utils import resolve_page, resolve_page_size
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
        "username": fields.String(required=False, description="用户名(3-20位,字母数字下划线)"),
        "role": fields.String(required=False, description="角色(admin/user)"),
        "password": fields.String(required=False, description="新密码(可选)"),
        "is_active": fields.Boolean(required=False, description="是否启用"),
    },
)


def _parse_user_list_filters() -> UserListFilters:
    args = request.args
    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=10,
        minimum=1,
        maximum=200,
    )
    sort_field = (args.get("sort", "created_at", type=str) or "created_at").lower()
    sort_order = (args.get("order", "desc", type=str) or "desc").lower()
    search = args.get("search", "", type=str) or ""
    role_filter = args.get("role", "", type=str) or ""
    status_filter = args.get("status", "", type=str) or ""

    return UserListFilters(
        page=page,
        limit=limit,
        search=search,
        role=role_filter if role_filter else None,
        status=status_filter if status_filter else None,
        sort_field=sort_field,
        sort_order=sort_order,
    )


def _parse_payload() -> ResourcePayload:
    if request.is_json:
        payload = request.get_json(silent=True)
        return cast(ResourcePayload, payload) if isinstance(payload, dict) else {}
    return {}


def _get_user_or_error(user_id: int) -> dict[str, object]:
    user = UsersRepository().get_by_id(user_id)
    if user is None:
        raise NotFoundError("用户不存在", extra={"user_id": user_id})
    return user.to_dict()


@ns.route("")
class UsersResource(BaseResource):
    """用户列表资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", UsersListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
        """获取用户列表."""
        filters = _parse_user_list_filters()

        def _execute():
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
                "search": filters.search,
                "role": filters.role,
                "status": filters.status,
                "sort": filters.sort_field,
                "order": filters.sort_order,
                "page": filters.page,
                "limit": filters.limit,
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
        payload = _parse_payload()
        sanitized = scrub_sensitive_fields(payload)

        log_info(
            "创建用户请求",
            module="users",
            user_id=current_user.id,
            request_data=sanitized,
        )

        def _execute():
            user = UserWriteService().create(payload, operator_id=current_user.id)
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
            context={"target_username": payload.get("username")},
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
        payload = _parse_payload()
        sanitized = scrub_sensitive_fields(payload)

        log_info(
            "更新用户请求",
            module="users",
            user_id=current_user.id,
            target_user_id=user_id,
            request_data=sanitized,
        )

        def _execute():
            user = UserWriteService().update(user_id, payload, operator_id=current_user.id)
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
            UserWriteService().delete(user_id, operator_id=current_user.id)
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
