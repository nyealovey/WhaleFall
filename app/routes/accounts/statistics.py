"""Accounts 域:统计视图与 API."""

from flask import Blueprint, render_template
from flask_login import login_required

from app.infra.route_safety import safe_route_call
from app.services.statistics.accounts_statistics_page_service import AccountsStatisticsPageService
from app.utils.decorators import view_required

accounts_statistics_bp = Blueprint("accounts_statistics", __name__)
_accounts_statistics_page_service = AccountsStatisticsPageService()


@accounts_statistics_bp.route("/statistics")
@login_required
@view_required
def statistics() -> str:
    """账户统计页面.

    Returns:
        渲染的账户统计页面,包含统计数据、最近同步记录和活跃实例列表.

    """
    public_error = "加载账户统计页面失败"

    def _execute() -> str:
        page_context = _accounts_statistics_page_service.build_context()
        return render_template(
            "accounts/statistics.html",
            stats=page_context.stats,
            recent_syncs=page_context.recent_syncs,
            recent_accounts=page_context.recent_accounts,
            instances=page_context.instances,
        )

    return safe_route_call(
        _execute,
        module="accounts_statistics",
        action="statistics_page",
        public_error=public_error,
    )
