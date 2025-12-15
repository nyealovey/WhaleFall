"""Accounts 域:账户台账(Ledgers)视图与 API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, Self, cast

from flask import Blueprint, Response, render_template, request
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app.constants import DATABASE_TYPES, DatabaseType
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
)
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.tag import Tag
from app.utils.decorators import view_required
from app.utils.query_filter_utils import get_active_tag_options, get_classification_options
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import log_with_context, safe_route_call
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Sequence

    from flask_sqlalchemy.pagination import Pagination

# 创建蓝图
accounts_ledgers_bp = Blueprint("accounts_ledgers", __name__)


class AccountQueryProtocol(Protocol):
    """最小化 Query 接口,便于类型标注."""

    def join(self, *args: object, **kwargs: object) -> Self:
        """执行 JOIN 操作并返回查询对象."""
        ...

    def filter(self, *args: object, **kwargs: object) -> Self:
        """应用过滤条件并返回链式查询."""
        ...

    def filter_by(self, **kwargs: object) -> Self:
        """根据关键字参数做等值过滤."""
        ...

    def order_by(self, *args: object, **kwargs: object) -> Self:
        """设置排序字段并继续返回查询对象."""
        ...

    def paginate(self, *args: object, **kwargs: object) -> Pagination:
        """按照分页参数切片查询结果."""
        ...

    def count(self) -> int:
        """统计当前查询命中的记录数."""
        ...


AccountQuery = AccountQueryProtocol


@dataclass(frozen=True)
class AccountFilters:
    """账户筛选条件集合."""

    page: int
    per_page: int
    search: str
    instance_id: int | None
    is_locked: str | None
    is_superuser: str | None
    plugin: str
    tags: list[str]
    classification: str
    classification_filter: str
    db_type: str | None


@dataclass(frozen=True)
class AccountsResponseContext:
    """账户列表 JSON 响应所需的上下文数据."""

    pagination: Pagination
    stats: dict[str, int]
    instances: Sequence[Instance]
    database_type_options: list[dict[str, Any]]
    classification_options: list[dict[str, str]]
    tag_options: list[dict[str, Any]]


@dataclass(frozen=True)
class PaginatedAccounts:
    """封装账户分页结果及分类映射."""

    filters: AccountFilters
    pagination: Pagination
    classifications: dict[int, list[dict[str, str]]]


def _parse_account_filters(
    db_type_param: str | None,
    *,
    per_page_param: str = "per_page",
    allow_query_db_type: bool = False,
) -> AccountFilters:
    args = request.args
    page = args.get("page", 1, type=int)
    per_page = args.get(per_page_param, 20, type=int)
    search = (args.get("search", "") or "").strip()
    instance_id = args.get("instance_id", type=int)
    is_locked = args.get("is_locked")
    is_superuser = args.get("is_superuser")
    plugin = (args.get("plugin", "") or "").strip()
    tags = _normalize_tags(args.getlist("tags"), args.get("tags", ""))
    classification_param = (args.get("classification", "") or "").strip()
    classification_filter = classification_param if classification_param not in {"", "all"} else ""
    raw_db_type = args.get("db_type") if allow_query_db_type else db_type_param
    normalized_db_type = raw_db_type if raw_db_type not in {None, "", "all"} else None

    return AccountFilters(
        page=page,
        per_page=per_page,
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


def _normalize_tags(raw_list: list[str], raw_string: str) -> list[str]:
    tags = [tag.strip() for tag in raw_list if tag and tag.strip()]
    if tags:
        return tags
    fallback = (raw_string or "").strip()
    if not fallback:
        return []
    return [tag.strip() for tag in fallback.split(",") if tag.strip()]


def _build_account_query(filters: AccountFilters) -> AccountQuery:
    base_query = cast("AccountQuery", AccountPermission.query)
    relationship_clause = cast("Any", AccountPermission.instance_account)
    query = base_query.join(InstanceAccount, relationship_clause)
    query = query.filter(InstanceAccount.is_active.is_(True))

    if filters.db_type:
        query = query.filter(AccountPermission.db_type == filters.db_type)
    if filters.instance_id:
        query = query.filter(AccountPermission.instance_id == filters.instance_id)

    query = _apply_search_filter(query, filters.search)
    query = _apply_lock_filters(query, filters.is_locked, filters.is_superuser)
    query = _apply_tag_filter(query, filters.tags)
    return _apply_classification_filter(query, filters.classification_filter)


def _apply_search_filter(query: AccountQuery, search: str) -> AccountQuery:
    if not search:
        return query
    query = query.join(Instance, AccountPermission.instance_id == Instance.id)
    username_column = cast("Any", AccountPermission.username)
    instance_name_column = cast("Any", Instance.name)
    instance_host_column = cast("Any", Instance.host)
    return query.filter(
        or_(
            username_column.contains(search),
            instance_name_column.contains(search),
            instance_host_column.contains(search),
        ),
    )


def _apply_lock_filters(
    query: AccountQuery,
    is_locked: str | None,
    is_superuser: str | None,
) -> AccountQuery:
    if is_locked == "true":
        query = query.filter(AccountPermission.is_locked.is_(True))
    elif is_locked == "false":
        query = query.filter(AccountPermission.is_locked.is_(False))

    if is_superuser in {"true", "false"}:
        query = query.filter(AccountPermission.is_superuser == (is_superuser == "true"))
    return query


def _apply_tag_filter(query: AccountQuery, tags: list[str]) -> AccountQuery:
    if not tags:
        return query
    try:
        tag_relationship = cast("Any", Instance.tags)
        tag_name_column = cast("Any", Tag.name)
        return query.join(Instance).join(tag_relationship).filter(tag_name_column.in_(tags))
    except SQLAlchemyError as exc:  # pragma: no cover - 日志用于排查
        log_with_context(
            "warning",
            "标签过滤失败",
            module="accounts_ledgers",
            action="_apply_tag_filter",
            context={"tags": tags},
            extra={"error_message": str(exc)},
            include_actor=False,
        )
        return query


def _apply_classification_filter(query: AccountQuery, classification_filter: str) -> AccountQuery:
    if not classification_filter:
        return query
    try:
        classification_id = int(classification_filter)
    except (ValueError, TypeError) as exc:
        log_with_context(
            "warning",
            "分类ID转换失败",
            module="accounts_ledgers",
            action="_apply_classification_filter",
            context={"classification": classification_filter},
            extra={"error_message": str(exc)},
            include_actor=False,
        )
        return query

    assignment_join = query.join(AccountClassificationAssignment)
    classification_join = assignment_join.join(AccountClassification)
    return classification_join.filter(
        AccountClassification.id == classification_id,
        AccountClassificationAssignment.is_active.is_(True),
    )


def _calculate_account_stats() -> dict[str, int]:
    base_query = cast("AccountQuery", AccountPermission.query)
    relationship_clause = cast("Any", AccountPermission.instance_account)
    base_query = base_query.join(InstanceAccount, relationship_clause)
    base_query = base_query.filter(InstanceAccount.is_active.is_(True))
    return {
        "total": base_query.count(),
        "mysql": base_query.filter(AccountPermission.db_type == "mysql").count(),
        "postgresql": base_query.filter(AccountPermission.db_type == "postgresql").count(),
        "oracle": base_query.filter(AccountPermission.db_type == "oracle").count(),
        "sqlserver": base_query.filter(AccountPermission.db_type == "sqlserver").count(),
    }


def _build_filter_options() -> tuple[list[Instance], list[dict[str, str]], list[dict[str, str]], list[dict[str, Any]]]:
    instances = Instance.query.filter_by(is_active=True).all()
    classification_options = [{"value": "all", "label": "全部分类"}, *get_classification_options()]
    tag_options = get_active_tag_options()
    database_type_options = [
        {
            "value": item["name"],
            "label": item["display_name"],
            "icon": item.get("icon", "fa-database"),
            "color": item.get("color", "primary"),
        }
        for item in DATABASE_TYPES
    ]
    return instances, classification_options, tag_options, database_type_options


def _fetch_account_classifications(accounts: Sequence[AccountPermission]) -> dict[int, list[dict[str, str]]]:
    if not accounts:
        return {}

    account_ids = [account.id for account in accounts]
    assignments = AccountClassificationAssignment.query.filter(
        AccountClassificationAssignment.account_id.in_(account_ids),
        AccountClassificationAssignment.is_active.is_(True),
    ).all()

    classifications: dict[int, list[dict[str, str]]] = {}
    for assignment in assignments:
        classifications.setdefault(assignment.account_id, []).append(
            {
                "name": assignment.classification.name,
                "color": assignment.classification.color_value,
            },
        )
    return classifications


def _build_accounts_json_response(context: AccountsResponseContext) -> tuple[Response, int]:
    pagination = context.pagination
    return jsonify_unified_success(
        data={
            "accounts": [account.to_dict() for account in pagination.items],
            "pagination": {
                "page": pagination.page,
                "pages": pagination.pages,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
            "stats": context.stats,
            "instances": [instance.to_dict() for instance in context.instances],
            "filter_options": {
                "db_types": context.database_type_options,
                "classifications": context.classification_options,
                "tags": context.tag_options,
            },
        },
        message="获取账户列表成功",
    )


def _build_paginated_accounts(
    filters: AccountFilters,
    *,
    sort_field: str,
    sort_order: str,
) -> PaginatedAccounts:
    """根据筛选与排序参数构建分页账户结果."""
    query = _apply_sorting(_build_account_query(filters), sort_field, sort_order)
    pagination = query.paginate(page=filters.page, per_page=filters.per_page, error_out=False)
    classifications = _fetch_account_classifications(pagination.items)
    return PaginatedAccounts(filters=filters, pagination=pagination, classifications=classifications)


def _apply_sorting(query: AccountQuery, sort_field: str, sort_order: str) -> AccountQuery:
    sortable_fields = {
        "username": AccountPermission.username,
        "db_type": AccountPermission.db_type,
        "is_locked": AccountPermission.is_locked,
        "is_superuser": AccountPermission.is_superuser,
    }
    order_column = sortable_fields.get(sort_field, AccountPermission.username)
    return query.order_by(order_column.desc() if sort_order == "desc" else order_column.asc())


def _serialize_account_row(account: AccountPermission, classifications: list[dict[str, str]]) -> dict[str, Any]:
    instance = account.instance
    instance_account = account.instance_account
    is_active = bool(instance_account.is_active) if instance_account else True
    item_tags: list[dict[str, str]] = []
    if instance and instance.tags:
        tags_iterable = instance.tags.all() if hasattr(instance.tags, "all") else instance.tags
        item_tags = [
            {
                "name": tag.name,
                "display_name": tag.display_name,
                "color": tag.color,
            }
            for tag in tags_iterable
        ]

    return {
        "id": account.id,
        "username": account.username,
        "instance_name": instance.name if instance else "未知实例",
        "instance_host": instance.host if instance else "未知主机",
        "db_type": account.db_type,
        "is_locked": account.is_locked,
        "is_superuser": account.is_superuser,
        "is_active": is_active,
        "is_deleted": not is_active,
        "tags": item_tags,
        "classifications": classifications,
    }


@accounts_ledgers_bp.route("/ledgers")
@accounts_ledgers_bp.route("/ledgers/<db_type>")
@login_required
@view_required
def list_accounts(db_type: str | None = None) -> str | Response | tuple[Response, int]:
    """账户列表页面."""
    filters = _parse_account_filters(db_type)
    paginated = _build_paginated_accounts(filters, sort_field="username", sort_order="asc")
    (
        instances,
        classification_options,
        tag_options,
        database_type_options,
    ) = _build_filter_options()
    stats = _calculate_account_stats()

    if request.is_json:
        context = AccountsResponseContext(
            pagination=paginated.pagination,
            stats=stats,
            instances=instances,
            database_type_options=database_type_options,
            classification_options=classification_options,
            tag_options=tag_options,
        )
        return _build_accounts_json_response(context)

    persist_query_args = request.args.to_dict(flat=False)
    persist_query_args.pop("page", None)
    filters = paginated.filters

    return render_template(
        "accounts/ledgers.html",
        accounts=paginated.pagination,
        pagination=paginated.pagination,
        db_type=filters.db_type or "all",
        current_db_type=filters.db_type,
        search=filters.search,
        instance_id=filters.instance_id,
        is_locked=filters.is_locked,
        is_superuser=filters.is_superuser,
        plugin=filters.plugin,
        selected_tags=filters.tags,
        classification=filters.classification,
        instances=instances,
        stats=stats,
        database_type_options=database_type_options,
        classification_options=classification_options,
        tag_options=tag_options,
        classifications=paginated.classifications,
        persist_query_args=persist_query_args,
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
        account = AccountPermission.query.get_or_404(account_id)
        instance = account.instance

        permissions = {
            "db_type": instance.db_type.upper() if instance else "",
            "username": account.username,
            "is_superuser": account.is_superuser,
            "last_sync_time": (
                time_utils.format_china_time(account.last_sync_time) if account.last_sync_time else "未知"
            ),
        }

        if instance and instance.db_type == DatabaseType.MYSQL:
            permissions["global_privileges"] = account.global_privileges or []
            permissions["database_privileges"] = account.database_privileges or {}
        elif instance and instance.db_type == DatabaseType.POSTGRESQL:
            permissions["predefined_roles"] = account.predefined_roles or []
            permissions["role_attributes"] = account.role_attributes or {}
            permissions["database_privileges_pg"] = account.database_privileges_pg or {}
            permissions["tablespace_privileges"] = account.tablespace_privileges or {}
        elif instance and instance.db_type == DatabaseType.SQLSERVER:
            permissions["server_roles"] = account.server_roles or []
            permissions["server_permissions"] = account.server_permissions or []
            permissions["database_roles"] = account.database_roles or {}
            raw_db_perms = account.database_permissions or {}
            simplified_db_perms: dict[str, list[str]] = {}
            if isinstance(raw_db_perms, dict):
                for db_name, entry in raw_db_perms.items():
                    if not isinstance(entry, dict):
                        continue
                    db_perm_list: list[str] = []
                    db_level = entry.get("database")
                    if isinstance(db_level, list):
                        db_perm_list.extend([p for p in db_level if isinstance(p, str)])
                    simplified_db_perms[db_name] = db_perm_list
            permissions["database_permissions"] = simplified_db_perms
        elif instance and instance.db_type == DatabaseType.ORACLE:
            permissions["oracle_roles"] = account.oracle_roles or []
            permissions["system_privileges"] = account.system_privileges or []
            permissions["tablespace_privileges_oracle"] = account.tablespace_privileges_oracle or {}

        return jsonify_unified_success(
            data={
                "permissions": permissions,
                "account": {
                    "id": account.id,
                    "username": account.username,
                    "instance_name": instance.name if instance else "未知实例",
                    "db_type": instance.db_type if instance else "",
                },
            },
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
    filters = _parse_account_filters(
        None,
        per_page_param="limit",
        allow_query_db_type=True,
    )
    sort_field = request.args.get("sort", "username")
    sort_order = (request.args.get("order", "asc") or "asc").lower()
    search_override = (request.args.get("search") or request.args.get("q") or "").strip()
    if search_override and search_override != filters.search:
        filters = AccountFilters(
            page=filters.page,
            per_page=filters.per_page,
            search=search_override,
            instance_id=filters.instance_id,
            is_locked=filters.is_locked,
            is_superuser=filters.is_superuser,
            plugin=filters.plugin,
            tags=filters.tags,
            classification=filters.classification,
            classification_filter=filters.classification_filter,
            db_type=filters.db_type,
        )

    paginated = _build_paginated_accounts(filters, sort_field=sort_field, sort_order=sort_order)
    pagination = paginated.pagination
    items = [
        _serialize_account_row(
            account,
            paginated.classifications.get(account.id, []),
        )
        for account in pagination.items
    ]

    payload = {
        "items": items,
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "limit": pagination.per_page,
    }

    return jsonify_unified_success(data=payload, message="获取账户列表成功")
