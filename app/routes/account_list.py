"""
泰摸鱼吧 - 账户管理路由
"""

from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import current_user, login_required

from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.instance import Instance
from app.models.tag import Tag
from app.services.account_sync_service import account_sync_service
from app.utils.decorators import update_required, view_required
from app.utils.structlog_config import log_error
from app.utils.timezone import now

# 创建蓝图
account_list_bp = Blueprint("account_list", __name__)


@account_list_bp.route("/")
@account_list_bp.route("/<db_type>")
@login_required
@view_required
def list_accounts(db_type: str | None = None) -> str:
    """账户列表页面"""
    # 获取查询参数
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "").strip()
    instance_id = request.args.get("instance_id", type=int)
    is_locked = request.args.get("is_locked")
    is_superuser = request.args.get("is_superuser")
    plugin = request.args.get("plugin", "").strip()
    tags = request.args.getlist("tags")
    classification = request.args.get("classification", "").strip()

    # 构建查询
    query = CurrentAccountSyncData.query.filter_by(is_deleted=False)

    # 数据库类型过滤
    if db_type and db_type != "all":
        query = query.filter(CurrentAccountSyncData.db_type == db_type)

    # 实例过滤
    if instance_id:
        query = query.filter(CurrentAccountSyncData.instance_id == instance_id)

    # 搜索过滤
    if search:
        query = query.filter(CurrentAccountSyncData.username.contains(search))

    # 锁定状态过滤（使用is_active字段）
    if is_locked is not None:
        if is_locked == "true":
            # 查找 is_active = False 的记录（已锁定）
            query = query.filter(CurrentAccountSyncData.is_active.is_(False))
        elif is_locked == "false":
            # 查找 is_active = True 的记录（正常）
            query = query.filter(CurrentAccountSyncData.is_active.is_(True))

    # 超级用户过滤
    if is_superuser is not None:
        query = query.filter(CurrentAccountSyncData.is_superuser == (is_superuser == "true"))

    # 标签过滤 - 暂时禁用以避免500错误
    # if tags:
    #     try:
    #         # 通过实例的标签进行过滤，使用更简单的方式
    #         query = query.join(Instance).join(Instance.tags).filter(Tag.name.in_(tags))
    #     except Exception as e:
    #         log_error(
    #             "标签过滤失败",
    #             module="account_list",
    #             tags=tags,
    #             error=str(e),
    #         )
    #         # 如果标签过滤失败，继续执行但不进行标签过滤
    #         pass

    # 分类过滤
    if classification and classification != "all":
        from app.models.account_classification import AccountClassification, AccountClassificationAssignment

        # 通过分类分配表进行过滤
        query = (
            query.join(AccountClassificationAssignment)
            .join(AccountClassification)
            .filter(AccountClassification.id == classification, AccountClassificationAssignment.is_active.is_(True))
        )

    # 排序
    query = query.order_by(CurrentAccountSyncData.username.asc())

    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 获取实例列表用于过滤
    instances = Instance.query.filter_by(is_active=True).all()

    # 获取统计信息
    stats = {
        "total": CurrentAccountSyncData.query.filter_by(is_deleted=False).count(),
        "mysql": CurrentAccountSyncData.query.filter_by(db_type="mysql", is_deleted=False).count(),
        "postgresql": CurrentAccountSyncData.query.filter_by(db_type="postgresql", is_deleted=False).count(),
        "oracle": CurrentAccountSyncData.query.filter_by(db_type="oracle", is_deleted=False).count(),
        "sqlserver": CurrentAccountSyncData.query.filter_by(db_type="sqlserver", is_deleted=False).count(),
    }

    # 获取实际的分类选项
    from app.models.account_classification import AccountClassification

    classification_list = (
        AccountClassification.query.filter_by(is_active=True).order_by(AccountClassification.priority.desc()).all()
    )

    # 构建过滤选项
    filter_options = {
        "db_types": [
            {"value": "mysql", "label": "MySQL"},
            {"value": "postgresql", "label": "PostgreSQL"},
            {"value": "oracle", "label": "Oracle"},
            {"value": "sqlserver", "label": "SQL Server"},
        ],
        "classifications": [
            {"value": "all", "label": "全部分类"},
        ]
        + [{"value": str(c.id), "label": c.name} for c in classification_list],
        "all_tags": [],  # 暂时禁用以避免500错误
    }

    # 获取账户分类信息
    from app.models.account_classification import AccountClassificationAssignment

    classifications = {}
    if pagination.items:
        account_ids = [account.id for account in pagination.items]
        assignments = AccountClassificationAssignment.query.filter(
            AccountClassificationAssignment.account_id.in_(account_ids),
            AccountClassificationAssignment.is_active.is_(True),
        ).all()

        for assignment in assignments:
            if assignment.account_id not in classifications:
                classifications[assignment.account_id] = []
            classifications[assignment.account_id].append(
                {
                    "name": assignment.classification.name,
                    "color": assignment.classification.color,
                }
            )

    if request.is_json:
        return jsonify(
            {
                "accounts": [account.to_dict() for account in pagination.items],
                "pagination": {
                    "page": pagination.page,
                    "pages": pagination.pages,
                    "per_page": pagination.per_page,
                    "total": pagination.total,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                },
                "stats": stats,
                "instances": [instance.to_dict() for instance in instances],
            }
        )

    return render_template(
        "accounts/list.html",
        accounts=pagination,
        pagination=pagination,
        db_type=db_type or "all",
        current_db_type=db_type,
        search=search,
        instance_id=instance_id,
        is_locked=is_locked,
        is_superuser=is_superuser,
        plugin=plugin,
        selected_tags=tags,
        classification=classification,
        instances=instances,
        stats=stats,
        filter_options=filter_options,
        classifications=classifications,
    )


@account_list_bp.route("/export")
@login_required
@view_required
def export_accounts() -> "Response":
    """导出账户数据为CSV"""
    import csv
    import io

    from flask import Response

    # 获取查询参数（与list_accounts方法保持一致）
    db_type = request.args.get("db_type", type=str)
    search = request.args.get("search", "").strip()
    instance_id = request.args.get("instance_id", type=int)
    is_locked = request.args.get("is_locked")
    is_superuser = request.args.get("is_superuser")
    request.args.get("plugin", "").strip()
    request.args.getlist("tags")
    request.args.get("classification", "").strip()

    # 构建查询（与list_accounts方法保持一致）
    query = CurrentAccountSyncData.query.filter_by(is_deleted=False)

    # 数据库类型过滤
    if db_type and db_type != "all":
        query = query.filter(CurrentAccountSyncData.db_type == db_type)

    # 实例过滤
    if instance_id:
        query = query.filter(CurrentAccountSyncData.instance_id == instance_id)

    # 搜索过滤
    if search:
        query = query.filter(CurrentAccountSyncData.username.contains(search))

    # 锁定状态过滤（使用is_active字段）
    if is_locked is not None:
        if is_locked == "true":
            # 查找 is_active = False 的记录（已锁定）
            query = query.filter(CurrentAccountSyncData.is_active.is_(False))
        elif is_locked == "false":
            # 查找 is_active = True 的记录（正常）
            query = query.filter(CurrentAccountSyncData.is_active.is_(True))

    # 超级用户过滤
    if is_superuser is not None:
        query = query.filter(CurrentAccountSyncData.is_superuser == (is_superuser == "true"))

    # 排序
    query = query.order_by(CurrentAccountSyncData.username.asc())

    # 获取所有账户数据
    accounts = query.all()

    # 获取账户分类信息
    from app.models.account_classification import AccountClassificationAssignment

    classifications = {}
    if accounts:
        account_ids = [account.id for account in accounts]
        assignments = AccountClassificationAssignment.query.filter(
            AccountClassificationAssignment.account_id.in_(account_ids),
            AccountClassificationAssignment.is_active.is_(True),
        ).all()

        for assignment in assignments:
            if assignment.account_id not in classifications:
                classifications[assignment.account_id] = []
            classifications[assignment.account_id].append(assignment.classification.name)

    # 创建CSV内容
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头（与页面显示格式一致）
    writer.writerow(["名称", "实例名称", "IP地址", "标签", "数据库类型", "分类", "锁定状态"])

    # 写入账户数据
    for account in accounts:
        # 获取实例信息
        instance = Instance.query.get(account.instance_id) if account.instance_id else None

        # 获取分类信息
        account_classifications = classifications.get(account.id, [])
        classification_str = ", ".join(account_classifications) if account_classifications else "未分类"

        # 格式化用户名（与页面显示一致）
        if instance and instance.db_type in ["sqlserver", "oracle", "postgresql"]:
            username_display = account.username
        else:
            username_display = f"{account.username}@{account.instance.host if account.instance else '%'}"

        # 格式化锁定状态（与页面显示一致）
        is_locked = False
        if account.type_specific and isinstance(account.type_specific, dict):
            is_locked = account.is_locked_display  # 使用计算字段

        lock_status = ("已禁用" if instance and instance.db_type == "sqlserver" else "已锁定") if is_locked else "正常"

        # 格式化标签显示
        tags_display = ""
        if instance and instance.tags:
            tags_display = ", ".join([tag.display_name for tag in instance.tags.all()])

        writer.writerow(
            [
                username_display,
                instance.name if instance else "",
                instance.host if instance else "",
                tags_display,
                instance.db_type.upper() if instance else "",
                classification_str,
                lock_status,
            ]
        )

    # 创建响应
    output.seek(0)
    timestamp = now().strftime("%Y%m%d_%H%M%S")
    filename = f"accounts_export_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@account_list_bp.route("/sync/<int:instance_id>", methods=["POST"])
@login_required
@update_required
def sync_accounts(instance_id: int) -> "Response":
    """同步单个实例的账户"""
    try:
        instance = Instance.query.get_or_404(instance_id)

        # 使用统一的账户同步服务
        result = account_sync_service.sync_accounts(instance, sync_type="manual_single")

        if result["success"]:
            # 同步会话记录已通过sync_session_service管理，无需额外创建记录
            return jsonify(
                {
                    "success": True,
                    "message": result.get("message", "同步成功"),
                    "synced_count": result.get("synced_count", 0),
                }
            )
        # 同步会话记录已通过sync_session_service管理，无需额外创建记录

        return (
            jsonify(
                {
                    "success": False,
                    "error": result.get("error", "同步失败"),
                }
            ),
            400,
        )

    except Exception as e:
        # 记录详细的错误日志
        log_error(
            "同步账户失败",
            module="account_list",
            instance_id=instance_id,
            user_id=current_user.id if current_user else "unknown",
            error=str(e),
        )

        # 同步会话记录已通过sync_session_service管理，无需额外创建记录

        return (
            jsonify(
                {
                    "success": False,
                    "error": f"同步失败: {str(e)}",
                }
            ),
            500,
        )


@account_list_bp.route("/<int:account_id>/permissions")
@login_required
@view_required
def get_account_permissions(account_id: int) -> "Response":
    """获取账户权限详情"""
    try:
        account = CurrentAccountSyncData.query.get_or_404(account_id)
        instance = account.instance

        # 构建权限信息
        permissions = {
            "db_type": instance.db_type.upper(),
            "username": account.username,
            "is_superuser": account.is_superuser,
            "last_sync_time": (
                account.last_sync_time.strftime("%Y-%m-%d %H:%M:%S") if account.last_sync_time else "未知"
            ),
        }

        if instance.db_type == "mysql":
            permissions["global_privileges"] = account.global_privileges or []
            permissions["database_privileges"] = account.database_privileges or {}

        elif instance.db_type == "postgresql":
            permissions["predefined_roles"] = account.predefined_roles or []
            permissions["role_attributes"] = account.role_attributes or {}
            permissions["database_privileges_pg"] = account.database_privileges_pg or {}
            permissions["tablespace_privileges"] = account.tablespace_privileges or {}

        elif instance.db_type == "sqlserver":
            permissions["server_roles"] = account.server_roles or []
            permissions["server_permissions"] = account.server_permissions or []
            permissions["database_roles"] = account.database_roles or {}
            permissions["database_permissions"] = account.database_permissions or {}

        elif instance.db_type == "oracle":
            permissions["oracle_roles"] = account.oracle_roles or []
            permissions["system_privileges"] = account.system_privileges or []
            permissions["tablespace_privileges_oracle"] = account.tablespace_privileges_oracle or {}

        return jsonify(
            {
                "success": True,
                "permissions": permissions,
                "account": {
                    "id": account.id,
                    "username": account.username,
                    "instance_name": instance.name if instance else "未知实例",
                    "db_type": instance.db_type if instance else "",
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"获取权限失败: {str(e)}"}), 500


@account_list_bp.route("/<int:account_id>/change-history")
@login_required
@view_required
def get_account_change_history(account_id: int) -> "Response":
    """获取账户变更历史"""
    try:
        account = CurrentAccountSyncData.query.get_or_404(account_id)
        instance = account.instance

        from app.models.account_change_log import AccountChangeLog

        # 获取变更历史
        change_logs = (
            AccountChangeLog.query.filter_by(
                instance_id=account.instance_id,
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
                    "change_time": (log.change_time.strftime("%Y-%m-%d %H:%M:%S") if log.change_time else "未知"),
                    "status": log.status,
                    "message": log.message,
                    "privilege_diff": log.privilege_diff,
                    "other_diff": log.other_diff,
                    "session_id": log.session_id,
                }
            )

        return jsonify(
            {
                "success": True,
                "account": {
                    "id": account.id,
                    "username": account.username,
                    "db_type": instance.db_type if instance else "",
                },
                "history": history,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"获取变更历史失败: {str(e)}"}), 500


@account_list_bp.route("/api/sync/<int:instance_id>")
@login_required
@update_required
def api_sync_accounts(instance_id: int) -> "Response":
    """API: 同步单个实例的账户"""
    try:
        instance = Instance.query.get_or_404(instance_id)

        # 使用统一的账户同步服务
        result = account_sync_service.sync_accounts(instance, sync_type="manual_single")

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": f"同步失败: {str(e)}"}), 500
