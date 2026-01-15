"""数据库容量统计页面路由."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import PERIOD_TYPES
from app.infra.route_safety import safe_route_call
from app.services.capacity.capacity_databases_page_service import CapacityDatabasesPageService
from app.utils.decorators import view_required

# 创建蓝图
capacity_databases_bp = Blueprint("capacity_databases", __name__)
_capacity_databases_page_service = CapacityDatabasesPageService()


@capacity_databases_bp.route("/databases", methods=["GET"])
@login_required
@view_required
def list_databases() -> str:
    """数据库统计聚合页面(数据库统计层面)."""
    selected_db_type = request.args.get("db_type", "")
    selected_instance = request.args.get("instance", "")
    selected_database_id = request.args.get("database_id", "")
    selected_database = request.args.get("database", "")
    selected_period_type = request.args.get("period_type", "daily")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    def _execute() -> str:
        page_context = _capacity_databases_page_service.build_context(
            db_type=selected_db_type,
            instance=selected_instance,
            database_id=selected_database_id,
            database=selected_database,
        )
        return render_template(
            "capacity/databases.html",
            database_type_options=page_context.database_type_options,
            instance_options=page_context.instance_options,
            database_options=page_context.database_options,
            period_type_options=PERIOD_TYPES,
            db_type=page_context.db_type,
            instance=page_context.instance,
            database_id=page_context.database_id,
            database=page_context.database,
            period_type=selected_period_type,
            start_date=start_date,
            end_date=end_date,
        )

    return safe_route_call(
        _execute,
        module="capacity_databases",
        action="list_databases",
        public_error="加载数据库容量统计页面失败",
        context={
            "db_type": selected_db_type,
            "instance": selected_instance,
            "database_id": selected_database_id,
            "has_database_name": bool(selected_database),
            "period_type": selected_period_type,
        },
    )
