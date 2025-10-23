
"""
鲸落 - 数据库实例管理路由
"""

from typing import Any

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.errors import ConflictError, SystemError, ValidationError
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.tag import Tag
from app.utils.decorators import create_required, delete_required, require_csrf, update_required, view_required
from app.utils.data_validator import (
    DataValidator,
    sanitize_form_data,
    validate_db_type,
    validate_required_fields,
)
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils

# 创建蓝图
instances_bp = Blueprint("instances", __name__)


def _delete_instance_related_data(instance_id: int, instance_name: str = None) -> dict:
    """
    删除实例的所有关联数据

    Args:
        instance_id: 实例ID
        instance_name: 实例名称（用于日志）

    Returns:
        dict: 删除统计信息
    """
    from app.models.account_change_log import AccountChangeLog
    from app.models.account_classification import AccountClassificationAssignment
    from app.models.current_account_sync_data import CurrentAccountSyncData
    from app.models.sync_instance_record import SyncInstanceRecord

    # 统计删除的数据量
    stats = {"assignment_count": 0, "sync_data_count": 0, "sync_record_count": 0, "change_log_count": 0}

    try:
        # 第一步：删除账户分类分配 (依赖CurrentAccountSyncData)
        sync_data_ids = [data.id for data in CurrentAccountSyncData.query.filter_by(instance_id=instance_id).all()]
        if sync_data_ids:
            stats["assignment_count"] = AccountClassificationAssignment.query.filter(
                AccountClassificationAssignment.account_id.in_(sync_data_ids)
            ).count()
            if stats["assignment_count"] > 0:
                AccountClassificationAssignment.query.filter(
                    AccountClassificationAssignment.account_id.in_(sync_data_ids)
                ).delete(synchronize_session=False)
                log_info(
                    f"步骤1: 删除了 {stats['assignment_count']} 个分类分配记录",
                    module="instances",
                    instance_id=instance_id,
                    instance_name=instance_name,
                )

        # 第二步：删除同步数据 (CurrentAccountSyncData)
        stats["sync_data_count"] = CurrentAccountSyncData.query.filter_by(instance_id=instance_id).count()
        if stats["sync_data_count"] > 0:
            CurrentAccountSyncData.query.filter_by(instance_id=instance_id).delete()
            log_info(
                f"步骤2: 删除了 {stats['sync_data_count']} 条同步数据记录",
                module="instances",
                instance_id=instance_id,
                instance_name=instance_name,
            )

        # 第三步：删除同步实例记录 (SyncInstanceRecord)
        stats["sync_record_count"] = SyncInstanceRecord.query.filter_by(instance_id=instance_id).count()
        if stats["sync_record_count"] > 0:
            SyncInstanceRecord.query.filter_by(instance_id=instance_id).delete()
            log_info(
                f"步骤3: 删除了 {stats['sync_record_count']} 条同步实例记录",
                module="instances",
                instance_id=instance_id,
                instance_name=instance_name,
            )

        # 第四步：删除账户变更日志 (AccountChangeLog)
        stats["change_log_count"] = AccountChangeLog.query.filter_by(instance_id=instance_id).count()
        if stats["change_log_count"] > 0:
            AccountChangeLog.query.filter_by(instance_id=instance_id).delete()
            log_info(
                f"步骤4: 删除了 {stats['change_log_count']} 条账户变更日志",
                module="instances",
                instance_id=instance_id,
                instance_name=instance_name,
            )

        log_info(
            f"实例 {instance_name or instance_id} 的所有关联数据删除完成",
            module="instances",
            instance_id=instance_id,
            instance_name=instance_name,
        )

        return stats

    except Exception as e:
        log_error(
            f"删除实例 {instance_name or instance_id} 关联数据失败: {e}",
            module="instances",
            instance_id=instance_id,
            instance_name=instance_name,
        )
        raise


@instances_bp.route("/")
@login_required
@view_required
def index() -> str:
    """实例管理首页"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    db_type = request.args.get("db_type", "", type=str)
    status = request.args.get("status", "", type=str)
    tags_str = request.args.get("tags", "")
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

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
    
    if status:
        if status == 'active':
            query = query.filter(Instance.is_active == True)
        elif status == 'inactive':
            query = query.filter(Instance.is_active == False)

    # 标签筛选
    if tags:
        query = query.join(Instance.tags).filter(Tag.name.in_(tags))

    # 分页查询，按ID排序
    instances = query.order_by(Instance.id).paginate(page=page, per_page=per_page, error_out=False)

    # 获取所有可用的凭据
    credentials = Credential.query.filter_by(is_active=True).all()

    # 获取数据库类型配置
    from app.services.database_type_service import DatabaseTypeService

    database_types = DatabaseTypeService.get_active_types()

    # 获取所有标签用于筛选
    all_tags = Tag.get_active_tags()
    
    return render_template(
        "instances/list.html",
        instances=instances,
        credentials=credentials,
        database_types=database_types,
        all_tags=all_tags,
        selected_tags=tags,
        search=search,
        search_value=search,
        db_type=db_type,
        status=status,
    )




@instances_bp.route("/api/create", methods=["POST"])
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
            status=201,
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


@instances_bp.route("/create", methods=["GET", "POST"])
@login_required
@create_required
@require_csrf
def create() -> str | Response:
    """创建实例页面"""
    # 获取凭据列表
    credentials = Credential.query.filter_by(is_active=True).all()

    if request.method == "POST":
        data = request.form

        # 清理输入数据
        data = DataValidator.sanitize_input(data)

        # 使用新的数据验证器进行严格验证
        is_valid, validation_error = DataValidator.validate_instance_data(data)
        if not is_valid:
            flash(validation_error, "error")
            return render_template("instances/create.html", credentials=credentials)

        # 验证凭据ID（如果提供）
        if data.get("credential_id"):
            try:
                credential_id = int(data.get("credential_id"))
                credential = Credential.query.get(credential_id)
                if not credential:
                    error_msg = "凭据不存在"
                    flash(error_msg, "error")
                    return render_template("instances/create.html", credentials=credentials)
            except (ValueError, TypeError):
                error_msg = "无效的凭据ID"
                flash(error_msg, "error")
                return render_template("instances/create.html", credentials=credentials)

        # 验证实例名称唯一性
        existing_instance = Instance.query.filter_by(name=data.get("name")).first()
        if existing_instance:
            error_msg = "实例名称已存在"
            flash(error_msg, "error")
            return render_template("instances/create.html", credentials=credentials)

        try:
            # 创建新实例
            instance = Instance(
                name=data.get("name").strip(),
                db_type=data.get("db_type"),
                host=data.get("host").strip(),
                port=int(data.get("port")),
                database_name=data.get("database_name", "").strip() or None,
                credential_id=(int(data.get("credential_id")) if data.get("credential_id") else None),
                description=data.get("description", "").strip(),
            )

            # 设置其他属性
            instance.is_active = data.get("is_active", True) in [True, "on", "1", 1]

            db.session.add(instance)
            db.session.commit()

            # 处理标签
            tag_names = data.get("tag_names", [])
            
            if isinstance(tag_names, str):
                # 如果是逗号分隔的字符串，分割成列表
                tag_names = [name.strip() for name in tag_names.split(",") if name.strip()]
            
            # 添加标签
            added_tags = []
            for tag_name in tag_names:
                tag = Tag.get_tag_by_name(tag_name)
                if tag:
                    instance.add_tag(tag)
                    added_tags.append(tag_name)
            
            # 只记录一次标签创建结果
            if added_tags:
                log_info(
                    "实例标签已创建",
                    module="instances",
                    instance_id=instance.id,
                    instance_name=instance.name,
                    tags=added_tags,
                )

            # 记录操作日志
            log_info(
                "创建数据库实例",
                module="instances",
                user_id=current_user.id,
                instance_id=instance.id,
                instance_name=instance.name,
                db_type=instance.db_type,
                host=instance.host,
            )

            flash("实例创建成功！", "success")
            return redirect(url_for("instances.index"))

        except Exception as e:
            db.session.rollback()
            log_error(
                "创建实例失败",
                module="instances",
                user_id=getattr(current_user, "id", None),
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
                error_msg = f"创建实例失败: {str(e)}"

            flash(error_msg, "error")

    # GET请求，显示创建表单
    credentials = Credential.query.filter_by(is_active=True).all()

    # 获取可用的数据库类型
    from app.services.database_type_service import DatabaseTypeService

    database_types = DatabaseTypeService.get_active_types()
    
    # 获取所有标签
    all_tags = Tag.get_active_tags()

    return render_template("instances/create.html", credentials=credentials, database_types=database_types, all_tags=all_tags)





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


@instances_bp.route("/api/<int:instance_id>/delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def delete(instance_id: int) -> str | Response | tuple[Response, int]:
    """删除实例"""
    instance = Instance.query.get_or_404(instance_id)

    stats = {
        "assignment_count": 0,
        "sync_data_count": 0,
        "sync_record_count": 0,
        "change_log_count": 0,
    }

    try:
        # 记录操作日志
        log_info(
            "删除数据库实例",
            module="instances",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
        )

        # 删除关联数据并删除实例
        stats = _delete_instance_related_data(instance.id, instance.name)
        db.session.delete(instance)
        db.session.commit()

        # 提取统计信息
        assignment_count = stats["assignment_count"]
        sync_data_count = stats["sync_data_count"]
        sync_record_count = stats["sync_record_count"]
        change_log_count = stats["change_log_count"]

        # 实例及其相关数据删除成功

        return jsonify_unified_success(
            data={
                "deleted_assignments": assignment_count,
                "deleted_sync_data": sync_data_count,
                "deleted_sync_records": sync_record_count,
                "deleted_change_logs": change_log_count,
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


@instances_bp.route("/api/batch-delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def batch_delete() -> str | Response | tuple[Response, int]:
    """批量删除实例"""
    try:
        data = request.get_json()
        instance_ids = data.get("instance_ids", [])

        if not instance_ids:
            raise ValidationError("请选择要删除的实例")

        # 检查是否有相关数据关联
        from app.models.account_change_log import AccountChangeLog
        from app.models.current_account_sync_data import CurrentAccountSyncData
        from app.models.sync_instance_record import SyncInstanceRecord

        related_data_counts = {}
        for instance_id in instance_ids:
            instance = Instance.query.get(instance_id)
            if instance:
                # 检查各种关联数据
                sync_data_count = CurrentAccountSyncData.query.filter_by(instance_id=instance_id).count()
                sync_record_count = SyncInstanceRecord.query.filter_by(instance_id=instance_id).count()
                change_log_count = AccountChangeLog.query.filter_by(instance_id=instance_id).count()

                total_related = sync_data_count + sync_record_count + change_log_count
                if total_related > 0:
                    related_data_counts[instance.name] = {
                        "sync_data": sync_data_count,
                        "sync_records": sync_record_count,
                        "change_logs": change_log_count,
                        "total": total_related,
                    }

        # 如果有相关数据，先删除关联数据，然后删除实例
        if related_data_counts:
            log_info(
                f"检测到 {len(related_data_counts)} 个实例有关联数据，将先删除关联数据",
                module="instances",
                user_id=current_user.id,
            )

        # 批量删除
        deleted_count = 0
        deleted_assignments = 0
        deleted_sync_data = 0
        deleted_sync_records = 0
        deleted_change_logs = 0

        for instance_id in instance_ids:
            instance = Instance.query.get(instance_id)
            if instance:
                # 记录操作日志
                log_info(
                    "批量删除数据库实例",
                    module="instances",
                    user_id=current_user.id,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    db_type=instance.db_type,
                    host=instance.host,
                )

                # 第一步：删除所有关联数据
                try:
                    stats = _delete_instance_related_data(instance.id, instance.name)
                except Exception as e:
                    log_error(f"删除实例 {instance.name} 关联数据失败: {e}", module="instances")
                    continue  # 跳过这个实例，继续处理其他实例

                # 第二步：最后删除实例本身
                try:
                    db.session.delete(instance)
                    deleted_count += 1

                    # 累计统计信息
                    deleted_assignments += stats["assignment_count"]
                    deleted_sync_data += stats["sync_data_count"]
                    deleted_sync_records += stats["sync_record_count"]
                    deleted_change_logs += stats["change_log_count"]
                except Exception as e:
                    log_error(f"删除实例 {instance.name} 失败: {e}", module="instances")
                    continue  # 跳过这个实例，继续处理其他实例

        db.session.commit()

        log_info(
            f"批量删除完成：{deleted_count} 个实例，{deleted_assignments} 个分类分配，{deleted_sync_data} 条同步数据，{deleted_sync_records} 条同步记录，{deleted_change_logs} 条变更日志",
            module="instances",
        )

        return jsonify_unified_success(
            data={
                "deleted_count": deleted_count,
                "deleted_assignments": deleted_assignments,
                "deleted_sync_data": deleted_sync_data,
                "deleted_sync_records": deleted_sync_records,
                "deleted_change_logs": deleted_change_logs,
                "instances_with_related_data": related_data_counts,
            },
            message=f"成功删除 {deleted_count} 个实例",
        )

    except Exception as e:
        db.session.rollback()
        log_error("批量删除实例失败", module="instances", exception=e)
        raise SystemError("批量删除实例失败") from e


@instances_bp.route("/api/batch-create", methods=["POST"])
@login_required
@create_required
@require_csrf
def batch_create() -> str | Response | tuple[Response, int]:
    """批量创建实例"""
    try:
        # 检查是否有文件上传
        if "file" in request.files:
            file = request.files["file"]
            if file and file.filename.endswith(".csv"):
                return _process_csv_file(file)
            raise ValidationError("请上传CSV格式文件")

        # 处理JSON格式（保持向后兼容）
        data = request.get_json()
        instances_data = data.get("instances", [])

        if not instances_data:
            raise ValidationError("请提供实例数据")

        return _process_instances_data(instances_data)

    except Exception as e:
        db.session.rollback()
        log_error("批量创建实例失败", module="instances", exception=e)
        raise SystemError("批量创建实例失败") from e


def _process_csv_file(file: Any) -> dict[str, Any] | Response | tuple[Response, int]:  # noqa: ANN401
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

        return _process_instances_data(instances_data)

    except Exception as e:
        raise ValidationError(f"CSV文件处理失败: {str(e)}") from e


def _process_instances_data(
    instances_data: list[dict[str, Any]],
) -> Response:
    """处理实例数据"""
    created_count = 0
    errors = []

    # 使用新的数据验证器进行批量验证
    valid_data, validation_errors = DataValidator.validate_batch_data(instances_data)
    
    # 添加验证错误到错误列表
    errors.extend(validation_errors)

    for i, instance_data in enumerate(valid_data):
        try:

            # 检查实例名称是否已存在
            existing_instance = Instance.query.filter_by(name=instance_data["name"]).first()
            if existing_instance:
                errors.append(f"第 {i + 1} 个实例名称已存在: {instance_data['name']}")
                continue

            # 处理端口号
            try:
                port = int(instance_data["port"])
            except (ValueError, TypeError):
                errors.append(f"第 {i + 1} 个实例端口号无效: {instance_data['port']}")
                continue

            # 处理凭据ID
            credential_id = None
            if instance_data.get("credential_id"):
                try:
                    credential_id = int(instance_data["credential_id"])
                except (ValueError, TypeError):
                    errors.append(f"第 {i + 1} 个实例凭据ID无效: {instance_data['credential_id']}")
                    continue

            # 创建实例
            instance = Instance(
                name=instance_data["name"],
                db_type=instance_data["db_type"],
                host=instance_data["host"],
                port=port,
                database_name=instance_data.get("database_name"),
                description=instance_data.get("description"),
                credential_id=credential_id,
                tags={},
            )

            db.session.add(instance)
            created_count += 1

            # 记录操作日志
            if current_user and hasattr(current_user, "id"):
                log_info(
                    "批量创建数据库实例",
                    module="instances",
                    user_id=current_user.id,
                    instance_name=instance.name,
                    db_type=instance.db_type,
                    host=instance.host,
                )

        except Exception as e:
            errors.append(f"第 {i + 1} 个实例创建失败: {str(e)}")
            continue

    if created_count > 0:
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            log_error("批量创建实例提交失败", module="instances", exception=exc)
            raise SystemError("批量创建实例失败") from exc

    message = f"成功创建 {created_count} 个实例"
    payload: dict[str, Any] = {
        "created_count": created_count,
    }
    if errors:
        payload["errors"] = errors

    return jsonify_unified_success(data=payload, message=message)


@instances_bp.route("/api/export")
@login_required
@view_required
def export_instances() -> Response:
    """导出实例数据为CSV"""
    import csv
    import io

    from flask import Response

    # 获取查询参数（与index方法保持一致）
    search = request.args.get("search", "", type=str)
    db_type = request.args.get("db_type", "", type=str)

    # 构建查询（与index方法保持一致）
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


    # 获取所有实例数据
    instances = query.all()

    # 创建CSV内容
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    writer.writerow(
        [
            "ID",
            "实例名称",
            "数据库类型",
            "主机地址",
            "端口",
            "数据库名",
            "标签",
            "状态",
            "描述",
            "凭据ID",
            "同步次数",
            "最后连接时间",
            "创建时间",
            "更新时间",
        ]
    )

    # 写入实例数据
    for instance in instances:
        # 格式化标签显示
        tags_display = ""
        if instance.tags:
            tags_display = ", ".join([tag.display_name for tag in instance.tags.all()])
        
        writer.writerow(
            [
                instance.id,
                instance.name,
                instance.db_type,
                instance.host,
                instance.port,
                instance.database_name or "",
                tags_display,
                "启用" if instance.is_active else "禁用",
                instance.description or "",
                instance.credential_id or "",
                instance.sync_count or 0,
                (time_utils.format_china_time(instance.last_connected) if instance.last_connected else ""),
                (time_utils.format_china_time(instance.created_at) if instance.created_at else ""),
                (time_utils.format_china_time(instance.updated_at) if instance.updated_at else ""),
            ]
        )

    # 创建响应
    output.seek(0)
    from app.utils.time_utils import TimeFormats
    timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
    filename = f"instances_export_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@instances_bp.route("/api/template/download")
@login_required
@view_required
def download_template() -> Response:
    """下载CSV模板"""
    import csv
    import io

    from flask import Response

    # 创建CSV内容
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    writer.writerow(
        [
            "name",
            "db_type",
            "host",
            "port",
            "database_name",
            "description",
            "credential_id",
        ]
    )

    # 写入示例数据
    writer.writerow(
        [
            "mysql-prod-01",
            "mysql",
            "192.168.1.100",
            "3306",
            "mysql",
            "生产环境MySQL主库",
            "1",
        ]
    )
    writer.writerow(
        [
            "mysql-dev-01",
            "mysql",
            "192.168.1.101",
            "3306",
            "mysql",
            "开发环境MySQL",
            "2",
        ]
    )
    writer.writerow(
        [
            "postgres-test-01",
            "postgresql",
            "192.168.1.102",
            "5432",
            "postgres",
            "测试环境PostgreSQL",
            "3",
        ]
    )

    # 创建响应
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=instances_template.csv"},
    )


@instances_bp.route("/api/<int:instance_id>/test", methods=["POST"])
@login_required
@view_required
@require_csrf
def test_connection(instance_id: int) -> str | Response | tuple[Response, int]:
    """测试数据库连接"""
    instance = Instance.query.get_or_404(instance_id)

    try:
        # 使用实例模型测试连接
        result = instance.test_connection()

        if result["success"]:
            # 更新最后连接时间
            instance.last_connected = time_utils.now()
            db.session.commit()
            return jsonify_unified_success(
                data={"result": result},
                message="连接测试成功",
            )

        raise SystemError("连接测试失败", extra={"result": result})

    except Exception as e:
        log_error(
            "测试连接失败",
            module="instances",
            instance_id=instance_id,
            exception=e,
        )
        raise SystemError("连接测试失败，请重试") from e




# API路由
@instances_bp.route("/api")
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


@instances_bp.route("/api/<int:instance_id>")
@login_required
@view_required
def api_detail(instance_id: int) -> Response:
    """获取实例详情API"""
    instance = Instance.query.get_or_404(instance_id)
    return jsonify_unified_success(
        data={"instance": instance.to_dict()},
        message="获取实例详情成功",
    )


@instances_bp.route("/api/<int:instance_id>/test")
@login_required
@view_required
def api_test_connection(instance_id: int) -> Response | tuple[Response, int]:
    """
    测试连接API（已弃用，请使用 /connections/api/test）
    
    为了向后兼容保留此API，建议迁移到新的连接管理API
    """
    # 重定向到新的连接管理API
    from flask import redirect, url_for
    return redirect(url_for('connections.test_connection', instance_id=instance_id))


# 注册额外路由模块
from . import instances_accounts  # noqa: E402
from . import instances_capacity  # noqa: E402
