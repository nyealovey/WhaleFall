"""鲸落 - 标签管理路由."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import STATUS_ACTIVE_OPTIONS
from app.core.exceptions import SystemError
from app.services.common.filter_options_service import FilterOptionsService
from app.services.tags.tag_stats_service import TagStatsService
from app.utils.decorators import view_required
from app.infra.route_safety import safe_route_call

# 创建蓝图
tags_bp = Blueprint("tags", __name__)
_filter_options_service = FilterOptionsService()
_tag_stats_service = TagStatsService()


@tags_bp.route("/")
@login_required
@view_required
def index() -> str:
    """标签管理首页."""
    search = request.args.get("search", "", type=str)
    category = request.args.get("category", "", type=str)
    status_param = request.args.get("status", "all", type=str)

    def _execute() -> str:
        category_options = [{"value": "", "label": "全部分类"}, *_filter_options_service.list_tag_categories()]
        return render_template(
            "tags/index.html",
            search=search,
            category=category,
            status=status_param,
            category_options=category_options,
            status_options=STATUS_ACTIVE_OPTIONS,
            tag_stats=_tag_stats_service.get_stats(),
        )

    return safe_route_call(
        _execute,
        module="tags",
        action="index",
        public_error="加载标签管理页面失败",
        context={"search": search, "category": category, "status": status_param},
        expected_exceptions=(SystemError,),
    )
