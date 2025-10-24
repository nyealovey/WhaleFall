
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







# 注册额外路由模块
from . import instances_detail  # noqa: E402
from . import instances_capacity  # noqa: E402
