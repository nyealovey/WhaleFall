"""分区管理路由."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from app.infra.route_safety import safe_route_call
from app.utils.decorators import view_required

# 创建蓝图
partition_bp = Blueprint("partition", __name__)


@partition_bp.route("/", methods=["GET"])
@login_required
@view_required
def partitions_page() -> str:
    """分区管理页面."""
    return safe_route_call(
        lambda: render_template("admin/partitions/index.html"),
        module="partition",
        action="partitions_page",
        public_error="加载分区管理页面失败",
    )
