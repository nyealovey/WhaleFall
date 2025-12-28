"""数据库台账路由.

仅保留数据库台账页面(HTML)路由.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, render_template, request, url_for
from flask_login import login_required

from app.constants import DATABASE_TYPES
from app.services.common.filter_options_service import FilterOptionsService
from app.utils.decorators import view_required

databases_ledgers_bp = Blueprint("databases_ledgers", __name__)
_filter_options_service = FilterOptionsService()


def _build_database_type_options() -> list[dict[str, Any]]:
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


def _parse_tag_filters() -> list[str]:
    return [tag.strip() for tag in request.args.getlist("tags") if tag.strip()]


@databases_ledgers_bp.route("/ledgers")
@login_required
@view_required(permission="database_ledger.view")
def list_databases() -> str:
    """渲染数据库台账页面."""
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
        tag_options=_filter_options_service.list_active_tag_options(),
        selected_tags=selected_tags,
    )
