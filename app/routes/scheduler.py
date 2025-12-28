"""定时任务管理路由."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from app.utils.decorators import scheduler_view_required

# 创建蓝图
scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.route("/")
@login_required
@scheduler_view_required
def index() -> str:
    """定时任务管理页面."""
    return render_template("admin/scheduler/index.html")
