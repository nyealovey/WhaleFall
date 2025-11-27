"""账户统计相关路由"""

from flask import Blueprint, Response, flash, render_template, request
from flask_login import login_required

from app.errors import SystemError
from app.constants import FlashCategory
from app.models.instance import Instance
from app.services.statistics.account_statistics_service import (
    build_aggregated_statistics,
    empty_statistics,
    fetch_classification_stats,
    fetch_db_type_stats,
    fetch_summary,
)
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error


account_stat_bp = Blueprint("account_stat", __name__)


@account_stat_bp.route("/statistics")
@login_required
@view_required
def statistics() -> str:
    """账户统计页面。

    Returns:
        渲染的账户统计页面，包含统计数据、最近同步记录和活跃实例列表。
    """
    try:
        stats = build_aggregated_statistics()
    except SystemError:
        stats = empty_statistics()
        flash("获取账户统计信息失败，请稍后重试", FlashCategory.ERROR)

    from app.models.sync_session import SyncSession

    recent_syncs = SyncSession.query.order_by(SyncSession.created_at.desc()).limit(10).all()
    instances = Instance.query.filter_by(is_active=True).all()

    return render_template(
        "accounts/statistics.html",
        stats=stats,
        recent_syncs=recent_syncs,
        recent_accounts=stats.get("recent_accounts", []),
        instances=instances,
    )


@account_stat_bp.route("/api/statistics")
@login_required
@view_required
def get_account_statistics() -> tuple[Response, int]:
    """账户统计 API。

    Returns:
        (JSON 响应, HTTP 状态码)，包含聚合统计数据。

    Raises:
        SystemError: 当获取统计信息失败时抛出。
    """
    try:
        summary = build_aggregated_statistics()
        return jsonify_unified_success(data={"stats": summary}, message="获取账户统计信息成功")
    except SystemError:
        raise
    except Exception as exc:  # noqa: BLE001
        log_error("获取账户统计信息失败", module="account", exception=exc)
        raise SystemError("获取账户统计信息失败") from exc


@account_stat_bp.route("/api/statistics/summary")
@login_required
@view_required
def get_account_statistics_summary() -> tuple[Response, int]:
    """账户统计汇总。

    支持按实例 ID 和数据库类型筛选。

    Returns:
        (JSON 响应, HTTP 状态码)，包含统计汇总数据。

    Query Parameters:
        instance_id: 实例 ID 筛选，可选。
        db_type: 数据库类型筛选，可选。
    """
    instance_id = request.args.get("instance_id", type=int)
    db_type = request.args.get("db_type", type=str)

    summary = fetch_summary(instance_id=instance_id, db_type=db_type)
    return jsonify_unified_success(data=summary, message="获取账户统计汇总成功")


@account_stat_bp.route("/api/statistics/db-types")
@login_required
@view_required
def get_account_statistics_by_db_type() -> tuple[Response, int]:
    """按数据库类型统计。

    Returns:
        (JSON 响应, HTTP 状态码)，包含各数据库类型的账户统计。
    """
    stats = fetch_db_type_stats()
    return jsonify_unified_success(data=stats, message="获取数据库类型统计成功")


@account_stat_bp.route("/api/statistics/classifications")
@login_required
@view_required
def get_account_statistics_by_classification() -> tuple[Response, int]:
    """按分类统计。

    Returns:
        (JSON 响应, HTTP 状态码)，包含各分类的账户统计。
    """
    stats = fetch_classification_stats()
    return jsonify_unified_success(data=stats, message="获取账户分类统计成功")
