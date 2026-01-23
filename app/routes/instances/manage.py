"""鲸落 - 数据库实例管理路由."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import STATUS_ACTIVE_OPTIONS, DatabaseType
from app.infra.route_safety import safe_route_call
from app.repositories.credentials_repository import CredentialsRepository
from app.services.common.filter_options_service import FilterOptionsService
from app.utils.database_type_utils import (
    build_database_type_select_option,
    get_database_type_color,
    get_database_type_display_name,
    get_database_type_icon,
)
from app.utils.decorators import view_required

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

    def _render() -> str:
        credentials = CredentialsRepository.list_active_credentials()
        database_type_options = [build_database_type_select_option(item) for item in DatabaseType.RELATIONAL]
        database_type_map = {
            item: {
                "display_name": get_database_type_display_name(item),
                "icon": get_database_type_icon(item),
                "color": get_database_type_color(item),
            }
            for item in DatabaseType.RELATIONAL
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


# 注册额外路由模块
def _load_related_blueprints() -> None:
    """确保实例管理相关蓝图被导入注册."""
    from . import (  # noqa: F401, PLC0415
        statistics,
    )


_load_related_blueprints()
