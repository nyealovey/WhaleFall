"""定时任务管理路由."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from app.utils.decorators import scheduler_view_required
from app.infra.route_safety import safe_route_call

# 创建蓝图
scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.route("/")
@login_required
@scheduler_view_required
def index() -> str:
    """定时任务管理页面."""
    return safe_route_call(
        lambda: render_template("admin/scheduler/index.html"),
        module="scheduler",
        action="index",
        public_error="加载定时任务管理页面失败",
    )
