"""Accounts 域:统计视图与 API."""

from typing import Any

from flask import Blueprint, Response, flash, render_template, request
from flask_login import login_required

from app.constants import FlashCategory
from app.errors import SystemError
from app.models.instance import Instance
from app.models.sync_session import SyncSession
from app.services.statistics.account_statistics_service import (
    build_aggregated_statistics,
    empty_statistics,
    fetch_classification_stats,
    fetch_db_type_stats,
    fetch_summary,
)
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
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


@accounts_statistics_bp.route("/api/statistics")
@login_required
@view_required
def get_account_statistics() -> tuple[Response, int]:
    """账户统计 API.

    Returns:
        (JSON 响应, HTTP 状态码),包含聚合统计数据.

    Raises:
        SystemError: 当获取统计信息失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        summary = build_aggregated_statistics()
        return jsonify_unified_success(data={"stats": summary}, message="获取账户统计信息成功")

    return safe_route_call(
        _execute,
        module="accounts_statistics",
        action="get_account_statistics",
        public_error="获取账户统计信息失败",
    )


@accounts_statistics_bp.route("/api/statistics/summary")
@login_required
@view_required
def get_account_statistics_summary() -> tuple[Response, int]:
    """账户统计汇总.

    支持按实例 ID 和数据库类型筛选.

    Returns:
        (JSON 响应, HTTP 状态码),包含统计汇总数据.

    Query Parameters:
        instance_id: 实例 ID 筛选,可选.
        db_type: 数据库类型筛选,可选.

    """
    instance_id = request.args.get("instance_id", type=int)
    db_type = request.args.get("db_type", type=str)

    summary = fetch_summary(instance_id=instance_id, db_type=db_type)
    return jsonify_unified_success(data=summary, message="获取账户统计汇总成功")


@accounts_statistics_bp.route("/api/statistics/db-types")
@login_required
@view_required
def get_account_statistics_by_db_type() -> tuple[Response, int]:
    """按数据库类型统计.

    Returns:
        (JSON 响应, HTTP 状态码),包含各数据库类型的账户统计.

    """
    stats = fetch_db_type_stats()
    return jsonify_unified_success(data=stats, message="获取数据库类型统计成功")


@accounts_statistics_bp.route("/api/statistics/classifications")
@login_required
@view_required
def get_account_statistics_by_classification() -> tuple[Response, int]:
    """按分类统计.

    Returns:
        (JSON 响应, HTTP 状态码),包含各分类的账户统计.

    """
    stats = fetch_classification_stats()
    return jsonify_unified_success(data=stats, message="获取账户分类统计成功")
