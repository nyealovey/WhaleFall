"""鲸落 - 凭据管理路由."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask import Blueprint, Response, render_template, request
from flask_login import login_required

from app.constants import (
    CREDENTIAL_TYPES,
    DATABASE_TYPES,
    STATUS_ACTIVE_OPTIONS,
)
from app.services.common.filter_options_service import FilterOptionsService
from app.services.credentials.credential_detail_page_service import CredentialDetailPageService
from app.types.credentials import CredentialListFilters
from app.utils.decorators import (
    view_required,
)
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.route_safety import safe_route_call

if TYPE_CHECKING:
    from werkzeug.datastructures import MultiDict

# 创建蓝图
credentials_bp = Blueprint("credentials", __name__)
_filter_options_service = FilterOptionsService()


def _build_credential_filters(
    *,
    default_page: int,
    default_limit: int,
    allow_sort: bool,
) -> CredentialListFilters:
    """从请求参数构建筛选对象."""
    args = request.args
    page = resolve_page(args, default=default_page, minimum=1)
    limit = resolve_page_size(
        args,
        default=default_limit,
        minimum=1,
        maximum=200,
    )

    search = (args.get("search") or "").strip()
    credential_type = _normalize_filter_choice(args.get("credential_type", "", type=str))
    db_type = _normalize_filter_choice(args.get("db_type", "", type=str))
    status = _normalize_status_choice(args.get("status", "", type=str))
    tags = _extract_tags(args)

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


def _normalize_filter_choice(raw_value: str) -> str | None:
    """过滤值若为 all/空则返回 None."""
    value = (raw_value or "").strip()
    if not value or value.lower() == "all":
        return None
    return value


def _normalize_status_choice(raw_value: str) -> str | None:
    """规范化状态参数."""
    value = (raw_value or "").strip().lower()
    if value in {"active", "inactive"}:
        return value
    return None


def _extract_tags(args: MultiDict[str, str]) -> list[str]:
    """解析标签筛选."""
    return [tag.strip() for tag in args.getlist("tags") if tag and tag.strip()]


def _build_filter_options() -> dict[str, Any]:
    """构造下拉筛选选项."""
    credential_type_options = [{"value": "all", "label": "全部类型"}, *CREDENTIAL_TYPES]
    db_type_options = [
        {
            "value": item["name"],
            "label": item["display_name"],
            "icon": item.get("icon", "fa-database"),
            "color": item.get("color", "primary"),
        }
        for item in DATABASE_TYPES
    ]
    status_options = STATUS_ACTIVE_OPTIONS
    tag_options = _filter_options_service.list_active_tag_options()
    return {
        "credential_types": credential_type_options,
        "db_types": db_type_options,
        "status": status_options,
        "tags": tag_options,
    }


@credentials_bp.route("/")
@login_required
@view_required
def index() -> str | tuple[Response, int]:
    """凭据管理首页.

    渲染凭据管理页面,支持搜索、类型、数据库类型、状态和标签筛选.

    Returns:
        渲染后的 HTML 页面.

    Query Parameters:
        page: 页码,默认 1.
        limit: 每页数量,默认 10.
        search: 搜索关键词,可选.
        credential_type: 凭据类型筛选,可选.
        db_type: 数据库类型筛选,可选.
        status: 状态筛选,可选.
        tags: 标签筛选(多值),可选.

    """
    filters = _build_credential_filters(
        default_page=1,
        default_limit=10,
        allow_sort=False,
    )
    credential_type_param = request.args.get("credential_type", "", type=str)
    db_type_param = request.args.get("db_type", "", type=str)
    status_param = request.args.get("status", "", type=str)

    def _execute() -> str:
        filter_options = _build_filter_options()
        return render_template(
            "credentials/list.html",
            search=request.args.get("search", "", type=str),
            credential_type=credential_type_param,
            db_type=db_type_param,
            status=status_param,
            selected_tags=filters.tags,
            credential_type_options=filter_options["credential_types"],
            db_type_options=filter_options["db_types"],
            status_options=filter_options["status"],
            tag_options=filter_options["tags"],
        )

    return safe_route_call(
        _execute,
        module="credentials",
        action="index",
        public_error="加载凭据管理页面失败",
        context={
            "search": filters.search,
            "credential_type": filters.credential_type,
            "db_type": filters.db_type,
            "status": filters.status,
            "tags_count": len(filters.tags),
        },
    )


@credentials_bp.route("/<int:credential_id>")
@login_required
@view_required
def detail(credential_id: int) -> str:
    """查看凭据详情.

    Args:
        credential_id: 凭据 ID.

    Returns:
        str: 渲染后的详情页面.

    """

    def _render() -> str:
        context = CredentialDetailPageService().build_context(credential_id)
        return render_template("credentials/detail.html", credential=context.credential)

    return safe_route_call(
        _render,
        module="credentials",
        action="detail",
        public_error="加载凭据详情失败",
        context={"credential_id": credential_id},
    )


# ---------------------------------------------------------------------------
# 表单路由已由前端模态替代,不再暴露独立页面入口
