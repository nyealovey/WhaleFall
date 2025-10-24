"""
实例详情相关接口
"""

from datetime import date
from typing import Any, Dict, Optional

from flask import Response, request
from flask_login import login_required
from sqlalchemy import text

from app import db
from app.errors import SystemError, ValidationError
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.routes.database_stats import database_stats_bp
from app.routes.instances import instances_bp
from app.services.account_sync_adapters.account_data_manager import AccountDataManager
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error
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


@instances_bp.route("/api/<int:instance_id>/accounts")
@login_required
@view_required
def api_get_accounts(instance_id: int) -> Response:
    """获取实例账户数据API"""
    instance = Instance.query.get_or_404(instance_id)

    include_deleted = request.args.get("include_deleted", "false").lower() == "true"

    try:
        accounts = AccountDataManager.get_accounts_by_instance(instance_id, include_deleted=include_deleted)

        account_data = []
        for account in accounts:
            type_specific = account.type_specific or {}

            account_info = {
                "id": account.id,
                "username": account.username,
                "is_superuser": account.is_superuser,
                "is_locked": not account.is_active,
                "is_deleted": account.is_deleted,
                "last_change_time": account.last_change_time.isoformat() if account.last_change_time else None,
                "type_specific": type_specific,
                "server_roles": account.server_roles or [],
                "server_permissions": account.server_permissions or [],
                "database_roles": account.database_roles or {},
                "database_permissions": account.database_permissions or {},
            }

            if instance.db_type == "mysql":
                account_info.update({"host": type_specific.get("host", "%"), "plugin": type_specific.get("plugin", "")})
            elif instance.db_type == "sqlserver":
                account_info.update({"password_change_time": type_specific.get("password_change_time")})
            elif instance.db_type == "oracle":
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


@instances_bp.route("/api/<int:instance_id>/accounts/<int:account_id>/permissions")
@login_required
@view_required
def get_account_permissions(instance_id: int, account_id: int) -> dict[str, Any] | Response | tuple[Response, int]:
    """获取账户权限详情"""
    instance = Instance.query.get_or_404(instance_id)

    from app.models.current_account_sync_data import CurrentAccountSyncData

    account = CurrentAccountSyncData.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

    try:
        permissions = {
            "数据库类型": instance.db_type.upper(),
            "用户名": account.username,
            "超级用户": "是" if account.is_superuser else "否",
            "最后同步时间": (
                time_utils.format_china_time(account.last_sync_time) if account.last_sync_time else "未知"
            ),
        }

        if instance.db_type == "mysql":
            if account.global_privileges:
                permissions["global_privileges"] = account.global_privileges
            if account.database_privileges:
                permissions["database_privileges"] = account.database_privileges

        elif instance.db_type == "postgresql":
            if account.predefined_roles:
                permissions["predefined_roles"] = account.predefined_roles
            if account.role_attributes:
                permissions["role_attributes"] = account.role_attributes
            if account.database_privileges_pg:
                permissions["database_privileges_pg"] = account.database_privileges_pg

        elif instance.db_type == "sqlserver":
            if account.server_roles:
                permissions["server_roles"] = account.server_roles
            if account.server_permissions:
                permissions["server_permissions"] = account.server_permissions
            if account.database_roles:
                permissions["database_roles"] = account.database_roles
            if account.database_permissions:
                permissions["database_permissions"] = account.database_permissions

        elif instance.db_type == "oracle":
            if account.oracle_roles:
                permissions["oracle_roles"] = account.oracle_roles
            if account.system_privileges:
                permissions["system_privileges"] = account.system_privileges
            if account.tablespace_privileges_oracle:
                permissions["tablespace_privileges_oracle"] = account.tablespace_privileges_oracle

        return jsonify_unified_success(
            data={
                "account": {
                    "id": account.id,
                    "username": account.username,
                    "host": getattr(account, "host", None),
                    "plugin": getattr(account, "plugin", None),
                    "db_type": instance.db_type,
                },
                "permissions": permissions,
            },
            message="获取权限详情成功",
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
