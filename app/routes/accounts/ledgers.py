"""Accounts 域:账户台账(Ledgers)视图与 API."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import DATABASE_TYPES
from app.infra.route_safety import safe_route_call
from app.services.common.filter_options_service import FilterOptionsService
from app.utils.decorators import view_required

# 创建蓝图
accounts_ledgers_bp = Blueprint("accounts_ledgers", __name__)
_filter_options_service = FilterOptionsService()


@accounts_ledgers_bp.route("/ledgers")
@accounts_ledgers_bp.route("/ledgers/<db_type>")
@login_required
@view_required
def list_accounts(db_type: str | None = None) -> str:
    """账户列表页面."""
    search = (request.args.get("search") or "").strip()
    selected_tags = [tag.strip() for tag in request.args.getlist("tags") if tag and tag.strip()]
    classification = (request.args.get("classification") or "").strip()
    classification_filter = classification if classification not in {"", "all"} else ""
    normalized_db_type = db_type if db_type not in {None, "", "all"} else None

    def _execute() -> str:
        classification_options = [
            {"value": "all", "label": "全部分类"},
            *_filter_options_service.list_classification_options(),
        ]
        tag_options = _filter_options_service.list_active_tag_options()
        database_type_options = [
            {
                "value": item["name"],
                "label": item["display_name"],
                "icon": item.get("icon", "fa-database"),
                "color": item.get("color", "primary"),
            }
            for item in DATABASE_TYPES
        ]

        return render_template(
            "accounts/ledgers.html",
            db_type=normalized_db_type or "all",
            current_db_type=normalized_db_type,
            search=search,
            selected_tags=selected_tags,
            classification=classification,
            database_type_options=database_type_options,
            classification_options=classification_options,
            tag_options=tag_options,
        )

    return safe_route_call(
        _execute,
        module="accounts_ledgers",
        action="list_accounts",
        public_error="加载账户台账页面失败",
        context={
            "db_type": normalized_db_type,
            "search": search,
            "tags_count": len(selected_tags),
            "classification": classification_filter,
        },
    )
