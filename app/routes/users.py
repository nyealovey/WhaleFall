"""鲸落 - 用户管理路由."""

from typing import cast

from collections.abc import Callable
from flask import Blueprint, Response, flash, render_template, request
from flask_login import current_user, login_required
from flask_restx import marshal
from flask.typing import ResponseReturnValue, RouteCallable

from app import db
from app.constants import STATUS_ACTIVE_OPTIONS, FlashCategory, HttpStatus, UserRole
from app.errors import ConflictError, SystemError, ValidationError
from app.models.user import User
from app.routes.users_restx_models import USER_LIST_ITEM_FIELDS
from app.services.users import UserFormService, UsersListService, UsersStatsService
from app.types.users import UserListFilters
from app.utils.decorators import (
    create_required,
    delete_required,
    require_csrf,
    update_required,
    view_required,
)
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.sensitive_data import scrub_sensitive_fields
from app.utils.structlog_config import log_info
from app.views.user_forms import UserFormView

# 创建蓝图
users_bp = Blueprint("users", __name__)
_user_form_service = UserFormService()
_users_list_service = UsersListService()


@users_bp.route("/")
@login_required
@view_required
def index() -> str:
    """用户管理首页.

    渲染用户管理页面,支持搜索、角色和状态筛选.

    Returns:
        渲染后的 HTML 页面.

    Query Parameters:
        search: 搜索关键词,可选.
        role: 角色筛选,可选.
        status: 状态筛选('all'、'active'、'inactive'),默认 'all'.

    """

    def _execute() -> str:
        role_options = [{"value": role, "label": UserRole.get_display_name(role)} for role in UserRole.ALL]
        return render_template(
            "auth/list.html",
            role_options=role_options,
            status_options=STATUS_ACTIVE_OPTIONS,
            search=request.args.get("search", "", type=str),
            role=request.args.get("role", "", type=str),
            status=request.args.get("status", "all", type=str),
        )

    try:
        return safe_route_call(
            _execute,
            module="users",
            action="index",
            public_error="加载用户管理页面失败",
            context={"endpoint": "users_index"},
            expected_exceptions=(SystemError,),
        )
    except SystemError as exc:
        flash(f"获取用户列表失败: {exc!s}", FlashCategory.ERROR)
        return render_template("auth/list.html", role_options=[], status_options=STATUS_ACTIVE_OPTIONS)


@users_bp.route("/api/users")
@login_required
@view_required
def list_users() -> tuple[Response, int]:
    """获取用户列表 API.

    支持分页、排序、搜索和筛选.

    Returns:
        (JSON 响应, HTTP 状态码).

    Query Parameters:
        page: 页码,默认 1.
        page_size: 每页数量,默认 10(兼容 limit/pageSize).
        sort: 排序字段,默认 'created_at'.
        order: 排序方向('asc'、'desc'),默认 'desc'.
        search: 搜索关键词,可选.
        role: 角色筛选,可选.
        status: 状态筛选,可选.

    """
    page = resolve_page(request.args, default=1, minimum=1)
    limit = resolve_page_size(
        request.args,
        default=10,
        minimum=1,
        maximum=200,
        module="users",
        action="list_users",
    )
    sort_field = request.args.get("sort", "created_at", type=str)
    sort_order = request.args.get("order", "desc", type=str)
    search = request.args.get("search", "", type=str)
    role_filter = request.args.get("role", "", type=str)
    status_filter = request.args.get("status", "", type=str)

    def _execute() -> tuple[Response, int]:
        filters = UserListFilters(
            page=page,
            limit=limit,
            search=search,
            role=role_filter if role_filter else None,
            status=status_filter if status_filter else None,
            sort_field=sort_field.lower(),
            sort_order=sort_order.lower(),
        )
        result = _users_list_service.list_users(filters)
        users_data = marshal(result.items, USER_LIST_ITEM_FIELDS)

        return jsonify_unified_success(
            data={
                "items": users_data,
                "total": result.total,
                "page": result.page,
                "pages": result.pages,
                "limit": result.limit,
            },
        )

    return safe_route_call(
        _execute,
        module="users",
        action="list_users",
        public_error="获取用户列表失败",
        context={
            "search": search,
            "role": role_filter,
            "status": status_filter,
            "sort": sort_field,
            "order": sort_order,
            "page": page,
            "limit": limit,
        },
    )


@users_bp.route("/api/users/<int:user_id>")
@login_required
@view_required
def get_user(user_id: int) -> tuple[Response, int]:
    """获取单个用户信息 API.

    Args:
        user_id: 用户 ID.

    Returns:
        (JSON 响应, HTTP 状态码).

    Raises:
        NotFoundError: 当用户不存在时抛出.

    """
    user = User.query.get_or_404(user_id)
    return jsonify_unified_success(
        data={"user": user.to_dict()},
        message="获取用户信息成功",
    )


@users_bp.route("/api/users", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_user() -> tuple[Response, int]:
    """创建用户 API.

    Returns:
        (JSON 响应, HTTP 状态码).

    Raises:
        ConflictError: 当用户名已存在时抛出.
        ValidationError: 当表单验证失败时抛出.

    """
    payload = request.get_json(silent=True) or {}
    sanitized_payload = scrub_sensitive_fields(payload)

    log_info(
        "创建用户请求",
        module="users",
        user_id=current_user.id,
        request_data=sanitized_payload,
    )

    result = _user_form_service.upsert(payload)
    if not result.success or not result.data:
        if result.message_key == UserFormService.MESSAGE_USERNAME_EXISTS:
            raise ConflictError(result.message or "用户名已存在")
        raise ValidationError(result.message or "用户创建失败")

    user = result.data

    log_info(
        "创建用户成功",
        module="users",
        user_id=current_user.id,
        created_user_id=user.id,
        created_username=user.username,
        created_role=user.role,
        is_active=user.is_active,
    )

    return jsonify_unified_success(
        data={"user": user.to_dict()},
        message="用户创建成功",
        status=HttpStatus.CREATED,
    )


@users_bp.route("/api/users/<int:user_id>", methods=["PUT"])
@login_required
@update_required
@require_csrf
def update_user(user_id: int) -> tuple[Response, int]:
    """更新用户 API.

    Args:
        user_id: 目标用户 ID.

    Returns:
        tuple[Response, int]: 更新后的用户 JSON 与状态码.

    """
    user = User.query.get_or_404(user_id)
    payload = request.get_json(silent=True) or {}
    sanitized_payload = scrub_sensitive_fields(payload)

    log_info(
        "更新用户请求",
        module="users",
        user_id=current_user.id,
        target_user_id=user_id,
        request_data=sanitized_payload,
    )

    result = _user_form_service.upsert(payload, user)
    if not result.success or not result.data:
        if result.message_key == UserFormService.MESSAGE_USERNAME_EXISTS:
            raise ConflictError(result.message or "用户名已存在")
        raise ValidationError(result.message or "用户更新失败")

    user = result.data

    log_info(
        "更新用户",
        module="users",
        user_id=current_user.id,
        updated_user_id=user.id,
        updated_username=user.username,
        updated_role=user.role,
        is_active=user.is_active,
    )

    return jsonify_unified_success(
        data={"user": user.to_dict()},
        message="用户更新成功",
    )


@users_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
@login_required
@delete_required
@require_csrf
def delete_user(user_id: int) -> tuple[Response, int]:
    """删除用户 API.

    不允许删除自己的账户或最后一个管理员账户.

    Args:
        user_id: 用户 ID.

    Returns:
        (JSON 响应, HTTP 状态码).

    Raises:
        NotFoundError: 当用户不存在时抛出.
        ValidationError: 当删除操作不被允许时抛出.

    """
    user = User.query.get_or_404(user_id)
    deleted_username = user.username
    deleted_role = user.role

    def _execute() -> tuple[Response, int]:
        if user.id == current_user.id:
            msg = "不能删除自己的账户"
            raise ValidationError(msg)

        if user.role == UserRole.ADMIN:
            admin_count = User.query.filter_by(role=UserRole.ADMIN).count()
            if admin_count <= 1:
                msg = "不能删除最后一个管理员账户"
                raise ValidationError(msg)

        db.session.delete(user)

        log_info(
            "删除用户",
            module="users",
            user_id=current_user.id,
            deleted_user_id=user_id,
            deleted_username=deleted_username,
            deleted_role=deleted_role,
        )

        return jsonify_unified_success(message="用户删除成功")

    return safe_route_call(
        _execute,
        module="users",
        action="delete_user",
        public_error="删除用户失败",
        context={"target_user_id": user_id, "target_role": user.role},
        expected_exceptions=(ValidationError,),
    )


@users_bp.route("/api/users/stats")
@login_required
@view_required
def get_user_stats() -> tuple[Response, int]:
    """获取用户统计信息 API.

    Returns:
        tuple[Response, int]: 用户统计 JSON 与状态码.

    """
    def _execute() -> tuple[Response, int]:
        data = UsersStatsService().get_stats()
        return jsonify_unified_success(data=data)

    return safe_route_call(
        _execute,
        module="users",
        action="get_user_stats",
        public_error="获取用户统计信息失败",
    )


# ---------------------------------------------------------------------------
# 表单路由
# ---------------------------------------------------------------------------
_user_create_view = cast(
    Callable[..., ResponseReturnValue],
    UserFormView.as_view("user_create_form"),
)
_user_create_view = login_required(create_required(require_csrf(_user_create_view)))

users_bp.add_url_rule(
    "/create",
    view_func=cast(RouteCallable, _user_create_view),
    methods=["GET", "POST"],
    defaults={"resource_id": None},
    endpoint="create",
)

_user_edit_view = cast(
    Callable[..., ResponseReturnValue],
    UserFormView.as_view("user_edit_form"),
)
_user_edit_view = login_required(update_required(require_csrf(_user_edit_view)))

users_bp.add_url_rule(
    "/<int:user_id>/edit",
    view_func=cast(RouteCallable, _user_edit_view),
    methods=["GET", "POST"],
    endpoint="edit",
)
