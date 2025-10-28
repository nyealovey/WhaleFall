"""
账户统计相关路由
"""

from flask import Response, flash, render_template, request
from flask_login import login_required

from app.errors import SystemError
from app.constants import TaskStatus
from app.models.instance import Instance
from app.routes.account import account_bp
from app.services.account_statistics_service import (
    build_aggregated_statistics,
    empty_statistics,
    fetch_classification_stats,
    fetch_db_type_stats,
    fetch_summary,
)
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error


@account_bp.route("/statistics")
@login_required
@view_required
def statistics() -> str:
    """账户统计页面"""
    try:
        stats = build_aggregated_statistics()
    except SystemError:
        stats = empty_statistics()
        flash("获取账户统计信息失败，请稍后重试", "error")

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


@account_bp.route("/api/statistics")
@login_required
@view_required
def statistics_api() -> tuple[Response, int]:
    """账户统计API"""
    try:
        summary = build_aggregated_statistics()
        return jsonify_unified_success(data={"stats": summary}, message="获取账户统计信息成功")
    except SystemError:
        raise
    except Exception as exc:  # noqa: BLE001
        log_error("获取账户统计信息失败", module="account", exception=exc)
        raise SystemError("获取账户统计信息失败") from exc


@account_bp.route("/api/statistics/summary")
@login_required
@view_required
def statistics_summary_api() -> tuple[Response, int]:
    """账户统计汇总"""
    instance_id = request.args.get("instance_id", type=int)
    db_type = request.args.get("db_type", type=str)

    summary = fetch_summary(instance_id=instance_id, db_type=db_type)
    return jsonify_unified_success(data=summary, message="获取账户统计汇总成功")


@account_bp.route("/api/statistics/db-types")
@login_required
@view_required
def statistics_db_type_api() -> tuple[Response, int]:
    """按数据库类型统计"""
    stats = fetch_db_type_stats()
    return jsonify_unified_success(data=stats, message="获取数据库类型统计成功")


@account_bp.route("/api/statistics/classifications")
@login_required
@view_required
def statistics_classification_api() -> tuple[Response, int]:
    """按分类统计"""
    stats = fetch_classification_stats()
    return jsonify_unified_success(data=stats, message="获取账户分类统计成功")
