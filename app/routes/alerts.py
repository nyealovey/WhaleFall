"""邮件告警配置页面路由."""

from __future__ import annotations

from flask import Blueprint, render_template

from app.infra.route_safety import safe_route_call
from app.utils.decorators import admin_required

alerts_bp = Blueprint("alerts", __name__, url_prefix="/alerts")


@alerts_bp.route("/email-settings")
@admin_required
def email_settings() -> str:
    """邮件告警配置页面."""

    def _execute() -> str:
        return render_template("admin/alerts/email-settings.html")

    return safe_route_call(
        _execute,
        module="alerts",
        action="email_settings",
        public_error="加载邮件告警配置页面失败",
    )
