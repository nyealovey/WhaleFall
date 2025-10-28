
"""
鲸落 - 账户管理路由
"""

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from app.constants import DatabaseType
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
)
from app.errors import SystemError
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.instance import Instance
from app.models.tag import Tag
from app.services.account_sync_adapters.account_sync_service import account_sync_service
from app.utils.decorators import update_required, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils

# 创建蓝图
account_bp = Blueprint("account", __name__)


@account_bp.route("/")
@account_bp.route("/<db_type>")
@login_required
@view_required
def list_accounts(db_type: str | None = None) -> str | tuple[Response, int]:
    """账户列表页面"""
    # 获取查询参数
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "").strip()
    instance_id = request.args.get("instance_id", type=int)
    is_locked = request.args.get("is_locked")
    is_superuser = request.args.get("is_superuser")
    plugin = request.args.get("plugin", "").strip()
    tags = [tag for tag in request.args.getlist("tags") if tag.strip()]
    classification = request.args.get("classification", "").strip()

    # 构建查询
    query = CurrentAccountSyncData.query.filter_by(is_deleted=False)

    # 数据库类型过滤
    if db_type and db_type != "all":
        query = query.filter(CurrentAccountSyncData.db_type == db_type)

    # 实例过滤
    if instance_id:
        query = query.filter(CurrentAccountSyncData.instance_id == instance_id)

    # 搜索过滤 - 支持用户名、实例名称、IP地址搜索
    if search:
        from app import db
        # 通过JOIN实例表来搜索实例名称和IP地址
        query = query.join(Instance, CurrentAccountSyncData.instance_id == Instance.id)
        query = query.filter(
            db.or_(
                CurrentAccountSyncData.username.contains(search),
                Instance.name.contains(search),
                Instance.host.contains(search)
            )
        )

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

    # 标签过滤
    if tags:
        try:
            # 通过实例的标签进行过滤
            query = query.join(Instance).join(Instance.tags).filter(Tag.name.in_(tags))
            # 应用标签过滤
        except Exception as e:
            log_error(
                "标签过滤失败",
                module="account",
                tags=tags,
                error=str(e),
            )
            # 如果标签过滤失败，继续执行但不进行标签过滤
            pass
    # 标签过滤逻辑

    # 分类过滤 - 使用分配表查询（现在分配表数据是准确的）
    if classification and classification != "all":
        from app.models.account_classification import AccountClassification, AccountClassificationAssignment

        try:
            # 将字符串转换为整数
            classification_id = int(classification)
            
            # 通过分类分配表进行过滤
            query = (
                query.join(AccountClassificationAssignment)
                .join(AccountClassification)
                .filter(AccountClassification.id == classification_id, AccountClassificationAssignment.is_active.is_(True))
            )
                
        except (ValueError, TypeError) as e:
            log_error(
                "分类ID转换失败",
                module="account",
                classification=classification,
                error=str(e),
            )
            # 如果转换失败，忽略分类过滤
            pass

    # 排序
    query = query.order_by(CurrentAccountSyncData.username.asc())

    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 获取实例列表用于过滤
    instances = Instance.query.filter_by(is_active=True).all()
    
    # 获取分类列表用于筛选
    from app.models.account_classification import AccountClassification
    classifications_list = AccountClassification.query.filter_by(is_active=True).order_by(AccountClassification.priority.desc(), AccountClassification.name.asc()).all()

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
        "all_tags": Tag.query.all(),
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
                    "color": assignment.classification.color_value,  # 使用实际颜色值
                }
            )

    if request.is_json:
        return jsonify_unified_success(
            data={
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
            },
            message="获取账户列表成功",
        )

    persist_query_args = request.args.to_dict(flat=False)
    persist_query_args.pop("page", None)

    return render_template(
        "accounts/list.html",
        accounts=pagination,
        pagination=pagination,
        db_type=db_type or "all",
        current_db_type=db_type,
        search=search,
        search_value=search,
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
        classifications_list=classifications_list,
        persist_query_args=persist_query_args,
    )


@account_bp.route("/api/<int:account_id>/permissions")
@login_required
@view_required
def get_account_permissions(account_id: int) -> tuple[Response, int]:
    """获取账户权限详情"""
    try:
        account = CurrentAccountSyncData.query.get_or_404(account_id)
        instance = account.instance

        # 构建权限信息
        permissions = {
            "db_type": instance.db_type.upper() if instance else "",
            "username": account.username,
            "is_superuser": account.is_superuser,
            "last_sync_time": (
                time_utils.format_china_time(account.last_sync_time) if account.last_sync_time else "未知"
            ),
        }

        if instance and instance.db_type == DatabaseType.MYSQL:
            permissions["global_privileges"] = account.global_privileges or []
            permissions["database_privileges"] = account.database_privileges or {}

        elif instance and instance.db_type == DatabaseType.POSTGRESQL:
            permissions["predefined_roles"] = account.predefined_roles or []
            permissions["role_attributes"] = account.role_attributes or {}
            permissions["database_privileges_pg"] = account.database_privileges_pg or {}
            permissions["tablespace_privileges"] = account.tablespace_privileges or {}

        elif instance and instance.db_type == DatabaseType.SQLSERVER:
            permissions["server_roles"] = account.server_roles or []
            permissions["server_permissions"] = account.server_permissions or []
            permissions["database_roles"] = account.database_roles or {}
            permissions["database_permissions"] = account.database_permissions or {}

        elif instance and instance.db_type == DatabaseType.ORACLE:
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

    except Exception as exc:
        log_error(
            "获取账户权限失败",
            module="account",
            account_id=account_id,
            exception=exc,
        )
        raise SystemError("获取账户权限失败") from exc


# 注册统计相关路由
from . import account_stat  # noqa: E402  pylint: disable=wrong-import-position
