"""实例容量统计页面路由."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import DATABASE_TYPES, PERIOD_TYPES
from app.infra.route_safety import safe_route_call
from app.services.common.filter_options_service import FilterOptionsService
from app.utils.decorators import view_required

# 创建蓝图
capacity_instances_bp = Blueprint("capacity_instances", __name__)
_filter_options_service = FilterOptionsService()


def _build_capacity_instance_options(raw_options: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in raw_options:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or item.get("label", "") or "").strip()
        normalized.append(
            {
                "value": str(item.get("value", "") or ""),
                "label": name,
                "name": name,
                "db_type": str(item.get("db_type", "") or ""),
                "asset_url": str(item.get("asset_url", "") or ""),
            },
        )
    return normalized


@capacity_instances_bp.route("/instances", methods=["GET"])
@login_required
@view_required
def list_instances() -> str:
    """实例统计聚合页面."""

    def _execute() -> str:
        selected_db_types = [item.strip() for item in request.args.getlist("db_type") if item and item.strip()]
        selected_instances = [item.strip() for item in request.args.getlist("instance") if item and item.strip()]
        selected_period_type = request.args.get("period_type", "daily")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")

        database_type_options = [{"value": item["name"], "label": item["display_name"]} for item in DATABASE_TYPES]

        instance_options = (
            _build_capacity_instance_options(_filter_options_service.list_instance_select_options(selected_db_types))
            if selected_db_types
            else []
        )

        return render_template(
            "capacity/instances.html",
            instance_options=instance_options,
            database_type_options=database_type_options,
            period_type_options=PERIOD_TYPES,
            db_type=selected_db_types,
            instance=selected_instances,
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
            "db_types": request.args.getlist("db_type"),
            "instances": request.args.getlist("instance"),
            "period_type": request.args.get("period_type"),
        },
    )
