
"""
鲸落 - 账户管理路由
"""

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from app.constants import DatabaseType
from app.constants.filter_options import DATABASE_TYPES
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
)
from app.errors import SystemError
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.tag import Tag
from app.services.account_sync import account_sync_service
from app.utils.decorators import update_required, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils
from app.utils.query_filter_utils import get_active_tag_options, get_classification_options

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
    if not tags:
        raw_tags = request.args.get("tags", "")
        if raw_tags:
            tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    classification_param = request.args.get("classification", "").strip()
    classification_filter = classification_param if classification_param not in {"", "all"} else ""
    classification = classification_param

    from app.models.instance_account import InstanceAccount

    # 构建查询
    query = AccountPermission.query.join(InstanceAccount, AccountPermission.instance_account)

    # 数据库类型过滤
    if db_type and db_type != "all":
        query = query.filter(AccountPermission.db_type == db_type)

    # 实例过滤
    if instance_id:
        query = query.filter(AccountPermission.instance_id == instance_id)

    # 搜索过滤 - 支持用户名、实例名称、IP地址搜索
    if search:
        from app import db
        # 通过JOIN实例表来搜索实例名称和IP地址
        query = query.join(Instance, AccountPermission.instance_id == Instance.id)
        query = query.filter(
            db.or_(
                AccountPermission.username.contains(search),
                Instance.name.contains(search),
                Instance.host.contains(search)
            )
        )

    # 锁定状态过滤（基于 InstanceAccount.is_active）
    if is_locked is not None:
        if is_locked == "true":
            query = query.filter(InstanceAccount.is_active.is_(False))
        elif is_locked == "false":
            query = query.filter(InstanceAccount.is_active.is_(True))
    else:
        query = query.filter(InstanceAccount.is_active.is_(True))

    # 超级用户过滤
    if is_superuser is not None:
        query = query.filter(AccountPermission.is_superuser == (is_superuser == "true"))

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
    if classification_filter:
        from app.models.account_classification import AccountClassification, AccountClassificationAssignment

        try:
            # 将字符串转换为整数
            classification_id = int(classification_filter)
            
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
                classification=classification_filter,
                error=str(e),
            )
            # 如果转换失败，忽略分类过滤
            pass

    # 排序
    query = query.order_by(AccountPermission.username.asc())

    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 获取统计信息
    base_query = AccountPermission.query.join(InstanceAccount, AccountPermission.instance_account)
    base_query = base_query.filter(InstanceAccount.is_active.is_(True))
    stats = {
        "total": base_query.count(),
        "mysql": base_query.filter(AccountPermission.db_type == "mysql").count(),
        "postgresql": base_query.filter(AccountPermission.db_type == "postgresql").count(),
        "oracle": base_query.filter(AccountPermission.db_type == "oracle").count(),
        "sqlserver": base_query.filter(AccountPermission.db_type == "sqlserver").count(),
    }

    instances = Instance.query.filter_by(is_active=True).all()
    classification_options = [{"value": "all", "label": "全部分类"}] + get_classification_options()
    tag_options = get_active_tag_options()
    database_type_options = [
        {
            "value": item["name"],
            "label": item["display_name"],
            "icon": item.get("icon", "fa-database"),
            "color": item.get("color", "primary"),
        }
        for item in DATABASE_TYPES
    ]

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
                "filter_options": {
                    "db_types": database_type_options,
                    "classifications": classification_options,
                    "tags": tag_options,
                },
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
        instance_id=instance_id,
        is_locked=is_locked,
        is_superuser=is_superuser,
        plugin=plugin,
        selected_tags=tags,
        classification=classification,
        instances=instances,
        stats=stats,
        database_type_options=database_type_options,
        classification_options=classification_options,
        tag_options=tag_options,
        classifications=classifications,
        persist_query_args=persist_query_args,
    )


@account_bp.route("/api/<int:account_id>/permissions")
@login_required
@view_required
def get_account_permissions(account_id: int) -> tuple[Response, int]:
    """获取账户权限详情"""
    try:
        account = AccountPermission.query.get_or_404(account_id)
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
