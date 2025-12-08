"""数据库台账路由..

提供数据库台账页面、列表 API 以及容量趋势 API.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, render_template, request, url_for
from flask_login import login_required

from app.constants import DATABASE_TYPES
from app.errors import NotFoundError, SystemError
from app.services.ledgers.database_ledger_service import DatabaseLedgerService
from app.utils.decorators import view_required
from app.utils.query_filter_utils import get_active_tag_options
from app.utils.response_utils import jsonify_unified_error, jsonify_unified_success

databases_ledgers_bp = Blueprint("databases_ledgers", __name__)


def _build_database_type_options() -> list[dict[str, Any]]:
    """构建数据库类型选项列表.."""
    return [
        {
            "value": "all",
            "label": "全部类型",
            "icon": "fa-layer-group",
            "color": "secondary",
        },
        *[
            {
                "value": item["name"],
                "label": item["display_name"],
                "icon": item.get("icon", "fa-database"),
                "color": item.get("color", "primary"),
            }
            for item in DATABASE_TYPES
        ],
    ]


@databases_ledgers_bp.route("/ledgers")
@login_required
@view_required(permission="database_ledger.view")
def list_databases() -> str:
    """渲染数据库台账页面.."""
    current_db_type = request.args.get("db_type", "all")
    search = request.args.get("search", "").strip()
    selected_tags = _parse_tag_filters()
    capacity_stats_url = url_for("capacity_databases.list_databases")
    return render_template(
        "databases/ledgers.html",
        current_db_type=current_db_type or "all",
        search=search,
        database_type_options=_build_database_type_options(),
        capacity_stats_url=capacity_stats_url,
        tag_options=get_active_tag_options(),
        selected_tags=selected_tags,
    )


@databases_ledgers_bp.route("/api/ledgers", methods=["GET"])
@login_required
@view_required(permission="database_ledger.view")
def fetch_ledger() -> Response:
    """获取数据库台账列表数据.."""
    try:
        search = request.args.get("search", "").strip()
        db_type = request.args.get("db_type", "all")
        tags = _parse_tag_filters()
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("limit", 20, type=int)

        service = DatabaseLedgerService()
        payload = service.get_ledger(
            search=search,
            db_type=db_type,
            tags=tags,
            page=max(page, 1),
            per_page=max(per_page, 1),
        )

        return jsonify_unified_success(data=payload)
    except SystemError as exc:
        return jsonify_unified_error(exc)


@databases_ledgers_bp.route("/api/ledgers/<int:database_id>/capacity-trend", methods=["GET"])
@login_required
@view_required(permission="database_ledger.view")
def fetch_capacity_trend(database_id: int) -> Response:
    """获取单个数据库的容量走势.."""
    try:
        days = request.args.get("days", DatabaseLedgerService.DEFAULT_TREND_DAYS, type=int)
        service = DatabaseLedgerService()
        data = service.get_capacity_trend(database_id, days=days)
        return jsonify_unified_success(data=data)
    except NotFoundError as exc:
        return jsonify_unified_error(exc, status_code=404)
    except SystemError as exc:
        return jsonify_unified_error(exc)
def _parse_tag_filters() -> list[str]:
    """解析请求参数中的标签筛选值.."""
    tags = [tag.strip() for tag in request.args.getlist("tags") if tag.strip()]
    if not tags:
        raw_tags = request.args.get("tags", "")
        if raw_tags:
            tags = [item.strip() for item in raw_tags.split(",") if item.strip()]
    return tags
