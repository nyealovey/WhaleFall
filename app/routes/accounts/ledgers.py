"""Accounts 域:账户台账(Ledgers)视图与 API."""

from __future__ import annotations

from flask import Blueprint, Response, render_template, request
from flask_login import login_required
from flask_restx import marshal

from app.constants import DATABASE_TYPES
from app.routes.accounts.restx_models import ACCOUNT_LEDGER_ITEM_FIELDS, ACCOUNT_LEDGER_PERMISSIONS_RESPONSE_FIELDS
from app.services.common.filter_options_service import FilterOptionsService
from app.services.ledgers.accounts_ledger_permissions_service import AccountsLedgerPermissionsService
from app.services.ledgers.accounts_ledger_list_service import AccountsLedgerListService
from app.types.accounts_ledgers import AccountFilters
from app.utils.decorators import view_required
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call

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
        module="accounts_ledgers",
        action="list_accounts_data",
    )
    search = (args.get("search") or "").strip()
    instance_id = args.get("instance_id", type=int)
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


@accounts_ledgers_bp.route("/api/ledgers/<int:account_id>/permissions")
@login_required
@view_required
def get_account_permissions(account_id: int) -> tuple[Response, int]:
    """获取账户权限详情.

    Args:
        account_id: 账户权限记录 ID.

    Returns:
        (payload, status_code) 的元组,成功时包含权限详情.

    """

    def _load_permissions() -> tuple[Response, int]:
        result = AccountsLedgerPermissionsService().get_permissions(account_id)
        payload = marshal(result, ACCOUNT_LEDGER_PERMISSIONS_RESPONSE_FIELDS, skip_none=True)
        return jsonify_unified_success(
            data=payload,
            message="获取账户权限成功",
        )

    return safe_route_call(
        _load_permissions,
        module="accounts_ledgers",
        action="get_account_permissions",
        public_error="获取账户权限失败",
        context={"account_id": account_id},
    )


@accounts_ledgers_bp.route("/api/ledgers", methods=["GET"])
@login_required
@view_required
def list_accounts_data() -> tuple[Response, int]:
    """Grid.js 账户列表 API."""
    filters = _parse_account_filters(None, allow_query_db_type=True)
    sort_field = request.args.get("sort", "username")
    sort_order = (request.args.get("order", "asc") or "asc").lower()

    def _execute() -> tuple[Response, int]:
        result = AccountsLedgerListService().list_accounts(filters, sort_field=sort_field, sort_order=sort_order)
        items = marshal(result.items, ACCOUNT_LEDGER_ITEM_FIELDS)
        payload = {
            "items": items,
            "total": result.total,
            "page": result.page,
            "pages": result.pages,
            "limit": result.limit,
        }
        return jsonify_unified_success(data=payload, message="获取账户列表成功")

    return safe_route_call(
        _execute,
        module="accounts_ledgers",
        action="list_accounts_data",
        public_error="获取账户列表失败",
        context={
            "search": filters.search,
            "db_type": filters.db_type,
            "instance_id": filters.instance_id,
            "is_locked": filters.is_locked,
            "is_superuser": filters.is_superuser,
            "tags_count": len(filters.tags),
            "classification": filters.classification_filter,
            "page": filters.page,
            "page_size": filters.limit,
            "sort": sort_field,
            "order": sort_order,
        },
    )
