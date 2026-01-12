"""鲸落 - 会话中心路由."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from app.core.constants import STATUS_SYNC_OPTIONS, SYNC_CATEGORIES, SYNC_TYPES
from app.utils.decorators import view_required
from app.infra.route_safety import safe_route_call

history_sessions_bp = Blueprint("history_sessions", __name__)


@history_sessions_bp.route("/")
@login_required
@view_required
def index() -> str:
    """会话中心首页."""

    def _render() -> str:
        return render_template(
            "history/sessions/sync-sessions.html",
            sync_type_options=SYNC_TYPES,
            sync_category_options=SYNC_CATEGORIES,
            status_options=STATUS_SYNC_OPTIONS,
        )

    return safe_route_call(
        _render,
        module="history_sessions",
        action="index",
        public_error="会话中心页面加载失败",
        context={"endpoint": "history_sessions_index"},
    )
