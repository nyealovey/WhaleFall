"""
实例容量与统计相关接口
"""

from flask import Response, flash, render_template
from flask_login import login_required

from app.errors import SystemError
from app.constants import FlashCategory
from app.routes.instance import instance_bp
from app.services.statistics.instance_statistics_service import (
    build_aggregated_statistics as build_instance_statistics,
    empty_statistics as empty_instance_statistics,
)
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success


@instance_bp.route("/statistics")
@login_required
@view_required
def statistics() -> str:
    """实例统计页面。

    Returns:
        str: 渲染后的统计页面。
    """
    try:
        stats = build_instance_statistics()
    except SystemError:
        stats = empty_instance_statistics()
        flash("获取实例统计信息失败，请稍后重试", FlashCategory.ERROR)
    return render_template("instances/statistics.html", stats=stats)


@instance_bp.route("/api/statistics")
@login_required
@view_required
def api_statistics() -> Response:
    """获取实例统计 API。

    Returns:
        Response: 包含统计数据的 JSON。
    """
    stats = build_instance_statistics()
    return jsonify_unified_success(data=stats, message="获取实例统计信息成功")
