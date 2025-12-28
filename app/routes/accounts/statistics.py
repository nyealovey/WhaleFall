"""Accounts 域:统计视图与 API."""

from typing import Any

from flask import Blueprint, flash, render_template
from flask_login import login_required

from app.constants import FlashCategory
from app.errors import SystemError
from app.models.instance import Instance
from app.models.sync_session import SyncSession
from app.services.statistics.account_statistics_service import (
    build_aggregated_statistics,
    empty_statistics,
)
from app.utils.decorators import view_required
from app.utils.route_safety import safe_route_call

accounts_statistics_bp = Blueprint("accounts_statistics", __name__)


def _fetch_active_instances() -> list[Instance]:
    """加载所有活跃实例."""
    return Instance.query.filter_by(is_active=True).all()


def _fetch_recent_syncs(limit: int = 10) -> list[SyncSession]:
    """查询最近的同步会话."""
    return SyncSession.query.order_by(SyncSession.created_at.desc()).limit(limit).all()


def _build_statistics_context(stats: dict[str, Any]) -> dict[str, Any]:
    """构造渲染模板所需的上下文."""
    return {
        "stats": stats,
        "recent_syncs": _fetch_recent_syncs(),
        "recent_accounts": stats.get("recent_accounts", []),
        "instances": _fetch_active_instances(),
    }


def _build_fallback_statistics_context() -> dict[str, Any]:
    """构造失败时的兜底上下文."""
    return {
        "stats": empty_statistics(),
        "recent_syncs": [],
        "recent_accounts": [],
        "instances": _fetch_active_instances(),
    }


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
        stats = build_aggregated_statistics()
        context = _build_statistics_context(stats)
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
        context = _build_fallback_statistics_context()
        return _render_statistics_page(context)
