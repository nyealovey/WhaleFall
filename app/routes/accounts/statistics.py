"""Accounts 域:统计视图与 API."""

from typing import Any

from flask import Blueprint, flash, render_template
from flask_login import login_required

from app.constants import FlashCategory
from app.errors import SystemError
from app.services.statistics.accounts_statistics_page_service import AccountsStatisticsPageService
from app.utils.decorators import view_required
from app.utils.route_safety import safe_route_call

accounts_statistics_bp = Blueprint("accounts_statistics", __name__)
_accounts_statistics_page_service = AccountsStatisticsPageService()


def _render_statistics_page(context: dict[str, Any]) -> str:
    """统一渲染统计模板."""
    return render_template(
        "accounts/statistics.html",
        stats=context["stats"],
        recent_syncs=context["recent_syncs"],
        recent_accounts=context["recent_accounts"],
        instances=context["instances"],
    )


@accounts_statistics_bp.route("/statistics")
@login_required
@view_required
def statistics() -> str:
    """账户统计页面.

    Returns:
        渲染的账户统计页面,包含统计数据、最近同步记录和活跃实例列表.

    """

    def _render() -> str:
        page_context = _accounts_statistics_page_service.build_context()
        context = {
            "stats": page_context.stats,
            "recent_syncs": page_context.recent_syncs,
            "recent_accounts": page_context.recent_accounts,
            "instances": page_context.instances,
        }
        return _render_statistics_page(context)

    try:
        return safe_route_call(
            _render,
            module="accounts_statistics",
            action="statistics_page",
            public_error="加载账户统计页面失败",
        )
    except SystemError as exc:
        flash(f"获取账户统计信息失败: {exc!s}", FlashCategory.ERROR)
        fallback_context = _accounts_statistics_page_service.build_fallback_context()
        context = {
            "stats": fallback_context.stats,
            "recent_syncs": fallback_context.recent_syncs,
            "recent_accounts": fallback_context.recent_accounts,
            "instances": fallback_context.instances,
        }
        return _render_statistics_page(context)
