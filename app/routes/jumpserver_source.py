"""JumpServer 数据源页面路由."""

from __future__ import annotations

from flask import Blueprint, render_template

from app.infra.route_safety import safe_route_call
from app.utils.decorators import admin_required

jumpserver_source_bp = Blueprint("jumpserver_source", __name__, url_prefix="/integrations/jumpserver")


@jumpserver_source_bp.route("/source")
@admin_required
def source_settings() -> str:
    """JumpServer 数据源页面."""

    def _execute() -> str:
        return render_template("integrations/jumpserver/source.html")

    return safe_route_call(
        _execute,
        module="jumpserver",
        action="source_settings",
        public_error="加载 JumpServer 数据源页面失败",
    )
