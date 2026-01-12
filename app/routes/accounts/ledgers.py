"""Accounts 域:账户台账(Ledgers)视图与 API."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import DATABASE_TYPES
from app.services.common.filter_options_service import FilterOptionsService
from app.core.types.accounts_ledgers import AccountFilters
from app.utils.decorators import view_required
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.infra.route_safety import safe_route_call

# 创建蓝图
accounts_ledgers_bp = Blueprint("accounts_ledgers", __name__)
_filter_options_service = FilterOptionsService()


def _parse_account_filters(
    db_type_param: str | None,
    *,
    allow_query_db_type: bool = False,
) -> AccountFilters:
    args = request.args
    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=20,
        minimum=1,
        maximum=200,
    )
    search = (args.get("search") or "").strip()
    instance_id = args.get("instance_id", type=int)
    include_deleted = (args.get("include_deleted") or "").lower() == "true"
    is_locked = args.get("is_locked")
    is_superuser = args.get("is_superuser")
    plugin = (args.get("plugin", "") or "").strip()
    tags = _normalize_tags(args.getlist("tags"))
    classification_param = (args.get("classification", "") or "").strip()
    classification_filter = classification_param if classification_param not in {"", "all"} else ""
    raw_db_type = args.get("db_type") if allow_query_db_type else db_type_param
    normalized_db_type = raw_db_type if raw_db_type not in {None, "", "all"} else None

    return AccountFilters(
        page=page,
        limit=limit,
        search=search,
        instance_id=instance_id,
        include_deleted=include_deleted,
        is_locked=is_locked,
        is_superuser=is_superuser,
        plugin=plugin,
        tags=tags,
        classification=classification_param,
        classification_filter=classification_filter,
        db_type=normalized_db_type,
    )


def _normalize_tags(raw_list: list[str]) -> list[str]:
    return [tag.strip() for tag in raw_list if tag and tag.strip()]


@accounts_ledgers_bp.route("/ledgers")
@accounts_ledgers_bp.route("/ledgers/<db_type>")
@login_required
@view_required
def list_accounts(db_type: str | None = None) -> str:
    """账户列表页面."""
    filters = _parse_account_filters(db_type)

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
            db_type=filters.db_type or "all",
            current_db_type=filters.db_type,
            search=filters.search,
            selected_tags=filters.tags,
            classification=filters.classification,
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
            "db_type": filters.db_type,
            "search": filters.search,
            "tags_count": len(filters.tags),
            "classification": filters.classification_filter,
        },
    )
