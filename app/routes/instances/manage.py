"""鲸落 - 数据库实例管理路由."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from flask import Blueprint, render_template, request
from flask.typing import ResponseReturnValue, RouteCallable
from flask_login import login_required

from app.services.instances.instance_list_page_service import InstanceListPageService
from app.utils.decorators import create_required, require_csrf, update_required, view_required
from app.utils.route_safety import safe_route_call
from app.views.instance_forms import InstanceFormView

# 创建蓝图
instances_bp = Blueprint("instances", __name__)
_instance_list_page_service = InstanceListPageService()


@instances_bp.route("/")
@login_required
@view_required
def index() -> str:
    """实例管理首页.

    渲染实例列表页面,支持搜索、筛选和标签过滤.

    Returns:
        渲染后的 HTML 页面.

    """
    search = (request.args.get("search") or "").strip()
    db_type = (request.args.get("db_type") or "").strip()
    status_param = (request.args.get("status") or "").strip()
    include_deleted_raw = (request.args.get("include_deleted") or "").strip().lower()
    include_deleted = include_deleted_raw in {"true", "1", "on", "yes"}
    tags_raw = request.args.getlist("tags")
    tags = [tag.strip() for tag in tags_raw if tag.strip()]

    def _render() -> str:
        context = _instance_list_page_service.build_context(
            search=search,
            db_type=db_type,
            status=status_param,
            include_deleted=include_deleted,
            selected_tags=tags,
        )
        return render_template(
            "instances/list.html",
            credentials=context.credentials,
            database_type_options=context.database_type_options,
            database_type_map=context.database_type_map,
            tag_options=context.tag_options,
            status_options=context.status_options,
            search=context.search,
            db_type=context.db_type,
            status=context.status,
            include_deleted=context.include_deleted,
            selected_tags=context.selected_tags,
        )

    return safe_route_call(
        _render,
        module="instances",
        action="index",
        public_error="加载实例管理页面失败",
        context={
            "search": search,
            "db_type": db_type,
            "status": status_param,
            "include_deleted": include_deleted,
            "tags_count": len(tags),
        },
    )


# ---------------------------------------------------------------------------
# 表单路由
# ---------------------------------------------------------------------------
_instance_create_view = cast(
    Callable[..., ResponseReturnValue],
    InstanceFormView.as_view("instance_create_form"),
)
_instance_create_view = login_required(create_required(require_csrf(_instance_create_view)))

instances_bp.add_url_rule(
    "/create",
    view_func=cast(RouteCallable, _instance_create_view),
    methods=["GET", "POST"],
    endpoint="create",
)

_instance_edit_view = cast(
    Callable[..., ResponseReturnValue],
    InstanceFormView.as_view("instance_edit_form"),
)
_instance_edit_view = login_required(update_required(require_csrf(_instance_edit_view)))

instances_bp.add_url_rule(
    "/<int:instance_id>/edit",
    view_func=cast(RouteCallable, _instance_edit_view),
    methods=["GET", "POST"],
    endpoint="edit",
)


# 注册额外路由模块
def _load_related_blueprints() -> None:
    """确保实例管理相关蓝图被导入注册."""
    from . import (  # noqa: F401, PLC0415
        detail,
        statistics,
    )


_load_related_blueprints()
