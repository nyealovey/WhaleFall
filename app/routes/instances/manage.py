"""鲸落 - 数据库实例管理路由."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from collections import defaultdict

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app import db
from app.constants import (
    STATUS_ACTIVE_OPTIONS,
    DatabaseType,
    HttpStatus,
    SyncStatus,
)
from app.errors import ConflictError, ValidationError
from app.models.account_permission import AccountPermission
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.instance_database import InstanceDatabase
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.tag import Tag, instance_tags
from app.routes.instances.batch import batch_deletion_service
from app.services.accounts_sync.account_query_service import get_accounts_by_instance
from app.services.database_type_service import DatabaseTypeService
from app.utils.data_validator import (
    DataValidator,
)
from app.utils.decorators import create_required, delete_required, require_csrf, view_required
from app.utils.query_filter_utils import get_active_tag_options
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from werkzeug.datastructures import MultiDict


@dataclass(slots=True)
class InstanceListFilters:
    """实例列表筛选条件."""

    page: int
    limit: int
    sort_field: str
    sort_order: str
    search: str
    db_type: str
    status: str
    tags: list[str]

# 创建蓝图
instances_bp = Blueprint("instances", __name__)


def _parse_instance_filters(args: "MultiDict[str, str]") -> InstanceListFilters:
    """解析请求参数,构建统一的筛选条件."""

    page = max(args.get("page", 1, type=int), 1)
    limit = min(max(args.get("limit", 20, type=int), 1), 100)
    sort_field = (args.get("sort", "id", type=str) or "id").lower()
    sort_order = (args.get("order", "desc", type=str) or "desc").lower()
    if sort_order not in {"asc", "desc"}:
        sort_order = "desc"

    search = (args.get("search") or args.get("q") or "").strip()
    db_type = (args.get("db_type") or "").strip()
    status_value = (args.get("status") or "").strip()
    tags = [tag.strip() for tag in args.getlist("tags") if tag and tag.strip()]
    if not tags:
        tags_raw = (args.get("tags") or "").split(",")
        tags = [tag.strip() for tag in tags_raw if tag.strip()]

    return InstanceListFilters(
        page=page,
        limit=limit,
        sort_field=sort_field,
        sort_order=sort_order,
        search=search,
        db_type=db_type,
        status=status_value,
        tags=tags,
    )


def _build_last_sync_subquery():
    """构建同步时间子查询."""

    return (
        db.session.query(
            SyncInstanceRecord.instance_id.label("instance_id"),
            func.max(SyncInstanceRecord.completed_at).label("last_sync_time"),
        )
        .filter(
            SyncInstanceRecord.sync_category.in_(["account", "capacity"]),
            SyncInstanceRecord.status == SyncStatus.COMPLETED,
            SyncInstanceRecord.completed_at.isnot(None),
        )
        .group_by(SyncInstanceRecord.instance_id)
        .subquery()
    )


def _apply_instance_filters(query, filters: InstanceListFilters):
    """将搜索、数据库类型、状态与标签筛选应用到查询."""

    if filters.search:
        like_term = f"%{filters.search}%"
        query = query.filter(
            or_(
                Instance.name.ilike(like_term),
                Instance.host.ilike(like_term),
                Instance.description.ilike(like_term),
            ),
        )

    if filters.db_type and filters.db_type != "all":
        query = query.filter(Instance.db_type == filters.db_type)

    if filters.status:
        if filters.status == "active":
            query = query.filter(Instance.is_active.is_(True))
        elif filters.status == "inactive":
            query = query.filter(Instance.is_active.is_(False))

    if filters.tags:
        query = query.join(Instance.tags).filter(Tag.name.in_(filters.tags))

    return query


def _apply_instance_sorting(query, filters: InstanceListFilters, last_sync_subquery) -> Any:
    """根据排序字段组装 SQLAlchemy 排序语句."""

    sortable_fields = {
        "id": Instance.id,
        "name": Instance.name,
        "db_type": Instance.db_type,
        "host": Instance.host,
    }
    if filters.sort_field == "last_sync_time":
        query = query.outerjoin(last_sync_subquery, Instance.id == last_sync_subquery.c.instance_id)
        sortable_fields["last_sync_time"] = last_sync_subquery.c.last_sync_time

    order_column = sortable_fields.get(filters.sort_field, Instance.id)
    if filters.sort_order == "asc":
        return query.order_by(order_column.asc())
    return query.order_by(order_column.desc())


def _collect_instance_metrics(
    instance_ids: list[int],
) -> tuple[dict[int, int], dict[int, int], dict[int, Any], dict[int, list[dict[str, Any]]]]:
    """加载实例关联的数据库/账户数量、同步时间与标签."""

    if not instance_ids:
        return {}, {}, {}, {}

    database_counts = dict(
        db.session.query(InstanceDatabase.instance_id, func.count(InstanceDatabase.id))
        .filter(
            InstanceDatabase.instance_id.in_(instance_ids),
            InstanceDatabase.is_active.is_(True),
        )
        .group_by(InstanceDatabase.instance_id)
        .all(),
    )

    account_counts = dict(
        db.session.query(InstanceAccount.instance_id, func.count(InstanceAccount.id))
        .filter(
            InstanceAccount.instance_id.in_(instance_ids),
            InstanceAccount.is_active.is_(True),
        )
        .group_by(InstanceAccount.instance_id)
        .all(),
    )

    last_sync_rows = (
        db.session.query(
            SyncInstanceRecord.instance_id,
            func.max(SyncInstanceRecord.completed_at),
        )
        .filter(
            SyncInstanceRecord.instance_id.in_(instance_ids),
            SyncInstanceRecord.sync_category.in_(["account", "capacity"]),
            SyncInstanceRecord.status == SyncStatus.COMPLETED,
            SyncInstanceRecord.completed_at.isnot(None),
        )
        .group_by(SyncInstanceRecord.instance_id)
        .all()
    )
    last_sync_times = dict(last_sync_rows)

    tags_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    tag_rows = (
        db.session.query(
            instance_tags.c.instance_id,
            Tag.name,
            Tag.display_name,
            Tag.color,
        )
        .join(Tag, Tag.id == instance_tags.c.tag_id)
        .filter(instance_tags.c.instance_id.in_(instance_ids))
        .all()
    )
    for instance_id, tag_name, display_name, color in tag_rows:
        tags_map[instance_id].append(
            {
                "name": tag_name,
                "display_name": display_name,
                "color": color,
            },
        )

    return database_counts, account_counts, last_sync_times, tags_map


def _serialize_instance_items(
    instances: list[Instance],
    database_counts: dict[int, int],
    account_counts: dict[int, int],
    last_sync_times: dict[int, Any],
    tags_map: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """将实例对象和统计信息转换为前端需要的结构."""

    items: list[dict[str, Any]] = []
    for instance in instances:
        last_sync = last_sync_times.get(instance.id)
        items.append(
            {
                "id": instance.id,
                "name": instance.name,
                "db_type": instance.db_type,
                "host": instance.host,
                "port": instance.port,
                "description": instance.description or "",
                "is_active": instance.is_active,
                "main_version": instance.main_version,
                "active_db_count": database_counts.get(instance.id, 0),
                "active_account_count": account_counts.get(instance.id, 0),
                "last_sync_time": last_sync.isoformat() if last_sync else None,
                "tags": tags_map.get(instance.id, []),
            },
        )
    return items


@instances_bp.route("/")
@login_required
@view_required
def index() -> str:
    """实例管理首页.

    渲染实例列表页面,支持搜索、筛选和标签过滤.

    Returns:
        渲染后的 HTML 页面.

    """
    search = (request.args.get("search") or request.args.get("q") or "").strip()
    db_type = (request.args.get("db_type") or "").strip()
    status_param = (request.args.get("status") or "").strip()
    tags_raw = request.args.getlist("tags")
    if tags_raw:
        tags = [tag.strip() for tag in tags_raw if tag.strip()]
    else:
        tags_str = request.args.get("tags", "")
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

    # 获取所有可用的凭据
    credentials = Credential.query.filter_by(is_active=True).all()

    database_type_configs = DatabaseTypeService.get_active_types()
    database_type_options = [
        {
            "value": config.name,
            "label": config.display_name,
            "icon": config.icon or "fa-database",
            "color": config.color or "primary",
        }
        for config in database_type_configs
    ]
    database_type_map = {
        config.name: {
            "display_name": config.display_name,
            "icon": config.icon or "fa-database",
            "color": config.color or "primary",
        }
        for config in database_type_configs
    }

    tag_options = get_active_tag_options()

    return render_template(
        "instances/list.html",
        credentials=credentials,
        database_type_options=database_type_options,
        database_type_map=database_type_map,
        tag_options=tag_options,
        status_options=STATUS_ACTIVE_OPTIONS,
        search=search,
        db_type=db_type,
        status=status_param,
        selected_tags=tags,
    )


@instances_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_instance() -> Response:
    """创建实例 API.

    接收 JSON 或表单数据,验证后创建新的数据库实例.

    Returns:
        包含新创建实例信息的 JSON 响应.

    Raises:
        ValidationError: 当数据验证失败时抛出.
        ConflictError: 当实例名称已存在时抛出.
        SystemError: 当创建失败时抛出.

    """
    raw_payload = request.get_json() if request.is_json else request.form
    payload = DataValidator.sanitize_input(raw_payload)

    def _execute() -> Response:
        is_valid, validation_error = DataValidator.validate_instance_data(payload)
        if not is_valid:
            raise ValidationError(validation_error)

        if payload.get("credential_id"):
            try:
                credential_id = int(payload.get("credential_id"))
            except (ValueError, TypeError) as exc:
                msg = "无效的凭据ID"
                raise ValidationError(msg) from exc
            credential = Credential.query.get(credential_id)
            if not credential:
                msg = "凭据不存在"
                raise ValidationError(msg)

        existing_instance = Instance.query.filter_by(name=payload.get("name")).first()
        if existing_instance:
            msg = "实例名称已存在"
            raise ConflictError(msg)

        instance = Instance(
            name=(payload.get("name") or "").strip(),
            db_type=payload.get("db_type"),
            host=(payload.get("host") or "").strip(),
            port=int(payload.get("port")),
            credential_id=payload.get("credential_id"),
            description=(payload.get("description", "") or "").strip(),
            is_active=True,
        )

        with db.session.begin():
            db.session.add(instance)

        log_info(
            "创建数据库实例",
            module="instances",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
            port=instance.port,
        )

        return jsonify_unified_success(
            data={"instance": instance.to_dict()},
            message="实例创建成功",
            status=HttpStatus.CREATED,
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="create_instance",
        public_error="创建实例失败",
        context={
            "credential_id": payload.get("credential_id"),
            "db_type": payload.get("db_type"),
        },
    )


@instances_bp.route("/api/<int:instance_id>/delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def delete(instance_id: int) -> str | Response | tuple[Response, int]:
    """删除实例.

    删除指定实例及其关联的所有数据(账户、同步记录、变更日志等).

    Args:
        instance_id: 实例ID.

    Returns:
        包含删除统计信息的 JSON 响应.

    Raises:
        SystemError: 当删除失败时抛出.

    """
    instance = Instance.query.get_or_404(instance_id)

    def _execute() -> Response:
        log_info(
            "删除数据库实例",
            module="instances",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
        )

        result = batch_deletion_service.delete_instances([instance.id], operator_id=current_user.id)

        return jsonify_unified_success(
            data={
                "deleted_assignments": result.get("deleted_assignments", 0),
                "deleted_sync_data": result.get("deleted_sync_data", 0),
                "deleted_sync_records": result.get("deleted_sync_records", 0),
                "deleted_change_logs": result.get("deleted_change_logs", 0),
            },
            message="实例删除成功",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="delete_instance",
        public_error="删除实例失败,请重试",
        context={"instance_id": instance_id},
    )


# API路由
@instances_bp.route("/api/instances", methods=["GET"])
@login_required
@view_required
def list_instances_data() -> Response:
    """Grid.js 实例列表 API.

    Returns:
        Response: 包含分页实例数据的 JSON.

    Raises:
        SystemError: 查询或序列化失败时抛出.

    """

    def _execute() -> Response:
        filters = _parse_instance_filters(request.args)
        query = Instance.query
        query = _apply_instance_filters(query, filters)
        last_sync_subquery = _build_last_sync_subquery()
        query = _apply_instance_sorting(query, filters, last_sync_subquery)

        pagination = query.paginate(page=filters.page, per_page=filters.limit, error_out=False)
        instance_ids = [instance.id for instance in pagination.items]
        (
            database_counts,
            account_counts,
            last_sync_times,
            tags_map,
        ) = _collect_instance_metrics(instance_ids)
        items = _serialize_instance_items(
            list(pagination.items),
            database_counts,
            account_counts,
            last_sync_times,
            tags_map,
        )

        return jsonify_unified_success(
            data={
                "items": items,
                "total": pagination.total,
                "page": pagination.page,
                "pages": pagination.pages,
                "limit": pagination.per_page,
            },
            message="获取实例列表成功",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="list_instances_data",
        public_error="获取实例列表失败",
        context={
            "endpoint": "instances_list",
            "search": request.args.get("search"),
            "status": request.args.get("status"),
        },
    )


@instances_bp.route("/api/<int:instance_id>")
@login_required
@view_required
def get_instance_detail(instance_id: int) -> Response:
    """获取实例详情 API.

    Args:
        instance_id: 实例 ID.

    Returns:
        Response: 包含实例详细信息的 JSON.

    """
    instance = Instance.query.get_or_404(instance_id)
    return jsonify_unified_success(
        data={"instance": instance.to_dict()},
        message="获取实例详情成功",
    )


@instances_bp.route("/api/<int:instance_id>/accounts")
@login_required
@view_required
def list_instance_accounts(instance_id: int) -> Response:
    """获取实例账户数据 API.

    Args:
        instance_id: 实例 ID.

    Returns:
        Response: 账户列表 JSON.

    Raises:
        SystemError: 查询账户数据失败时抛出.

    """
    instance = Instance.query.get_or_404(instance_id)
    include_deleted = request.args.get("include_deleted", "false").lower() == "true"

    def _execute() -> Response:
        accounts = get_accounts_by_instance(instance_id, include_inactive=include_deleted)

        account_data = []
        for account in accounts:
            type_specific = account.type_specific or {}
            instance_account = account.instance_account
            is_active = bool(instance_account and instance_account.is_active)
            is_locked_flag = bool(account.is_locked)

            account_info = {
                "id": account.id,
                "username": account.username,
                "is_superuser": account.is_superuser,
                "is_locked": is_locked_flag,
                "is_deleted": not is_active,
                "last_change_time": account.last_change_time.isoformat() if account.last_change_time else None,
                "type_specific": type_specific,
                "server_roles": account.server_roles or [],
                "server_permissions": account.server_permissions or [],
                "database_roles": account.database_roles or {},
                "database_permissions": account.database_permissions or {},
            }

            if instance.db_type == DatabaseType.MYSQL:
                account_info.update({"host": type_specific.get("host", "%"), "plugin": type_specific.get("plugin", "")})
            elif instance.db_type == DatabaseType.SQLSERVER:
                account_info.update({"password_change_time": type_specific.get("password_change_time")})
            elif instance.db_type == DatabaseType.ORACLE:
                account_info.update(
                    {
                        "oracle_id": type_specific.get("oracle_id"),
                        "authentication_type": type_specific.get("authentication_type"),
                        "account_status": type_specific.get("account_status"),
                        "lock_date": type_specific.get("lock_date"),
                        "expiry_date": type_specific.get("expiry_date"),
                        "default_tablespace": type_specific.get("default_tablespace"),
                        "created": type_specific.get("created"),
                    },
                )

            account_data.append(account_info)

        return jsonify_unified_success(
            data={"accounts": account_data},
            message="获取实例账户数据成功",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="list_instance_accounts",
        public_error="获取实例账户数据失败",
        context={"instance_id": instance_id, "include_deleted": include_deleted},
    )


@instances_bp.route("/api/<int:instance_id>/accounts/<int:account_id>/permissions")
@login_required
@view_required
def get_instance_account_permissions(instance_id: int, account_id: int) -> Response:
    """获取指定实例账户的权限详情.

    Args:
        instance_id: 实例 ID.
        account_id: 账户权限记录 ID.

    Returns:
        Response: 权限详情 JSON.

    """
    instance = Instance.query.get_or_404(instance_id)
    account = AccountPermission.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

    def _execute() -> Response:
        permissions = {
            "db_type": instance.db_type.upper(),
            "username": account.username,
            "is_superuser": account.is_superuser,
            "last_sync_time": (
                time_utils.format_china_time(account.last_sync_time) if account.last_sync_time else "未知"
            ),
        }

        if instance.db_type == DatabaseType.MYSQL:
            permissions["global_privileges"] = account.global_privileges or []
            permissions["database_privileges"] = account.database_privileges or {}
        elif instance.db_type == DatabaseType.POSTGRESQL:
            permissions["predefined_roles"] = account.predefined_roles or []
            permissions["role_attributes"] = account.role_attributes or {}
            permissions["database_privileges_pg"] = account.database_privileges_pg or {}
            permissions["tablespace_privileges"] = account.tablespace_privileges or {}
        elif instance.db_type == DatabaseType.SQLSERVER:
            permissions["server_roles"] = account.server_roles or []
            permissions["server_permissions"] = account.server_permissions or []
            permissions["database_roles"] = account.database_roles or {}
            permissions["database_permissions"] = account.database_permissions or {}
        elif instance.db_type == DatabaseType.ORACLE:
            permissions["oracle_roles"] = account.oracle_roles or []
            permissions["system_privileges"] = account.system_privileges or []
            permissions["tablespace_privileges_oracle"] = account.tablespace_privileges_oracle or {}

        return jsonify_unified_success(
            data={
                "permissions": permissions,
                "account": {
                    "id": account.id,
                    "username": account.username,
                    "instance_name": instance.name,
                    "db_type": instance.db_type,
                },
            },
            message="获取账户权限成功",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="get_instance_account_permissions",
        public_error="获取权限失败",
        context={"instance_id": instance_id, "account_id": account_id},
    )


# 注册额外路由模块
def _load_related_blueprints() -> None:
    """确保实例管理相关蓝图被导入注册."""
    from . import (  # noqa: F401, PLC0415
        detail,
        statistics,
    )


_load_related_blueprints()
