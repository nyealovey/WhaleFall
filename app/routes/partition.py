"""分区管理路由."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from app.utils.decorators import view_required

# 创建蓝图
partition_bp = Blueprint("partition", __name__)


@partition_bp.route("/", methods=["GET"])
@login_required
@view_required
def partitions_page() -> str:
    """分区管理页面."""
    return render_template("admin/partitions/index.html")
