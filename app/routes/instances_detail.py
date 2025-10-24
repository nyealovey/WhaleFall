"""
实例详情相关接口
"""

from datetime import date
from typing import Any, Dict, Optional

from flask import Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import text

from app import db
from app.errors import ConflictError, SystemError, ValidationError
from app.models.database_size_stat import DatabaseSizeStat
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.tag import Tag
from app.routes.database_stats import database_stats_bp
from app.routes.instances import instances_bp
from app.services.account_sync_adapters.account_data_manager import AccountDataManager
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


@instances_bp.route("/<int:instance_id>")
@login_required
@view_required
def detail(instance_id: int) -> str | Response | tuple[Response, int]:
    """实例详情"""
    instance = Instance.query.get_or_404(instance_id)
    
    # 确保标签关系被加载
    instance.tags  # 触发标签关系的加载

    # 获取查询参数
    include_deleted = request.args.get("include_deleted", "true").lower() == "true"  # 默认包含已删除账户

    # 获取账户数据 - 使用新的优化同步模型
    from app.services.account_sync_adapters.account_data_manager import AccountDataManager

    sync_accounts = AccountDataManager.get_accounts_by_instance(instance_id, include_deleted=include_deleted)

    # 转换数据格式以适配模板
    accounts = []
    for sync_account in sync_accounts:
        # 从type_specific字段获取额外信息
        type_specific = sync_account.type_specific or {}

        account_data = {
            "id": sync_account.id,
            "username": sync_account.username,
            "host": type_specific.get("host", "%"),
            "plugin": type_specific.get("plugin", ""),
            "account_type": sync_account.db_type,
            "is_locked": sync_account.is_locked_display,  # 使用计算字段
            "is_active": not sync_account.is_deleted,
            "account_created_at": type_specific.get("account_created_at"),
            "last_sync_time": sync_account.last_sync_time,
            "is_superuser": sync_account.is_superuser,
            "last_change_type": sync_account.last_change_type,
            "last_change_time": sync_account.last_change_time,
            "type_specific": sync_account.type_specific,
            "is_deleted": sync_account.is_deleted,
            "deleted_time": sync_account.deleted_time,
            # 添加权限数据
            "server_roles": sync_account.server_roles or [],
            "server_permissions": sync_account.server_permissions or [],
            "database_roles": sync_account.database_roles or {},
            "database_permissions": sync_account.database_permissions or {},
        }
        accounts.append(account_data)

    return render_template("instances/detail.html", instance=instance, accounts=accounts)

@instances_bp.route("/api/<int:instance_id>/accounts/<int:account_id>/change-history")
@login_required
@view_required
def get_account_change_history(instance_id: int, account_id: int) -> Response:
    """获取账户变更历史"""
    instance = Instance.query.get_or_404(instance_id)

    from app.models.current_account_sync_data import CurrentAccountSyncData

    account = CurrentAccountSyncData.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

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

@instances_bp.route("/api/<int:instance_id>/edit", methods=["POST"])
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
        
        # 处理布尔值
        is_active_value = data.get("is_active", instance.is_active)
        if isinstance(is_active_value, str):
            instance.is_active = is_active_value in ["on", "true", "1", "yes"]
        else:
            instance.is_active = bool(is_active_value)

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


@instances_bp.route("/<int:instance_id>/edit", methods=["GET", "POST"])
@login_required
@update_required
@require_csrf
def edit(instance_id: int) -> str | Response | tuple[Response, int]:
    """编辑实例"""
    instance = Instance.query.get_or_404(instance_id)

    if request.method == "POST":
        data = request.form

        # 清理输入数据
        data = sanitize_form_data(data)

        # 输入验证
        required_fields = ["name", "db_type", "host", "port"]
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            flash(validation_error, "error")
            return render_template("instances/edit.html", instance=instance)

        # 验证数据库类型
        db_type_error = validate_db_type(data.get("db_type"))
        if db_type_error:
            flash(db_type_error, "error")
            return render_template("instances/edit.html", instance=instance)


        # 验证端口号
        try:
            port = int(data.get("port"))
            if port < 1 or port > 65535:
                error_msg = "端口号必须在1-65535之间"
                raise ValueError(error_msg)
        except (ValueError, TypeError):
            error_msg = "端口号必须是1-65535之间的整数"
            flash(error_msg, "error")
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
                flash(error_msg, "error")
                return render_template("instances/edit.html", instance=instance)

        # 验证实例名称唯一性（排除当前实例）
        existing_instance = Instance.query.filter(Instance.name == data.get("name"), Instance.id != instance_id).first()
        if existing_instance:
            error_msg = "实例名称已存在"
            flash(error_msg, "error")
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
            is_active_value = data.get("is_active", instance.is_active)
            if isinstance(is_active_value, str):
                instance.is_active = is_active_value in ["on", "true", "1", "yes"]
            else:
                instance.is_active = bool(is_active_value)

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

            flash("实例更新成功！", "success")
            return redirect(url_for("instances.detail", instance_id=instance_id))

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

            flash(error_msg, "error")

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




@database_stats_bp.route("/api/instances/<int:instance_id>/database-sizes", methods=["GET"])
@login_required
@view_required
def get_instance_database_sizes(instance_id: int) -> Response:
    """获取指定实例的数据库大小历史数据"""
    Instance.query.get_or_404(instance_id)

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    database_name = request.args.get("database_name")
    latest_only = request.args.get("latest_only", "false").lower() == "true"

    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except ValueError as exc:
        raise ValidationError("limit/offset 必须为整数") from exc

    start_date_obj: Optional[date] = None
    if start_date:
        try:
            parsed_dt = time_utils.to_china(start_date + "T00:00:00")
            start_date_obj = parsed_dt.date() if parsed_dt else None
        except Exception as exc:
            raise ValidationError("start_date 格式错误，应为 YYYY-MM-DD") from exc

    end_date_obj: Optional[date] = None
    if end_date:
        try:
            parsed_dt = time_utils.to_china(end_date + "T00:00:00")
            end_date_obj = parsed_dt.date() if parsed_dt else None
        except Exception as exc:
            raise ValidationError("end_date 格式错误，应为 YYYY-MM-DD") from exc

    try:
        if latest_only:
            stats_payload = _fetch_latest_database_sizes(
                instance_id, database_name, start_date_obj, end_date_obj, limit, offset
            )
        else:
            stats_payload = _fetch_historical_database_sizes(
                instance_id, database_name, start_date_obj, end_date_obj, limit, offset
            )
    except Exception as exc:
        log_error(
            "获取实例数据库大小历史数据失败",
            module="database_stats",
            instance_id=instance_id,
            error=str(exc),
        )
        raise SystemError("获取数据库大小历史数据失败") from exc

    return jsonify_unified_success(data=stats_payload, message="数据库大小数据获取成功")


def _fetch_latest_database_sizes(
    instance_id: int,
    database_name: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    sql_query = text(
        """
        SELECT * FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY database_name
                       ORDER BY collected_date DESC
                   ) AS rn
            FROM database_size_stats
            WHERE instance_id = :instance_id
        ) ranked
        WHERE rn = 1
        """
    )

    result = db.session.execute(sql_query, {"instance_id": instance_id})
    stats: list[DatabaseSizeStat] = []
    for row in result:
        stat = DatabaseSizeStat()
        stat.id = row.id
        stat.instance_id = row.instance_id
        stat.database_name = row.database_name
        stat.size_mb = row.size_mb
        stat.data_size_mb = row.data_size_mb
        stat.log_size_mb = row.log_size_mb
        stat.collected_date = row.collected_date
        stat.collected_at = row.collected_at
        stats.append(stat)

    if database_name:
        stats = [stat for stat in stats if database_name.lower() in stat.database_name.lower()]

    if start_date:
        stats = [stat for stat in stats if stat.collected_date >= start_date]

    if end_date:
        stats = [stat for stat in stats if stat.collected_date <= end_date]

    stats.sort(key=lambda x: x.collected_date, reverse=True)

    total_size_mb = sum(stat.size_mb or 0 for stat in stats)
    database_count = len(stats)
    total_count = len(stats)
    paged_stats = stats[offset : offset + limit]

    payload = {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "database_count": database_count,
        "total_size_mb": total_size_mb,
        "databases": [
            {
                "id": stat.id,
                "database_name": stat.database_name,
                "size_mb": stat.size_mb,
                "data_size_mb": stat.data_size_mb,
                "log_size_mb": stat.log_size_mb,
                "collected_date": stat.collected_date.isoformat() if stat.collected_date else None,
                "collected_at": stat.collected_at.isoformat() if stat.collected_at else None,
                "is_active": True,
            }
            for stat in paged_stats
        ],
    }

    return payload


def _fetch_historical_database_sizes(
    instance_id: int,
    database_name: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    query = DatabaseSizeStat.query.filter(DatabaseSizeStat.instance_id == instance_id)

    if database_name:
        query = query.filter(DatabaseSizeStat.database_name.ilike(f"%{database_name}%"))

    if start_date:
        query = query.filter(DatabaseSizeStat.collected_date >= start_date)

    if end_date:
        query = query.filter(DatabaseSizeStat.collected_date <= end_date)

    total = query.count()

    stats = (
        query.order_by(DatabaseSizeStat.collected_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "databases": [
            {
                "id": stat.id,
                "database_name": stat.database_name,
                "size_mb": stat.size_mb,
                "data_size_mb": stat.data_size_mb,
                "log_size_mb": stat.log_size_mb,
                "collected_date": stat.collected_date.isoformat() if stat.collected_date else None,
                "collected_at": stat.collected_at.isoformat() if stat.collected_at else None,
            }
            for stat in stats
        ],
    }
