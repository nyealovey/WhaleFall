"""Accounts 域:统计视图与 API."""

from flask import Blueprint, flash, render_template
from flask_login import login_required
from werkzeug.exceptions import HTTPException

from app.core.constants import FlashCategory
from app.core.exceptions import AppError, SystemError
from app.infra.route_safety import log_fallback, safe_route_call
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
        try:
            page_context = _accounts_statistics_page_service.build_context()
        except SystemError as exc:
            flash(f"获取账户统计信息失败: {exc!s}", FlashCategory.ERROR)
            log_fallback(
                "warning",
                "账户统计页面降级",
                module="accounts_statistics",
                action="statistics_page",
                fallback_reason=exc.__class__.__name__,
                context={"endpoint": "accounts_statistics_page"},
                extra={"error_type": exc.__class__.__name__, "error_message": str(exc)},
            )
            page_context = _accounts_statistics_page_service.build_fallback_context()
        except (AppError, HTTPException):
            raise
        except Exception as exc:
            flash(f"获取账户统计信息失败: {public_error}", FlashCategory.ERROR)
            log_fallback(
                "error",
                "账户统计页面降级",
                module="accounts_statistics",
                action="statistics_page",
                fallback_reason=exc.__class__.__name__,
                context={"endpoint": "accounts_statistics_page"},
                extra={"error_type": exc.__class__.__name__, "error_message": str(exc), "unexpected": True},
            )
            page_context = _accounts_statistics_page_service.build_fallback_context()

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
