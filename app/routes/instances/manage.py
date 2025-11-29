
"""
鲸落 - 数据库实例管理路由
"""

from typing import Any

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import asc, desc, func, or_

from app import db
from app.constants import (
    DatabaseType,
    FlashCategory,
    HttpMethod,
    HttpStatus,
    STATUS_ACTIVE_OPTIONS,
    SyncStatus,
)
from app.errors import ConflictError, SystemError, ValidationError
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.models.instance_account import InstanceAccount
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.tag import Tag, instance_tags
from app.utils.query_filter_utils import get_active_tag_options
from app.utils.decorators import create_required, delete_required, require_csrf, update_required, view_required
from app.utils.data_validator import (
    DataValidator,
    sanitize_form_data,
    validate_db_type,
    validate_required_fields,
)
from app.utils.response_utils import jsonify_unified_success
from app.services.accounts_sync.account_query_service import get_accounts_by_instance
from app.utils.structlog_config import log_error, log_info
from app.routes.instances.batch import batch_deletion_service
from app.utils.time_utils import time_utils

# 创建蓝图
instances_bp = Blueprint("instances", __name__)


@instances_bp.route("/")
@login_required
@view_required
def index() -> str:
    """实例管理首页。

    渲染实例列表页面，支持搜索、筛选和标签过滤。

    Returns:
        渲染后的 HTML 页面。
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

    # 获取数据库类型配置
    from app.services.database_type_service import DatabaseTypeService

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
    """创建实例 API。

    接收 JSON 或表单数据，验证后创建新的数据库实例。

    Returns:
        包含新创建实例信息的 JSON 响应。

    Raises:
        ValidationError: 当数据验证失败时抛出。
        ConflictError: 当实例名称已存在时抛出。
        SystemError: 当创建失败时抛出。
    """
    data = request.get_json() if request.is_json else request.form

    # 清理输入数据
    data = DataValidator.sanitize_input(data)

    # 使用新的数据验证器进行严格验证
    is_valid, validation_error = DataValidator.validate_instance_data(data)
    if not is_valid:
        raise ValidationError(validation_error)

    # 验证凭据ID（如果提供）
    if data.get("credential_id"):
        try:
            credential_id = int(data.get("credential_id"))
            credential = Credential.query.get(credential_id)
            if not credential:
                raise ValidationError("凭据不存在")
        except (ValueError, TypeError):
            raise ValidationError("无效的凭据ID")

    # 验证实例名称唯一性
    existing_instance = Instance.query.filter_by(name=data.get("name")).first()
    if existing_instance:
        raise ConflictError("实例名称已存在")

    try:
        # 创建新实例
        instance = Instance(
            name=data.get("name").strip(),
            db_type=data.get("db_type"),
            host=data.get("host").strip(),
            port=int(data.get("port")),
            credential_id=data.get("credential_id"),
            description=data.get("description", "").strip(),
            is_active=True,
        )

        db.session.add(instance)
        db.session.commit()

        # 记录操作日志
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

    except Exception as e:
        db.session.rollback()
        log_error(
            "创建实例失败",
            module="instances",
            user_id=getattr(current_user, "id", None),
            exception=e,
        )
        raise SystemError("创建实例失败") from e


@instances_bp.route("/api/<int:instance_id>/delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def delete(instance_id: int) -> str | Response | tuple[Response, int]:
    """删除实例。

    删除指定实例及其关联的所有数据（账户、同步记录、变更日志等）。

    Args:
        instance_id: 实例ID。

    Returns:
        包含删除统计信息的 JSON 响应。

    Raises:
        SystemError: 当删除失败时抛出。
    """
    instance = Instance.query.get_or_404(instance_id)

    try:
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

    except Exception as e:
        db.session.rollback()
        log_error(
            "删除实例失败",
            module="instances",
            instance_id=instance.id,
            instance_name=instance.name,
            exception=e,
        )
        raise SystemError("删除实例失败，请重试") from e




# API路由
@instances_bp.route("/api/instances", methods=["GET"])
@login_required
@view_required
def list_instances_data() -> Response:
    """Grid.js 实例列表 API。

    Returns:
        Response: 包含分页实例数据的 JSON。

    Raises:
        SystemError: 查询或序列化失败时抛出。
    """

    try:
        page = max(request.args.get("page", 1, type=int), 1)
        limit = min(max(request.args.get("limit", 20, type=int), 1), 100)
        sort_field = request.args.get("sort", "id")
        sort_order = (request.args.get("order", "desc") or "desc").lower()

        search = (request.args.get("search") or request.args.get("q") or "").strip()
        db_type = (request.args.get("db_type") or "").strip()
        status_value = (request.args.get("status") or "").strip()
        tags_values = [tag.strip() for tag in request.args.getlist("tags") if tag.strip()]
        if not tags_values:
            tags_raw = (request.args.get("tags") or "").split(",")
            tags_values = [tag.strip() for tag in tags_raw if tag.strip()]

        query = Instance.query

        if search:
            query = query.filter(
                or_(
                    Instance.name.ilike(f"%{search}%"),
                    Instance.host.ilike(f"%{search}%"),
                    Instance.description.ilike(f"%{search}%"),
                )
            )

        if db_type and db_type != "all":
            query = query.filter(Instance.db_type == db_type)

        if status_value:
            if status_value == "active":
                query = query.filter(Instance.is_active.is_(True))
            elif status_value == "inactive":
                query = query.filter(Instance.is_active.is_(False))

        if tags_values:
            query = query.join(Instance.tags).filter(Tag.name.in_(tags_values))

        last_sync_subquery = (
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

        sortable_fields = {
            "id": Instance.id,
            "name": Instance.name,
            "db_type": Instance.db_type,
            "host": Instance.host,
        }
        if sort_field == "last_sync_time":
            query = query.outerjoin(last_sync_subquery, Instance.id == last_sync_subquery.c.instance_id)
            sortable_fields["last_sync_time"] = last_sync_subquery.c.last_sync_time

        order_column = sortable_fields.get(sort_field, Instance.id)
        query = query.order_by(order_column.asc() if sort_order == "asc" else order_column.desc())

        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        instance_ids = [instance.id for instance in pagination.items]

        active_database_counts: dict[int, int] = {}
        active_account_counts: dict[int, int] = {}
        last_sync_times: dict[int, Any] = {}
        tags_map: dict[int, list[dict[str, Any]]] = {}

        if instance_ids:
            db_count_rows = (
                db.session.query(
                    InstanceDatabase.instance_id,
                    func.count(InstanceDatabase.id),
                )
                .filter(
                    InstanceDatabase.instance_id.in_(instance_ids),
                    InstanceDatabase.is_active.is_(True),
                )
                .group_by(InstanceDatabase.instance_id)
                .all()
            )
            active_database_counts = {instance_id: count for instance_id, count in db_count_rows}

            account_count_rows = (
                db.session.query(
                    InstanceAccount.instance_id,
                    func.count(InstanceAccount.id),
                )
                .filter(
                    InstanceAccount.instance_id.in_(instance_ids),
                    InstanceAccount.is_active.is_(True),
                )
                .group_by(InstanceAccount.instance_id)
                .all()
            )
            active_account_counts = {instance_id: count for instance_id, count in account_count_rows}

            sync_rows = (
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
            last_sync_times = {instance_id: completed_at for instance_id, completed_at in sync_rows}

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
                tags_map.setdefault(instance_id, []).append(
                    {
                        "name": tag_name,
                        "display_name": display_name,
                        "color": color,
                    }
                )

        items = []
        for instance in pagination.items:
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
                    "active_db_count": active_database_counts.get(instance.id, 0),
                    "active_account_count": active_account_counts.get(instance.id, 0),
                    "last_sync_time": (
                        last_sync_times.get(instance.id).isoformat()
                        if last_sync_times.get(instance.id)
                        else None
                    ),
                    "tags": tags_map.get(instance.id, []),
                }
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

    except Exception as exc:  # noqa: BLE001
        log_error("获取实例列表失败", module="instances", exception=exc)
        raise SystemError("获取实例列表失败") from exc



@instances_bp.route("/api/<int:instance_id>")
@login_required
@view_required
def get_instance_detail(instance_id: int) -> Response:
    """获取实例详情 API。

    Args:
        instance_id: 实例 ID。

    Returns:
        Response: 包含实例详细信息的 JSON。
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
    """获取实例账户数据 API。

    Args:
        instance_id: 实例 ID。

    Returns:
        Response: 账户列表 JSON。

    Raises:
        SystemError: 查询账户数据失败时抛出。
    """
    instance = Instance.query.get_or_404(instance_id)

    include_deleted = request.args.get("include_deleted", "false").lower() == "true"

    try:
        accounts = get_accounts_by_instance(instance_id, include_inactive=include_deleted)

        account_data = []
        for account in accounts:
            type_specific = account.type_specific or {}
            instance_account = account.instance_account
            is_active = bool(instance_account and instance_account.is_active)
            # 对于锁定状态优先使用各数据库的 type_specific 字段判定，若账户已被标记删除再补充为锁定
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
                    }
                )

            account_data.append(account_info)

        return jsonify_unified_success(
            data={"accounts": account_data},
            message="获取实例账户数据成功",
        )

    except Exception as exc:  # noqa: BLE001
        log_error(
            "获取实例账户数据失败",
            module="instances",
            instance_id=instance_id,
            exception=exc,
        )
        raise SystemError("获取实例账户数据失败") from exc


    from app.models.account_permission import AccountPermission

    account = AccountPermission.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

    try:
        # 构建权限信息（与账户管理页面保持一致的数据结构）
        permissions = {
            "db_type": instance.db_type.upper() if instance else "",
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
                    "instance_name": instance.name if instance else "未知实例",
                    "db_type": instance.db_type if instance else "",
                },
            },
            message="获取账户权限成功",
        )

    except Exception as exc:  # noqa: BLE001
        log_error(
            "获取账户权限失败",
            module="instances",
            instance_id=instance_id,
            account_id=account_id,
            exception=exc,
        )
        raise SystemError("获取权限失败") from exc


# 注册额外路由模块
from . import detail  # noqa: E402,F401
from . import statistics  # noqa: E402,F401
