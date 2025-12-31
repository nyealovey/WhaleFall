"""鲸落 - 数据库实例管理路由."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from flask import Blueprint, render_template, request
from flask.typing import ResponseReturnValue, RouteCallable
from flask_login import login_required

from app.constants import (
    STATUS_ACTIVE_OPTIONS,
    DatabaseType,
)
from app.models.credential import Credential
from app.services.common.filter_options_service import FilterOptionsService
from app.utils.decorators import create_required, require_csrf, update_required, view_required
from app.views.instance_forms import InstanceFormView

# 创建蓝图
instances_bp = Blueprint("instances", __name__)
_filter_options_service = FilterOptionsService()


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

    # 获取所有可用的凭据
    credentials = Credential.query.filter_by(is_active=True).all()

    database_type_options = [DatabaseType.build_select_option(db_type) for db_type in DatabaseType.RELATIONAL]
    database_type_map = {
        db_type: {
            "display_name": DatabaseType.get_display_name(db_type),
            "icon": DatabaseType.get_icon(db_type),
            "color": DatabaseType.get_color(db_type),
        }
        for db_type in DatabaseType.RELATIONAL
    }

    tag_options = _filter_options_service.list_active_tag_options()

    return render_template(
        "instances/list.html",
        credentials=credentials,
        database_type_options=database_type_options,
        database_type_map=database_type_map,
        tag_options=tag_options,
        status_options=STATUS_ACTIVE_OPTIONS,
        search=search,
        db_type=db_type,
        status=status_param,
        include_deleted=include_deleted,
        selected_tags=tags,
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
