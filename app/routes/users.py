"""鲸落 - 用户管理路由."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from flask import Blueprint, render_template, request
from flask.typing import ResponseReturnValue, RouteCallable
from flask_login import login_required

from app.core.constants import STATUS_ACTIVE_OPTIONS, UserRole
from app.infra.route_safety import safe_route_call
from app.utils.decorators import create_required, require_csrf, update_required, view_required
from app.utils.user_role_utils import get_user_role_display_name
from app.views.user_forms import UserFormView

# 创建蓝图
users_bp = Blueprint("users", __name__)


@users_bp.route("/")
@login_required
@view_required
def index() -> str:
    """用户管理首页."""
    search = request.args.get("search", "", type=str)
    role_param = request.args.get("role", "", type=str)
    status_param = request.args.get("status", "all", type=str)

    def _execute() -> str:
        role_options = [{"value": role, "label": get_user_role_display_name(role)} for role in UserRole.ALL]
        return render_template(
            "auth/list.html",
            role_options=role_options,
            status_options=STATUS_ACTIVE_OPTIONS,
            search=search,
            role=role_param,
            status=status_param,
        )

    return safe_route_call(
        _execute,
        module="users",
        action="index",
        public_error="加载用户管理页面失败",
        context={"endpoint": "users_index"},
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
