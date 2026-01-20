"""账户变更历史（全量）页面路由."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import DATABASE_TYPES, TIME_RANGES
from app.infra.route_safety import safe_route_call
from app.services.common.filter_options_service import FilterOptionsService
from app.utils.decorators import view_required

history_account_change_logs_bp = Blueprint("history_account_change_logs", __name__)


@history_account_change_logs_bp.route("/")
@login_required
@view_required
def index() -> str:
    """账户变更历史页面."""

    def _render() -> str:
        search = request.args.get("search", "").strip()
        db_type = request.args.get("db_type", "").strip()
        change_type = request.args.get("change_type", "").strip()
        time_range = request.args.get("time_range", "all").strip() or "all"

        # 支持 `instance_id`(API 风格) 与 `instance`(旧筛选宏) 两种入参
        instance_id = (request.args.get("instance_id") or request.args.get("instance") or "").strip()

        db_type_options = [{"value": item["name"], "label": item["display_name"]} for item in DATABASE_TYPES]
        instance_options = FilterOptionsService().list_instance_select_options()
        change_type_options = [
            {"value": "add", "label": "新增"},
            {"value": "modify_privilege", "label": "权限变更"},
            {"value": "modify_other", "label": "属性变更"},
            {"value": "delete", "label": "删除"},
        ]
        time_range_options = [{"value": "all", "label": "全部"}, *TIME_RANGES]
        return render_template(
            "history/account_change_logs/account-change-logs.html",
            db_type_options=db_type_options,
            instance_options=instance_options,
            change_type_options=change_type_options,
            time_range_options=time_range_options,
            selected_search=search,
            selected_db_type=db_type,
            selected_instance_id=instance_id,
            selected_change_type=change_type,
            selected_time_range=time_range,
        )

    return safe_route_call(
        _render,
        module="history_account_change_logs",
        action="index",
        public_error="账户变更历史页面加载失败",
        context={"endpoint": "history_account_change_logs_index"},
    )
