"""实例详情相关接口.

提供实例详情页面、账户历史及容量统计等 API.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any, cast

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required
from flask_restx import marshal

from app import db
from app.errors import ConflictError, ValidationError
from app.models.credential import Credential
from app.models.instance import Instance
from app.services.instances.instance_accounts_service import InstanceAccountsService
from app.services.instances.instance_database_sizes_service import InstanceDatabaseSizesService
from app.services.instances.instance_detail_page_service import InstanceDetailPageService
from app.types.instance_accounts import InstanceAccountListFilters
from app.types.instance_database_sizes import InstanceDatabaseSizesQuery
from app.routes.instances.restx_models import (
    INSTANCE_ACCOUNT_CHANGE_HISTORY_RESPONSE_FIELDS,
    INSTANCE_ACCOUNT_LIST_ITEM_FIELDS,
    INSTANCE_ACCOUNT_PERMISSIONS_RESPONSE_FIELDS,
    INSTANCE_ACCOUNT_SUMMARY_FIELDS,
    INSTANCE_DATABASE_SIZE_ENTRY_FIELDS,
)
from app.utils.data_validator import DataValidator
from app.utils.decorators import require_csrf, update_required, view_required
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils


instances_detail_bp = Blueprint("instances_detail", __name__, url_prefix="/instances")


def _parse_is_active_value(data: Mapping[str, object] | object, *, default: bool = False) -> bool:
    """严格解析 is_active,仅接受布尔类型."""
    value = data.get("is_active", default) if isinstance(data, Mapping) else getattr(data, "is_active", default)

    if value is None:
        return default
    if isinstance(value, bool):
        return value

    msg = "is_active 仅支持布尔类型"
    raise ValidationError(msg)


def _parse_int(value: object | None, *, field: str, default: int | None = None) -> int:
    """解析整数参数,非法时抛出验证错误."""
    if value is None or value == "":
        if default is not None:
            return default
        msg = f"{field} 必须为整数"
        raise ValidationError(msg)

    try:
        return int(cast(Any, value))
    except (TypeError, ValueError) as exc:
        msg = f"{field} 必须为整数"
        raise ValidationError(msg) from exc


def _safe_strip(value: object, default: str = "") -> str:
    """安全去除字符串首尾空白."""
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return default
    return str(value).strip()


@instances_detail_bp.route("/<int:instance_id>")
@login_required
@view_required
def detail(instance_id: int) -> str | Response | tuple[Response, int]:
    """实例详情页面.

    Args:
        instance_id: 实例 ID.

    Returns:
        渲染的实例详情页面,包含账户列表和统计信息.

    Raises:
        NotFoundError: 当实例不存在时抛出.

    Query Parameters:
        include_deleted: 是否包含已删除账户,默认 'true'.

    """

    def _render() -> str:
        context = InstanceDetailPageService().build_context(instance_id)

        return render_template(
            "instances/detail.html",
            instance=context.instance,
            tags=context.tags,
            account_summary=context.account_summary,
            credentials=context.credentials,
            database_type_options=context.database_type_options,
        )

    return safe_route_call(
        _render,
        module="instances",
        action="detail",
        public_error="实例详情加载失败",
        context={"instance_id": instance_id},
    )


@instances_detail_bp.route("/api/<int:instance_id>/accounts")
@login_required
@view_required
def list_instance_accounts(instance_id: int) -> tuple[Response, int]:
    """获取实例账户数据 API."""
    include_deleted = request.args.get("include_deleted", "false").lower() == "true"
    include_permissions = request.args.get("include_permissions", "false").lower() == "true"
    search = (request.args.get("search") or "").strip()
    page = resolve_page(request.args, default=1, minimum=1)
    limit = resolve_page_size(
        request.args,
        default=20,
        minimum=1,
        maximum=200,
        module="instances",
        action="list_instance_accounts",
    )
    sort_field = (request.args.get("sort") or "username").strip().lower()
    sort_order = (request.args.get("order") or "asc").strip().lower()
    if sort_order not in {"asc", "desc"}:
        sort_order = "asc"

    def _execute() -> tuple[Response, int]:
        filters = InstanceAccountListFilters(
            instance_id=instance_id,
            include_deleted=include_deleted,
            include_permissions=include_permissions,
            search=search,
            page=page,
            limit=limit,
            sort_field=sort_field,
            sort_order=sort_order,
        )
        result = InstanceAccountsService().list_accounts(filters)
        items = marshal(result.items, INSTANCE_ACCOUNT_LIST_ITEM_FIELDS, skip_none=True)
        summary = marshal(result.summary, INSTANCE_ACCOUNT_SUMMARY_FIELDS)

        return jsonify_unified_success(
            data={
                "items": items,
                "total": result.total,
                "page": result.page,
                "pages": result.pages,
                "limit": result.limit,
                "summary": summary,
            },
            message="获取实例账户数据成功",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="list_instance_accounts",
        public_error="获取实例账户数据失败",
        context={
            "instance_id": instance_id,
            "include_deleted": include_deleted,
            "include_permissions": include_permissions,
            "search": search,
            "page": page,
            "limit": limit,
            "sort": sort_field,
            "order": sort_order,
        },
    )


@instances_detail_bp.route("/api/<int:instance_id>/accounts/<int:account_id>/change-history")
@login_required
@view_required
def get_account_change_history(instance_id: int, account_id: int) -> tuple[Response, int]:
    """获取账户变更历史.

    Args:
        instance_id: 实例 ID.
        account_id: 账户 ID.

    Returns:
        Response: 包含历史记录的 JSON.

    Raises:
        SystemError: 查询失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        result = InstanceAccountsService().get_change_history(instance_id, account_id)
        payload = marshal(result, INSTANCE_ACCOUNT_CHANGE_HISTORY_RESPONSE_FIELDS)
        return jsonify_unified_success(
            data=payload,
            message="获取账户变更历史成功",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="get_account_change_history",
        public_error="获取变更历史失败",
        context={"instance_id": instance_id, "account_id": account_id},
    )


@instances_detail_bp.route("/api/<int:instance_id>/edit", methods=["POST"])
@login_required
@update_required
@require_csrf
def update_instance_detail(instance_id: int) -> tuple[Response, int]:
    """编辑实例 API.

    Args:
        instance_id: 实例 ID.

    Returns:
        JSON 响应,包含更新后的实例信息.

    Raises:
        NotFoundError: 当实例不存在时抛出.
        ValidationError: 当数据验证失败时抛出.
        ConflictError: 当实例名称已存在时抛出.

    """

    def _execute() -> tuple[Response, int]:
        instance = (
            Instance.query.filter(
                Instance.id == instance_id,
                cast(Any, Instance.deleted_at).is_(None),
            )
            .first_or_404()
        )
        data = request.get_json() if request.is_json else request.form
        data = DataValidator.sanitize_input(data)

        is_valid, validation_error = DataValidator.validate_instance_data(data)
        if not is_valid:
            raise ValidationError(validation_error)

        credential_raw = data.get("credential_id")
        if credential_raw not in (None, ""):
            credential_id = _parse_int(credential_raw, field="credential_id")
            credential = Credential.query.get(credential_id)
            if not credential:
                msg = "凭据不存在"
                raise ValidationError(msg)

        existing_instance = Instance.query.filter(
            Instance.name == data.get("name"),
            Instance.id != instance_id,
        ).first()
        if existing_instance:
            msg = "实例名称已存在"
            raise ConflictError(msg)

        try:
            instance.name = _safe_strip(data.get("name", instance.name), instance.name or "")
            instance.db_type = data.get("db_type", instance.db_type)
            instance.host = _safe_strip(data.get("host", instance.host), instance.host or "")
            port_value = data.get("port", instance.port)
            instance.port = _parse_int(port_value, field="端口", default=instance.port or 0)
            credential_value = data.get("credential_id", instance.credential_id)
            instance.credential_id = (
                _parse_int(credential_value, field="credential_id") if credential_value not in (None, "") else None
            )
            instance.description = _safe_strip(
                data.get("description", instance.description),
                instance.description or "",
            )
            instance.is_active = _parse_is_active_value(data, default=instance.is_active)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        log_info(
            "更新数据库实例",
            module="instances",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=str(instance.db_type) if instance.db_type else None,
            host=instance.host,
            port=instance.port,
            is_active=instance.is_active,
        )

        return jsonify_unified_success(
            data={"instance": instance.to_dict()},
            message="实例更新成功",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="update_instance_detail",
        public_error="更新实例失败",
        expected_exceptions=(ValidationError, ConflictError),
        context={"instance_id": instance_id},
    )


@instances_detail_bp.route("/api/databases/<int:instance_id>/sizes", methods=["GET"])
@login_required
@view_required
def get_instance_database_sizes(instance_id: int) -> tuple[Response, int]:
    """获取指定实例的数据库大小数据(最新或历史).

    Args:
        instance_id: 实例 ID.

    Returns:
        JSON 响应,包含数据库大小数据列表和统计信息.

    Raises:
        NotFoundError: 当实例不存在时抛出.
        ValidationError: 当参数无效时抛出.
        SystemError: 当获取数据失败时抛出.

    Query Parameters:
        start_date: 开始日期(YYYY-MM-DD),可选.
        end_date: 结束日期(YYYY-MM-DD),可选.
        database_name: 数据库名称筛选,可选.
        latest_only: 是否只返回最新数据,默认 false.
        include_inactive: 是否包含非活跃数据库,默认 false.
        limit: 返回数量限制,默认 100.
        offset: 偏移量,默认 0.

    """
    query_snapshot = request.args.to_dict(flat=False)

    def _parse_date(value: str | None, field: str) -> date | None:
        if not value:
            return None
        try:
            parsed_dt = time_utils.to_china(value + "T00:00:00")
            return parsed_dt.date() if parsed_dt else None
        except Exception as exc:
            msg = f"{field} 格式错误,应为 YYYY-MM-DD"
            raise ValidationError(msg) from exc

    def _execute() -> tuple[Response, int]:
        (
            Instance.query.filter(
                Instance.id == instance_id,
                cast(Any, Instance.deleted_at).is_(None),
            )
            .first_or_404()
        )

        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        database_name = request.args.get("database_name")
        latest_only = request.args.get("latest_only", "false").lower() == "true"
        include_inactive = request.args.get("include_inactive", "false").lower() == "true"

        limit = _parse_int(request.args.get("limit"), field="limit", default=100)
        offset = _parse_int(request.args.get("offset"), field="offset", default=0)

        start_date_obj = _parse_date(start_date, "start_date")
        end_date_obj = _parse_date(end_date, "end_date")

        options = InstanceDatabaseSizesQuery(
            instance_id=instance_id,
            database_name=database_name,
            start_date=start_date_obj,
            end_date=end_date_obj,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset,
        )

        result = InstanceDatabaseSizesService().fetch_sizes(options, latest_only=latest_only)
        databases = marshal(result.databases, INSTANCE_DATABASE_SIZE_ENTRY_FIELDS)
        stats_payload: dict[str, object]
        if latest_only:
            stats_payload = {
                "total": result.total,
                "limit": result.limit,
                "offset": result.offset,
                "active_count": getattr(result, "active_count", 0),
                "filtered_count": getattr(result, "filtered_count", 0),
                "total_size_mb": getattr(result, "total_size_mb", 0),
                "databases": databases,
            }
        else:
            stats_payload = {
                "total": result.total,
                "limit": result.limit,
                "offset": result.offset,
                "databases": databases,
            }

        return jsonify_unified_success(data=stats_payload, message="数据库大小数据获取成功")

    return safe_route_call(
        _execute,
        module="database_aggregations",
        action="get_instance_database_sizes",
        public_error="获取数据库大小历史数据失败",
        expected_exceptions=(ValidationError,),
        context={"instance_id": instance_id, "query_params": query_snapshot},
    )


@instances_detail_bp.route("/api/<int:instance_id>/accounts/<int:account_id>/permissions")
@login_required
@view_required
def get_account_permissions(instance_id: int, account_id: int) -> tuple[Response, int]:
    """获取账户权限详情.

    根据数据库类型返回相应的权限信息(全局权限、角色、数据库权限等).

    Args:
        instance_id: 实例 ID.
        account_id: 账户 ID.

    Returns:
        JSON 响应,包含账户权限详情.

    Raises:
        NotFoundError: 当实例或账户不存在时抛出.

    """
    def _execute() -> tuple[Response, int]:
        result = InstanceAccountsService().get_account_permissions(instance_id, account_id)
        payload = marshal(result, INSTANCE_ACCOUNT_PERMISSIONS_RESPONSE_FIELDS, skip_none=True)
        return jsonify_unified_success(
            data=payload,
            message="获取账户权限成功",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="get_account_permissions",
        public_error="获取账户权限失败",
        context={"instance_id": instance_id, "account_id": account_id},
    )
