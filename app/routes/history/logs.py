"""日志路由入口.

仅保留日志中心页面(HTML)路由.
"""

from __future__ import annotations

from flask import Blueprint, render_template

from app.constants import LOG_LEVELS, TIME_RANGES
from app.services.history_logs.history_logs_extras_service import HistoryLogsExtrasService
from app.utils.decorators import admin_required
from app.infra.route_safety import safe_route_call

# 创建蓝图
history_logs_bp = Blueprint("history_logs", __name__)


@history_logs_bp.route("/")
@admin_required
def logs_dashboard() -> str | tuple[dict, int]:
    """日志中心仪表板."""

    def _render() -> str:
        module_values = HistoryLogsExtrasService().list_modules()
        module_options = [{"value": value, "label": value} for value in module_values]
        return render_template(
            "history/logs/logs.html",
            log_level_options=LOG_LEVELS,
            module_options=module_options,
            time_range_options=TIME_RANGES,
        )

    return safe_route_call(
        _render,
        module="history_logs",
        action="logs_dashboard",
        public_error="日志仪表盘加载失败",
        context={"endpoint": "logs_dashboard"},
    )
