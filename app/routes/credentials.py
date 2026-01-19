"""鲸落 - 凭据管理路由."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import (
    CREDENTIAL_TYPES,
    DATABASE_TYPES,
    STATUS_ACTIVE_OPTIONS,
)
from app.infra.route_safety import safe_route_call
from app.services.common.filter_options_service import FilterOptionsService
from app.services.credentials.credential_detail_read_service import CredentialDetailReadService
from app.utils.decorators import (
    view_required,
)

# 创建蓝图
credentials_bp = Blueprint("credentials", __name__)
_filter_options_service = FilterOptionsService()


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
def index() -> str:
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
    search_param = request.args.get("search", "", type=str)
    credential_type_param = request.args.get("credential_type", "", type=str)
    db_type_param = request.args.get("db_type", "", type=str)
    status_param = request.args.get("status", "", type=str)
    selected_tags = [tag.strip() for tag in request.args.getlist("tags") if tag and tag.strip()]

    def _execute() -> str:
        filter_options = _build_filter_options()
        return render_template(
            "credentials/list.html",
            search=search_param,
            credential_type=credential_type_param,
            db_type=db_type_param,
            status=status_param,
            selected_tags=selected_tags,
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
            "search": search_param,
            "credential_type": credential_type_param,
            "db_type": db_type_param,
            "status": status_param,
            "tags_count": len(selected_tags),
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
        credential = CredentialDetailReadService().get_credential_or_error(credential_id)
        return render_template("credentials/detail.html", credential=credential)

    return safe_route_call(
        _render,
        module="credentials",
        action="detail",
        public_error="加载凭据详情失败",
        context={"credential_id": credential_id},
    )


# ---------------------------------------------------------------------------
# 表单路由已由前端模态替代,不再暴露独立页面入口
