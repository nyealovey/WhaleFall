
"""
鲸落 - 数据库实例管理路由
"""

from typing import Any

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.constants import HttpStatus, TaskStatus, FlashCategory, HttpMethod
from app.constants.database_types import DatabaseType
from app.errors import ConflictError, SystemError, ValidationError
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.models.instance_account import InstanceAccount
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.tag import Tag
from app.constants.filter_options import STATUS_ACTIVE_OPTIONS
from app.utils.query_filter_utils import get_active_tag_options
from app.utils.decorators import create_required, delete_required, require_csrf, update_required, view_required
from app.utils.data_validator import (
    DataValidator,
    sanitize_form_data,
    validate_db_type,
    validate_required_fields,
)
from app.utils.response_utils import jsonify_unified_success
from app.services.account_sync.account_query_service import get_accounts_by_instance
from app.services.instances import InstanceBatchCreationService, InstanceBatchDeletionService
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils

# 创建蓝图
instance_bp = Blueprint("instance", __name__)
batch_creation_service = InstanceBatchCreationService()
batch_deletion_service = InstanceBatchDeletionService()


@instance_bp.route("/")
@login_required
@view_required
def index() -> str:
    """实例管理首页"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    db_type = request.args.get("db_type", "", type=str)
    status_param = request.args.get("status", "", type=str)
    status_filter = status_param if status_param not in {"", "all"} else ""
    tags_raw = request.args.getlist("tags")
    if tags_raw:
        tags = [tag.strip() for tag in tags_raw if tag.strip()]
    else:
        tags_str = request.args.get("tags", "")
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

    # 构建查询
    query = Instance.query

    if search:
        query = query.filter(
            db.or_(
                Instance.name.contains(search),
                Instance.host.contains(search),
                Instance.description.contains(search),
            )
        )

    if db_type:
        query = query.filter(Instance.db_type == db_type)
    
    if status_filter:
        if status_filter == 'active':
            query = query.filter(Instance.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(Instance.is_active == False)

    # 标签筛选
    if tags:
        query = query.join(Instance.tags).filter(Tag.name.in_(tags))

    # 分页查询，按ID排序
    instances = query.order_by(Instance.id).paginate(page=page, per_page=per_page, error_out=False)
    instance_ids = [instance.id for instance in instances.items]

    active_database_counts = {}
    active_account_counts = {}
    last_sync_times: dict[int, Any] = {}

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
                SyncInstanceRecord.status == "completed",
                SyncInstanceRecord.completed_at.isnot(None),
            )
            .group_by(SyncInstanceRecord.instance_id)
            .all()
        )
        last_sync_times = {instance_id: completed_at for instance_id, completed_at in sync_rows}

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
        instances=instances,
        credentials=credentials,
        database_type_options=database_type_options,
        database_type_map=database_type_map,
        active_database_counts=active_database_counts,
        active_account_counts=active_account_counts,
        last_sync_times=last_sync_times,
        tag_options=tag_options,
        status_options=STATUS_ACTIVE_OPTIONS,
        selected_tags=tags,
        search=search,
        search_value=search,
        db_type=db_type,
        status=status_param,
    )




@instance_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_api() -> Response:
    """创建实例API"""
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


@instance_bp.route("/api/<int:instance_id>/delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def delete(instance_id: int) -> str | Response | tuple[Response, int]:
    """删除实例"""
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


@instance_bp.route("/api/batch-delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def batch_delete() -> str | Response | tuple[Response, int]:
    """批量删除实例"""
    try:
        data = request.get_json() or {}
        instance_ids = data.get("instance_ids", [])

        result = batch_deletion_service.delete_instances(instance_ids, operator_id=current_user.id)
        message = f"成功删除 {result.get('deleted_count', 0)} 个实例"

        return jsonify_unified_success(data=result, message=message)

    except Exception as e:
        log_error("批量删除实例失败", module="instances", exception=e)
        raise SystemError("批量删除实例失败") from e


@instance_bp.route("/api/batch-create", methods=["POST"])
@login_required
@create_required
@require_csrf
def batch_create() -> str | Response | tuple[Response, int]:
    """批量创建实例"""
    try:
        file = request.files.get("file")
        if not file or not file.filename.endswith(".csv"):
            raise ValidationError("请上传CSV格式文件")

        return _process_csv_file(file)

    except Exception as e:
        db.session.rollback()
        log_error("批量创建实例失败", module="instances", exception=e)
        raise SystemError("批量创建实例失败") from e


def _process_csv_file(file: Any) -> Response:  # noqa: ANN401
    """处理CSV文件"""
    import csv
    import io

    try:
        # 读取CSV文件
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)

        instances_data = []
        for row in csv_input:
            # 清理数据
            instance_data = {}
            for key, value in row.items():
                if value and value.strip():
                    instance_data[key.strip()] = value.strip()
                else:
                    # 对于空值，不设置该字段，而不是设置为None
                    pass

            instances_data.append(instance_data)

        return _create_instances(instances_data)

    except Exception as e:
        raise ValidationError(f"CSV文件处理失败: {str(e)}") from e


def _create_instances(instances_data: list[dict[str, Any]]) -> Response:
    """调用服务执行批量创建并返回统一响应。"""
    operator_id = getattr(current_user, "id", None)
    result = batch_creation_service.create_instances(instances_data, operator_id=operator_id)
    message = result.pop("message", f"成功创建 {result.get('created_count', 0)} 个实例")
    return jsonify_unified_success(data=result, message=message)



# API路由
@instance_bp.route("/api")
@login_required
@view_required
def api_list() -> Response:
    """获取实例列表API"""
    try:
        # 获取查询参数
        db_type = request.args.get('db_type')
        
        # 构建查询
        query = Instance.query.filter_by(is_active=True)
        
        # 如果指定了数据库类型，添加筛选条件
        if db_type and db_type != '':
            query = query.filter_by(db_type=db_type)
        
        instances = query.order_by(Instance.id).all()
        
        instances_data = []
        for instance in instances:
            instances_data.append({
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'host': instance.host,
                'port': instance.port,
                'description': instance.description or '',
                'is_active': instance.is_active
            })
        
        return jsonify_unified_success(
            data={
                "instances": instances_data,
                "db_type": db_type or None,
            },
            message="获取实例列表成功",
        )
        
    except Exception as e:
        log_error("获取实例列表失败", module="instances", exception=e)
        raise SystemError("获取实例列表失败") from e



@instance_bp.route("/api/<int:instance_id>")
@login_required
@view_required
def api_detail(instance_id: int) -> Response:
    """获取实例详情API"""
    instance = Instance.query.get_or_404(instance_id)
    return jsonify_unified_success(
        data={"instance": instance.to_dict()},
        message="获取实例详情成功",
    )


@instance_bp.route("/api/<int:instance_id>/accounts")
@login_required
@view_required
def api_get_accounts(instance_id: int) -> Response:
    """获取实例账户数据API"""
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
from . import instance_detail  # noqa: E402
from . import instance_statistics  # noqa: E402
