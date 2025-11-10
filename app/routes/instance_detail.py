"""
实例详情相关接口
"""

from datetime import date, datetime
from typing import Any, Dict, Optional
from types import SimpleNamespace

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import text, or_

from app import db
from app.errors import ConflictError, SystemError, ValidationError
from app.constants import TaskStatus, FlashCategory, HttpMethod
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance_database import InstanceDatabase
from app.constants.database_types import DatabaseType
from app.models.credential import Credential
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.tag import Tag
from app.services.account_sync.account_query_service import get_accounts_by_instance
from app.utils.data_validator import (
    DataValidator,
    sanitize_form_data,
    validate_db_type,
    validate_required_fields,
)
from app.utils.decorators import require_csrf, update_required, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils

instance_detail_bp = Blueprint("instance_detail", __name__, url_prefix="/instances")


TRUTHY_VALUES = {"1", "true", "on", "yes", "y"}
FALSY_VALUES = {"0", "false", "off", "no", "n"}


def _parse_is_active_value(data: Any, default: bool = False) -> bool:
    """从请求数据中解析 is_active，兼容表单/JSON/checkbox"""
    value: Any
    if hasattr(data, "getlist"):
        values = data.getlist("is_active")
        if not values:
            value = None
        else:
            value = values[-1]  # 取最后一个值（checkbox优先于隐藏域）
    else:
        value = data.get("is_active", default)

    if value is None:
        return default

    if isinstance(value, (list, tuple)):
        # 兼容 JSON 中提供数组的情况，取最后一个
        for item in reversed(value):
            parsed = _parse_is_active_value({"is_active": item}, default)
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


@instance_detail_bp.route("/<int:instance_id>")
@login_required
@view_required
def detail(instance_id: int) -> str | Response | tuple[Response, int]:
    """实例详情"""
    instance = Instance.query.get_or_404(instance_id)
    
    # 确保标签关系被加载
    instance.tags  # 触发标签关系的加载

    # 获取查询参数
    include_deleted = request.args.get("include_deleted", "true").lower() == "true"  # 默认包含已删除账户

    sync_accounts = get_accounts_by_instance(instance_id, include_inactive=include_deleted)

    # 转换数据格式以适配模板
    accounts = []
    for sync_account in sync_accounts:
        # 从type_specific字段获取额外信息
        type_specific = sync_account.type_specific or {}

        instance_account = sync_account.instance_account
        is_active = bool(instance_account and instance_account.is_active)
        account_data = {
            "id": sync_account.id,
            "username": sync_account.username,
            "host": type_specific.get("host", "%"),
            "plugin": type_specific.get("plugin", ""),
            "account_type": sync_account.db_type,
            "is_locked": sync_account.is_locked_display,  # 使用计算字段
            "is_active": is_active,
            "account_created_at": type_specific.get("account_created_at"),
            "last_sync_time": sync_account.last_sync_time,
            "is_superuser": sync_account.is_superuser,
            "last_change_type": sync_account.last_change_type,
            "last_change_time": sync_account.last_change_time,
            "type_specific": sync_account.type_specific,
            "is_deleted": not is_active,
            "deleted_time": instance_account.deleted_at if instance_account else None,
            # 添加权限数据
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

    return render_template(
        "instances/detail.html",
        instance=instance,
        accounts=accounts,
        account_summary=account_summary,
    )

@instance_detail_bp.route("/api/<int:instance_id>/accounts/<int:account_id>/change-history")
@login_required
@view_required
def get_account_change_history(instance_id: int, account_id: int) -> Response:
    """获取账户变更历史"""
    instance = Instance.query.get_or_404(instance_id)

    from app.models.account_permission import AccountPermission

    account = AccountPermission.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

    try:
        from app.models.account_change_log import AccountChangeLog

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

        history = []
        for log in change_logs:
            history.append(
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
            )

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

    except Exception as exc:  # noqa: BLE001
        log_error(
            "获取账户变更历史失败",
            module="instances",
            instance_id=instance_id,
            account_id=account_id,
            exception=exc,
        )
        raise SystemError("获取变更历史失败") from exc

@instance_detail_bp.route("/api/<int:instance_id>/edit", methods=["POST"])
@login_required
@update_required
@require_csrf
def edit_api(instance_id: int) -> Response:
    """编辑实例API"""
    instance = Instance.query.get_or_404(instance_id)
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

    # 验证实例名称唯一性（排除当前实例）
    existing_instance = Instance.query.filter(
        Instance.name == data.get("name"), Instance.id != instance_id
    ).first()
    if existing_instance:
        raise ConflictError("实例名称已存在")

    try:
        # 更新实例信息
        instance.name = data.get("name", instance.name).strip()
        instance.db_type = data.get("db_type", instance.db_type)
        instance.host = data.get("host", instance.host).strip()
        instance.port = int(data.get("port", instance.port))
        instance.credential_id = data.get("credential_id", instance.credential_id)
        instance.description = data.get("description", instance.description).strip()

        instance.is_active = _parse_is_active_value(data, default=instance.is_active)

        db.session.commit()

        # 记录操作日志
        log_info(
            "更新数据库实例",
            module="instances",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
            port=instance.port,
            is_active=instance.is_active,
        )

        return jsonify_unified_success(
            data={"instance": instance.to_dict()},
            message="实例更新成功",
        )

    except Exception as e:
        db.session.rollback()
        log_error(
            "更新实例失败",
            module="instances",
            user_id=getattr(current_user, "id", None),
            instance_id=instance.id,
            exception=e,
        )
        raise SystemError("更新实例失败") from e


@instance_detail_bp.route("/<int:instance_id>/edit", methods=["GET", "POST"])
@login_required
@update_required
@require_csrf
def edit(instance_id: int) -> str | Response | tuple[Response, int]:
    """编辑实例"""
    instance = Instance.query.get_or_404(instance_id)

    if request.method == HttpMethod.POST:
        data = request.form

        # 清理输入数据
        data = sanitize_form_data(data)

        # 输入验证
        required_fields = ["name", "db_type", "host", "port"]
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            flash(validation_error, FlashCategory.ERROR)
            return render_template("instances/edit.html", instance=instance)

        # 验证数据库类型
        db_type_error = validate_db_type(data.get("db_type"))
        if db_type_error:
            flash(db_type_error, FlashCategory.ERROR)
            return render_template("instances/edit.html", instance=instance)


        # 验证端口号
        try:
            port = int(data.get("port"))
            if port < 1 or port > 65535:
                error_msg = "端口号必须在1-65535之间"
                raise ValueError(error_msg)
        except (ValueError, TypeError):
            error_msg = "端口号必须是1-65535之间的整数"
            flash(error_msg, FlashCategory.ERROR)
            return render_template("instances/edit.html", instance=instance)

        # 验证凭据ID
        if data.get("credential_id"):
            try:
                credential_id = int(data.get("credential_id"))
                credential = Credential.query.get(credential_id)
                if not credential:
                    error_msg = "凭据不存在"
                    raise ValueError(error_msg)
            except (ValueError, TypeError):
                error_msg = "无效的凭据ID"
                flash(error_msg, FlashCategory.ERROR)
                return render_template("instances/edit.html", instance=instance)

        # 验证实例名称唯一性（排除当前实例）
        existing_instance = Instance.query.filter(Instance.name == data.get("name"), Instance.id != instance_id).first()
        if existing_instance:
            error_msg = "实例名称已存在"
            flash(error_msg, FlashCategory.ERROR)
            return render_template("instances/edit.html", instance=instance)

        try:
            # 更新实例信息
            instance.name = data.get("name", instance.name).strip()
            instance.db_type = data.get("db_type", instance.db_type)
            instance.host = data.get("host", instance.host).strip()
            instance.port = int(data.get("port", instance.port))
            instance.database_name = data.get("database_name", instance.database_name)
            if instance.database_name:
                instance.database_name = instance.database_name.strip() or None
            instance.credential_id = int(data.get("credential_id")) if data.get("credential_id") else None
            instance.description = data.get("description", instance.description)
            if data.get("description"):
                instance.description = data.get("description").strip()
            # 正确处理布尔值
            instance.is_active = _parse_is_active_value(data, default=instance.is_active)

            # 处理标签更新
            tag_names = data.get("tag_names", [])
            
            if isinstance(tag_names, str):
                # 如果是逗号分隔的字符串，分割成列表
                tag_names = [name.strip() for name in tag_names.split(",") if name.strip()]
            
            # 清除现有标签 - 使用正确的方法
            # 先获取所有现有标签，然后逐个移除
            existing_tags = list(instance.tags)
            for tag in existing_tags:
                instance.tags.remove(tag)
            
            # 添加新标签
            added_tags = []
            for tag_name in tag_names:
                tag = Tag.get_tag_by_name(tag_name)
                if tag:
                    instance.tags.append(tag)
                    added_tags.append(tag_name)
            
            # 只记录一次标签更新结果
            if added_tags:
                log_info(f"实例 {instance.id} 标签已更新: {', '.join(added_tags)}")

            db.session.commit()

            # 记录操作日志
            log_info(
                "更新数据库实例",
                module="instances",
                user_id=current_user.id,
                instance_id=instance.id,
                instance_name=instance.name,
                db_type=instance.db_type,
                host=instance.host,
                changes={
                    "name": data.get("name"),
                    "db_type": data.get("db_type"),
                    "host": data.get("host"),
                    "port": data.get("port"),
                    "credential_id": data.get("credential_id"),
                    "description": data.get("description"),
                    "is_active": data.get("is_active"),
                },
            )

            flash("实例更新成功！", FlashCategory.SUCCESS)
            return redirect(url_for("instance_detail.detail", instance_id=instance_id))

        except Exception as e:
            db.session.rollback()
            log_error(
                "更新实例失败",
                module="instances",
                user_id=getattr(current_user, "id", None),
                instance_id=instance.id,
                exception=e,
            )

            # 根据错误类型提供更具体的错误信息
            if "UNIQUE constraint failed" in str(e):
                error_msg = "实例名称已存在，请使用其他名称"
            elif "NOT NULL constraint failed" in str(e):
                error_msg = "必填字段不能为空"
            elif "FOREIGN KEY constraint failed" in str(e):
                error_msg = "关联的凭据不存在"
            else:
                error_msg = f"更新实例失败: {str(e)}"

            flash(error_msg, FlashCategory.ERROR)

    # GET请求，显示编辑表单
    credentials = Credential.query.filter_by(is_active=True).all()

    # 获取可用的数据库类型
    from app.services.database_type_service import DatabaseTypeService

    database_types = DatabaseTypeService.get_active_types()
    
    # 获取所有标签
    all_tags = Tag.get_active_tags()

    return render_template(
        "instances/edit.html",
        instance=instance,
        all_tags=all_tags,
        credentials=credentials,
        database_types=database_types,
    )




@instance_detail_bp.route("/api/databases/<int:instance_id>/sizes", methods=["GET"])
@login_required
@view_required
def get_instance_database_sizes(instance_id: int) -> Response:
    """获取指定实例的数据库大小数据（最新或历史）"""
    Instance.query.get_or_404(instance_id)

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    database_name = request.args.get("database_name")
    latest_only = request.args.get("latest_only", "false").lower() == "true"
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"

    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except ValueError as exc:
        raise ValidationError("limit/offset 必须为整数") from exc

    def _parse_date(value: Optional[str], field: str) -> Optional[date]:
        if not value:
            return None
        try:
            parsed_dt = time_utils.to_china(value + "T00:00:00")
            return parsed_dt.date() if parsed_dt else None
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"{field} 格式错误，应为 YYYY-MM-DD") from exc

    start_date_obj = _parse_date(start_date, "start_date")
    end_date_obj = _parse_date(end_date, "end_date")

    try:
        if latest_only:
            stats_payload = _fetch_latest_database_sizes(
                instance_id=instance_id,
                database_name=database_name,
                start_date=start_date_obj,
                end_date=end_date_obj,
                include_inactive=include_inactive,
                limit=limit,
                offset=offset,
            )
        else:
            stats_payload = _fetch_historical_database_sizes(
                instance_id=instance_id,
                database_name=database_name,
                start_date=start_date_obj,
                end_date=end_date_obj,
                include_inactive=include_inactive,
                limit=limit,
                offset=offset,
            )
    except Exception as exc:  # noqa: BLE001
        log_error(
            "获取实例数据库大小历史数据失败",
            module="database_aggr",
            instance_id=instance_id,
            error=str(exc),
        )
        raise SystemError("获取数据库大小历史数据失败") from exc

    return jsonify_unified_success(data=stats_payload, message="数据库大小数据获取成功")


@instance_detail_bp.route("/api/<int:instance_id>/accounts/<int:account_id>/permissions")
@login_required
@view_required
def get_account_permissions(instance_id: int, account_id: int) -> dict[str, Any] | Response | tuple[Response, int]:
    """获取账户权限详情"""
    instance = Instance.query.get_or_404(instance_id)

    account = AccountPermission.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

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

    account_info = {
        "id": account.id,
        "instance_id": instance_id,
        "username": account.username,
        "db_type": instance.db_type.lower() if instance and instance.db_type else "",
        "is_superuser": account.is_superuser,
        "is_locked": account.is_locked_display,
        "last_sync_time": account.last_sync_time.isoformat() if account.last_sync_time else None,
    }

    return jsonify_unified_success(
        data={"permissions": permissions, "account": account_info},
        message="获取账户权限详情成功",
    )
def _build_capacity_query(
    instance_id: int,
    database_name: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
):
    query = (
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

    if database_name:
        query = query.filter(DatabaseSizeStat.database_name.ilike(f"%{database_name}%"))

    if start_date:
        query = query.filter(DatabaseSizeStat.collected_date >= start_date)

    if end_date:
        query = query.filter(DatabaseSizeStat.collected_date <= end_date)

    return query


def _normalize_active_flag(flag: Optional[bool]) -> bool:
    if flag is None:
        return True
    return bool(flag)


def _serialize_capacity_entry(
    stat: DatabaseSizeStat,
    is_active: bool,
    deleted_at: Optional[datetime],
    last_seen_date: Optional[date],
) -> dict[str, Any]:
    return {
        "id": stat.id,
        "database_name": stat.database_name,
        "size_mb": stat.size_mb,
        "data_size_mb": stat.data_size_mb,
        "log_size_mb": stat.log_size_mb,
        "collected_date": stat.collected_date.isoformat() if stat.collected_date else None,
        "collected_at": stat.collected_at.isoformat() if stat.collected_at else None,
        "is_active": is_active,
        "deleted_at": deleted_at.isoformat() if deleted_at else None,
        "last_seen_date": last_seen_date.isoformat() if last_seen_date else None,
    }


def _fetch_latest_database_sizes(
    instance_id: int,
    database_name: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    include_inactive: bool,
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    query = _build_capacity_query(instance_id, database_name, start_date, end_date)

    records = query.order_by(
        DatabaseSizeStat.database_name.asc(),
        DatabaseSizeStat.collected_date.desc(),
    ).all()

    latest: list[tuple[DatabaseSizeStat, bool, Optional[datetime], Optional[date]]] = []
    seen: set[str] = set()

    for stat, is_active_flag, deleted_at, last_seen in records:
        key = stat.database_name.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized_active = _normalize_active_flag(is_active_flag)
        if not include_inactive and not normalized_active:
            continue
        latest.append((stat, normalized_active, deleted_at, last_seen))

    include_placeholder_inactive = include_inactive or not latest

    if include_placeholder_inactive:
        inactive_query = (
            InstanceDatabase.query.filter(
                InstanceDatabase.instance_id == instance_id,
                InstanceDatabase.is_active.is_(False),
            )
        )
        if database_name:
            inactive_query = inactive_query.filter(InstanceDatabase.database_name.ilike(f"%{database_name}%"))

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
            latest.append((placeholder_stat, False, instance_db.deleted_at, instance_db.last_seen_date))
            seen.add(key)

    total = len(latest)
    filtered_count = sum(1 for _, active, _, _ in latest if not active)
    active_total_size = sum((stat.size_mb or 0) for stat, active, _, _ in latest if active)

    paged = latest[offset : offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "active_count": total - filtered_count,
        "filtered_count": filtered_count,
        "total_size_mb": active_total_size,
        "databases": [
            _serialize_capacity_entry(stat, active, deleted_at, last_seen)
            for stat, active, deleted_at, last_seen in paged
        ],
    }


def _fetch_historical_database_sizes(
    instance_id: int,
    database_name: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    include_inactive: bool,
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    query = _build_capacity_query(instance_id, database_name, start_date, end_date)

    if not include_inactive:
        query = query.filter(
            or_(
                InstanceDatabase.is_active.is_(True),
                InstanceDatabase.is_active.is_(None),
            )
        )

    total = query.count()

    rows = (
        query
        .order_by(DatabaseSizeStat.collected_date.desc(), DatabaseSizeStat.database_name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "databases": [
            _serialize_capacity_entry(
                stat,
                _normalize_active_flag(is_active_flag),
                deleted_at,
                last_seen,
            )
            for stat, is_active_flag, deleted_at, last_seen in rows
        ],
    }
