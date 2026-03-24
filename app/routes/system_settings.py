"""系统设置聚合页面路由."""

from __future__ import annotations

from flask import Blueprint, render_template

from app.infra.route_safety import safe_route_call
from app.utils.decorators import admin_required

system_settings_bp = Blueprint("system_settings", __name__, url_prefix="/admin")


@system_settings_bp.route("/system-settings")
@admin_required
def index() -> str:
    """系统设置聚合页面."""

    def _execute() -> str:
        return render_template("admin/system-settings/index.html")

    return safe_route_call(
        _execute,
        module="system_settings",
        action="index",
        public_error="加载系统设置页面失败",
    )
