"""实例容量统计页面路由."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import DATABASE_TYPES, PERIOD_TYPES
from app.services.common.filter_options_service import FilterOptionsService
from app.utils.decorators import view_required
from app.infra.route_safety import safe_route_call

# 创建蓝图
capacity_instances_bp = Blueprint("capacity_instances", __name__)
_filter_options_service = FilterOptionsService()


@capacity_instances_bp.route("/instances", methods=["GET"])
@login_required
@view_required
def list_instances() -> str:
    """实例统计聚合页面."""
    def _execute() -> str:
        selected_db_type = request.args.get("db_type", "")
        selected_instance = request.args.get("instance", "")
        selected_period_type = request.args.get("period_type", "daily")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")

        database_type_options = [{"value": item["name"], "label": item["display_name"]} for item in DATABASE_TYPES]

        instance_options = (
            _filter_options_service.list_instance_select_options(selected_db_type or None) if selected_db_type else []
        )

        return render_template(
            "capacity/instances.html",
            instance_options=instance_options,
            database_type_options=database_type_options,
            period_type_options=PERIOD_TYPES,
            db_type=selected_db_type,
            instance=selected_instance,
            period_type=selected_period_type,
            start_date=start_date,
            end_date=end_date,
        )

    return safe_route_call(
        _execute,
        module="capacity_instances",
        action="list_instances",
        public_error="加载实例容量统计页面失败",
        context={
            "db_type": request.args.get("db_type"),
            "instance": request.args.get("instance"),
            "period_type": request.args.get("period_type"),
        },
    )
