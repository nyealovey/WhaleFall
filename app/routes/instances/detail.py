"""实例详情相关接口.

提供实例详情页面、账户历史及容量统计等 API.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, cast
from sqlalchemy.sql.elements import ColumnElement

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from app import db
from app.constants.database_types import DatabaseType
from app.errors import ConflictError, ValidationError
from app.models.account_change_log import AccountChangeLog
from app.models.account_permission import AccountPermission
from app.models.credential import Credential
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.services.accounts_sync.account_query_service import get_accounts_by_instance
from app.services.database_type_service import DatabaseTypeService
from app.types import QueryProtocol
from app.utils.data_validator import DataValidator
from app.utils.decorators import require_csrf, update_required, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils


@dataclass(slots=True)
class CapacityQueryOptions:
    """数据库容量查询参数."""

    instance_id: int
    database_name: str | None
    start_date: date | None
    end_date: date | None
    include_inactive: bool
    limit: int
    offset: int

instances_detail_bp = Blueprint("instances_detail", __name__, url_prefix="/instances")
CapacityQuery = QueryProtocol[tuple[DatabaseSizeStat, bool | None, datetime | None, datetime | None]]


TRUTHY_VALUES = {"1", "true", "on", "yes", "y"}
FALSY_VALUES = {"0", "false", "off", "no", "n"}


def _parse_is_active_value(data: object, *, default: bool = False) -> bool:  # noqa: PLR0911
    """从请求数据中解析 is_active,兼容表单/JSON/checkbox.

    Args:
        data: 请求数据对象(表单或 JSON).
        default: 默认值,默认为 False.

    Returns:
        解析后的布尔值.

    """
    value: object | None
    if hasattr(data, "getlist"):
        values = data.getlist("is_active")  # type: ignore[call-arg]
        value = values[-1] if values else None  # 取最后一个值(checkbox优先)
    elif hasattr(data, "get"):
        value = data.get("is_active", default)  # type: ignore[call-arg]
    else:
        value = getattr(data, "is_active", default)

    if value is None:
        return default

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        # 兼容 JSON 中提供数组的情况,取最后一个
        for item in reversed(value):
            parsed = _parse_is_active_value({"is_active": item}, default=default)
            if parsed is not None:
                return parsed
        return default

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in TRUTHY_VALUES:
            return True
        if normalized in FALSY_VALUES:
            return False
        return default

    return bool(value)


def _safe_int(value: object | None, default: int) -> int:
    """安全解析整数,无法解析时回退默认值."""
    try:
        return int(cast(Any, value)) if value is not None else default
    except (TypeError, ValueError):  # pragma: no cover - 输入非法场景
        return default


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
        instance = Instance.query.get_or_404(instance_id)

        _ = instance.tags.all()

        include_deleted = request.args.get("include_deleted", "true").lower() == "true"

        sync_accounts = get_accounts_by_instance(instance_id, include_inactive=include_deleted)

        accounts = []
        for sync_account in sync_accounts:
            type_specific = sync_account.type_specific or {}

            instance_account = sync_account.instance_account
            is_active = bool(instance_account and instance_account.is_active)
            account_data = {
                "id": sync_account.id,
                "username": sync_account.username,
                "host": type_specific.get("host", "%"),
                "plugin": type_specific.get("plugin", ""),
                "account_type": sync_account.db_type,
                "is_locked": bool(sync_account.is_locked),
                "is_active": is_active,
                "account_created_at": type_specific.get("account_created_at"),
                "last_sync_time": sync_account.last_sync_time,
                "is_superuser": sync_account.is_superuser,
                "last_change_type": sync_account.last_change_type,
                "last_change_time": sync_account.last_change_time,
                "type_specific": sync_account.type_specific,
                "is_deleted": not is_active,
                "deleted_time": instance_account.deleted_at if instance_account else None,
                "server_roles": sync_account.server_roles or [],
                "server_permissions": sync_account.server_permissions or [],
                "database_roles": sync_account.database_roles or {},
                "database_permissions": sync_account.database_permissions or {},
            }
            accounts.append(account_data)

        account_summary = {
            "active": sum(1 for account in accounts if account.get("is_active")),
            "deleted": sum(1 for account in accounts if not account.get("is_active")),
            "superuser": sum(1 for account in accounts if account.get("is_superuser")),
        }

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

        return render_template(
            "instances/detail.html",
            instance=instance,
            accounts=accounts,
            account_summary=account_summary,
            credentials=credentials,
            database_type_options=database_type_options,
        )

    return safe_route_call(
        _render,
        module="instances",
        action="detail",
        public_error="实例详情加载失败",
        context={"instance_id": instance_id},
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
        instance = Instance.query.get_or_404(instance_id)

        account = AccountPermission.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

        change_logs = (
            AccountChangeLog.query.filter_by(
                instance_id=instance_id,
                username=account.username,
                db_type=instance.db_type,
            )
            .order_by(AccountChangeLog.change_time.desc())
            .limit(50)
            .all()
        )

        history = [
            {
                "id": log.id,
                "change_type": log.change_type,
                "change_time": (time_utils.format_china_time(log.change_time) if log.change_time else "未知"),
                "status": log.status,
                "message": log.message,
                "privilege_diff": log.privilege_diff,
                "other_diff": log.other_diff,
                "session_id": log.session_id,
            }
            for log in change_logs
        ]

        return jsonify_unified_success(
            data={
                "account": {
                    "id": account.id,
                    "username": account.username,
                    "db_type": instance.db_type,
                },
                "history": history,
            },
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
        instance = Instance.query.get_or_404(instance_id)
        data = request.get_json() if request.is_json else request.form
        data = DataValidator.sanitize_input(data)

        is_valid, validation_error = DataValidator.validate_instance_data(data)
        if not is_valid:
            raise ValidationError(validation_error)

        if data.get("credential_id"):
            try:
                credential_id = _safe_int(data.get("credential_id"), 0)
                credential = Credential.query.get(credential_id)
                if not credential:
                    msg = "凭据不存在"
                    raise ValidationError(msg)
            except (ValueError, TypeError) as exc:
                msg = "无效的凭据ID"
                raise ValidationError(msg) from exc

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
            instance.port = _safe_int(data.get("port", instance.port), instance.port or 0)
            instance.credential_id = _safe_int(
                data.get("credential_id", instance.credential_id),
                instance.credential_id or 0,
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


@instances_detail_bp.route("/api/edit/<int:instance_id>", methods=["POST"])
@login_required
@update_required
@require_csrf
def update_instance_detail_legacy(instance_id: int) -> tuple[Response, int]:
    """兼容旧版路径 `/instances/api/edit/<id>` 的别名."""
    return update_instance_detail(instance_id)


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
        Instance.query.get_or_404(instance_id)

        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        database_name = request.args.get("database_name")
        latest_only = request.args.get("latest_only", "false").lower() == "true"
        include_inactive = request.args.get("include_inactive", "false").lower() == "true"

        try:
            limit = _safe_int(request.args.get("limit"), 100)
            offset = _safe_int(request.args.get("offset"), 0)
        except ValueError as exc:
            msg = "limit/offset 必须为整数"
            raise ValidationError(msg) from exc

        start_date_obj = _parse_date(start_date, "start_date")
        end_date_obj = _parse_date(end_date, "end_date")

        options = CapacityQueryOptions(
            instance_id=instance_id,
            database_name=database_name,
            start_date=start_date_obj,
            end_date=end_date_obj,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset,
        )

        stats_payload = (
            _fetch_latest_database_sizes(options)
            if latest_only
            else _fetch_historical_database_sizes(options)
        )

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
def get_account_permissions(instance_id: int, account_id: int) -> dict[str, Any] | Response | tuple[Response, int]:
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
    instance = Instance.query.get_or_404(instance_id)

    account = AccountPermission.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

    permissions = {
        "db_type": instance.db_type.upper() if instance else "",
        "username": account.username,
        "is_superuser": account.is_superuser,
        "last_sync_time": (time_utils.format_china_time(account.last_sync_time) if account.last_sync_time else "未知"),
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

    account_info = {
        "id": account.id,
        "instance_id": instance_id,
        "username": account.username,
        "db_type": instance.db_type.lower() if instance and instance.db_type else "",
        "is_superuser": account.is_superuser,
        "is_locked": bool(account.is_locked),
        "last_sync_time": account.last_sync_time.isoformat() if account.last_sync_time else None,
    }

    return jsonify_unified_success(
        data={"permissions": permissions, "account": account_info},
        message="获取账户权限详情成功",
    )


def _build_capacity_query(
    instance_id: int,
    database_name: str | None,
    start_date: date | None,
    end_date: date | None,
) -> CapacityQuery:
    """构建容量查询对象.

    Args:
        instance_id: 实例 ID.
        database_name: 数据库名称筛选.
        start_date: 起始日期.
        end_date: 截止日期.

    Returns:
        查询对象,可继续链式操作.

    """
    base_query = (
        db.session.query(
            DatabaseSizeStat,
            InstanceDatabase.is_active,
            InstanceDatabase.deleted_at,
            InstanceDatabase.last_seen_date,
        )
        .outerjoin(
            InstanceDatabase,
            (DatabaseSizeStat.instance_id == InstanceDatabase.instance_id)
            & (DatabaseSizeStat.database_name == InstanceDatabase.database_name),
        )
        .filter(DatabaseSizeStat.instance_id == instance_id)
    )

    query = cast("CapacityQuery", base_query)

    if database_name:
        query = query.filter(DatabaseSizeStat.database_name.ilike(f"%{database_name}%"))

    if start_date:
        query = query.filter(DatabaseSizeStat.collected_date >= start_date)

    if end_date:
        query = query.filter(DatabaseSizeStat.collected_date <= end_date)

    return query


def _normalize_active_flag(*, flag: bool | None) -> bool:
    """将可能为空的激活标记标准化为 bool.

    Args:
        flag: 数据库记录中的活跃标记,可能为 None.

    Returns:
        bool: 默认视为 True 的布尔值.

    """
    if flag is None:
        return True
    return bool(flag)


def _serialize_capacity_entry(
    stat: DatabaseSizeStat,
    *,
    is_active: bool,
    deleted_at: datetime | None,
    last_seen_date: date | None,
) -> dict[str, Any]:
    """序列化容量记录.

    Args:
        stat: 数据库容量统计记录.
        is_active: 是否活跃.
        deleted_at: 删除时间.
        last_seen_date: 最后发现日期.

    Returns:
        dict[str, Any]: 包含数据库名称、大小及状态的字典.

    """
    collected_date_val = stat.collected_date if not isinstance(stat.collected_date, ColumnElement) else None
    collected_at_val = stat.collected_at if not isinstance(stat.collected_at, ColumnElement) else None

    return {
        "id": stat.id,
        "database_name": stat.database_name,
        "size_mb": stat.size_mb,
        "data_size_mb": stat.data_size_mb,
        "log_size_mb": stat.log_size_mb,
        "collected_date": collected_date_val.isoformat() if collected_date_val else None,
        "collected_at": collected_at_val.isoformat() if collected_at_val else None,
        "is_active": is_active,
        "deleted_at": deleted_at.isoformat() if deleted_at else None,
        "last_seen_date": last_seen_date.isoformat() if last_seen_date else None,
    }


def _fetch_latest_database_sizes(options: CapacityQueryOptions) -> dict[str, Any]:
    """获取最新一次容量统计.

    Args:
        options: 查询参数集合.

    Returns:
        dict[str, Any]: 包含分页数据与汇总信息的字典.

    """
    query = _build_capacity_query(
        options.instance_id,
        options.database_name,
        options.start_date,
        options.end_date,
    )

    records = (
        query.order_by(
            DatabaseSizeStat.database_name.asc(),
            DatabaseSizeStat.collected_date.desc(),
        )
        .all()
    )

    latest: list[tuple[DatabaseSizeStat, bool, datetime | None, date | None]] = []
    seen: set[str] = set()

    for stat, is_active_flag, deleted_at, last_seen in records:
        key = stat.database_name.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized_active = _normalize_active_flag(flag=is_active_flag)
        if not options.include_inactive and not normalized_active:
            continue
        latest.append((stat, normalized_active, deleted_at, last_seen))

    include_placeholder_inactive = options.include_inactive or not latest

    if include_placeholder_inactive:
        inactive_query = InstanceDatabase.query.filter(
            InstanceDatabase.instance_id == options.instance_id,
            cast(ColumnElement[bool], InstanceDatabase.is_active).is_(False),
        )
        if options.database_name:
            inactive_query = inactive_query.filter(
                InstanceDatabase.database_name.ilike(f"%{options.database_name}%"),
            )

        for instance_db in inactive_query:
            if not instance_db.database_name:
                continue
            key = instance_db.database_name.lower()
            if key in seen:
                continue
            placeholder_stat = SimpleNamespace(
                id=None,
                instance_id=instance_db.instance_id,
                database_name=instance_db.database_name,
                size_mb=0,
                data_size_mb=None,
                log_size_mb=None,
                collected_date=None,
                collected_at=None,
            )
            latest.append(
                (
                    cast(DatabaseSizeStat, placeholder_stat),
                    False,
                    instance_db.deleted_at,
                    instance_db.last_seen_date,
                ),
            )
            seen.add(key)

    total = len(latest)
    filtered_count = sum(1 for _, active, _, _ in latest if not active)
    active_total_size = sum((stat.size_mb or 0) for stat, active, _, _ in latest if active)

    paged = latest[options.offset : options.offset + options.limit]

    return {
        "total": total,
        "limit": options.limit,
        "offset": options.offset,
        "active_count": total - filtered_count,
        "filtered_count": filtered_count,
        "total_size_mb": active_total_size,
        "databases": [
            _serialize_capacity_entry(
                stat,
                is_active=active,
                deleted_at=deleted_at,
                last_seen_date=last_seen,
            )
            for stat, active, deleted_at, last_seen in paged
        ],
    }


def _fetch_historical_database_sizes(options: CapacityQueryOptions) -> dict[str, Any]:
    """获取历史容量统计.

    Args:
        options: 查询参数集合.

    Returns:
        dict[str, Any]: 包含历史记录的分页数据.

    """
    query = _build_capacity_query(
        options.instance_id,
        options.database_name,
        options.start_date,
        options.end_date,
    )

    if not options.include_inactive:
        query = query.filter(
            or_(
                InstanceDatabase.is_active.is_(True),
                InstanceDatabase.is_active.is_(None),
            ),
        )

    total = query.count()

    rows = (
        query.order_by(DatabaseSizeStat.collected_date.desc(), DatabaseSizeStat.database_name.asc())
        .offset(options.offset)
        .limit(options.limit)
        .all()
    )

    return {
        "total": total,
        "limit": options.limit,
        "offset": options.offset,
        "databases": [
            _serialize_capacity_entry(
                stat,
                is_active=_normalize_active_flag(flag=is_active_flag),
                deleted_at=deleted_at,
                last_seen_date=last_seen,
            )
            for stat, is_active_flag, deleted_at, last_seen in rows
        ],
    }
