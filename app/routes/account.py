
"""
鲸落 - 账户管理路由
"""

import logging
from collections import defaultdict
from datetime import timedelta

from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import current_user, login_required

from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
)
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.instance import Instance
from app.models.tag import Tag
from app.services.account_sync_service import account_sync_service
from app.utils.decorators import update_required, view_required
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils

# 创建蓝图
account_bp = Blueprint("account", __name__)


@account_bp.route("/")
@account_bp.route("/<db_type>")
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
    )


@account_bp.route("/api/export")
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
    timestamp = time_utils.now().strftime("%Y%m%d_%H%M%S")
    filename = f"accounts_export_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@account_bp.route("/api/<int:account_id>/permissions")
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


@account_bp.route("/api/<int:account_id>/change-history")
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


@account_bp.route("/statistics")
@login_required
@view_required
def statistics() -> str:
    """账户统计页面"""
    # 获取统计信息
    stats = get_account_statistics()

    # 获取最近同步记录 - 使用新的同步会话模型
    from app.models.sync_session import SyncSession

    recent_syncs = SyncSession.query.order_by(SyncSession.created_at.desc()).limit(10).all()

    # 获取实例列表
    instances = Instance.query.filter_by(is_active=True).all()

    if request.is_json:
        return jsonify(
            {
                "stats": stats,
                "recent_syncs": [sync.to_dict() for sync in recent_syncs],
                "instances": [instance.to_dict() for instance in instances],
            }
        )

    return render_template(
        "accounts/statistics.html",
        stats=stats,
        recent_syncs=recent_syncs,
        recent_accounts=stats.get("recent_accounts", []),  # 添加recent_accounts变量
        instances=instances,
    )


@account_bp.route("/api/account-statistics")
@login_required
def account_statistics() -> "Response":
    """账户统计API"""
    try:
        stats = get_account_statistics()
        return jsonify(
            {
                "success": True,
                "stats": stats,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": f"获取统计信息失败: {str(e)}"}), 500


def get_account_statistics() -> dict:
    """获取账户统计信息"""
    try:
        # 基础统计
        total_accounts = CurrentAccountSyncData.query.filter_by(is_deleted=False).count()

        # 按数据库类型统计（根据不同数据库类型使用不同的锁定判断标准）
        db_type_stats = {}
        for db_type in ["mysql", "postgresql", "oracle", "sqlserver"]:
            accounts = CurrentAccountSyncData.query.filter_by(db_type=db_type, is_deleted=False).all()
            total_count = len(accounts)
            active_count = 0
            locked_count = 0

            for account in accounts:
                is_locked = False
                
                if db_type == "mysql":
                    # MySQL使用is_locked字段
                    if account.type_specific and "is_locked" in account.type_specific:
                        is_locked = account.type_specific["is_locked"]
                elif db_type == "postgresql":
                    # PostgreSQL使用can_login字段，can_login=False表示锁定
                    if account.type_specific and "can_login" in account.type_specific:
                        is_locked = not account.type_specific["can_login"]
                elif db_type == "oracle":
                    # Oracle使用account_status字段，LOCKED表示锁定
                    if account.type_specific and "account_status" in account.type_specific:
                        is_locked = account.type_specific["account_status"] == "LOCKED"
                elif db_type == "sqlserver":
                    # SQL Server使用is_locked字段
                    if account.type_specific and "is_locked" in account.type_specific:
                        is_locked = account.type_specific["is_locked"]
                
                if is_locked:
                    locked_count += 1
                else:
                    active_count += 1

            db_type_stats[db_type] = {
                "total": total_count,
                "active": active_count,
                "locked": locked_count,
            }

        # 按实例统计（根据不同数据库类型使用不同的锁定判断标准）
        instance_stats = []
        instances = Instance.query.filter_by(is_active=True).all()
        for instance in instances:
            accounts = CurrentAccountSyncData.query.filter_by(instance_id=instance.id, is_deleted=False).all()
            total_count = len(accounts)
            active_count = 0
            locked_count = 0

            for account in accounts:
                is_locked = False
                
                if instance.db_type == "mysql":
                    # MySQL使用is_locked字段
                    if account.type_specific and "is_locked" in account.type_specific:
                        is_locked = account.type_specific["is_locked"]
                elif instance.db_type == "postgresql":
                    # PostgreSQL使用can_login字段，can_login=False表示锁定
                    if account.type_specific and "can_login" in account.type_specific:
                        is_locked = not account.type_specific["can_login"]
                elif instance.db_type == "oracle":
                    # Oracle使用account_status字段，LOCKED表示锁定
                    if account.type_specific and "account_status" in account.type_specific:
                        is_locked = account.type_specific["account_status"] == "LOCKED"
                elif instance.db_type == "sqlserver":
                    # SQL Server使用is_locked字段
                    if account.type_specific and "is_locked" in account.type_specific:
                        is_locked = account.type_specific["is_locked"]
                
                if is_locked:
                    locked_count += 1
                else:
                    active_count += 1

            instance_stats.append(
                {
                    "name": instance.name,
                    "db_type": instance.db_type,
                    "total_accounts": total_count,
                    "active_accounts": active_count,
                    "locked_accounts": locked_count,
                    "host": instance.host,
                }
            )

        # 移除按环境统计（已废弃环境字段）

        # 按分类统计（参考仪表盘逻辑，去重统计）
        from sqlalchemy import distinct

        classification_stats = {}
        classifications = (
            AccountClassification.query.filter_by(is_active=True).order_by(AccountClassification.priority.desc()).all()
        )
        for classification in classifications:
            # 使用去重统计，只统计活跃的分配
            assignment_count = (
                AccountClassificationAssignment.query.filter_by(classification_id=classification.id, is_active=True)
                .with_entities(distinct(AccountClassificationAssignment.account_id))
                .count()
            )
            classification_stats[classification.name] = {
                "classification_name": classification.name,
                "account_count": assignment_count,
                "color": classification.color,
            }

        # 按状态统计（根据不同数据库类型使用不同的锁定判断标准）
        all_accounts = CurrentAccountSyncData.query.filter_by(is_deleted=False).all()
        active_accounts = 0
        locked_accounts = 0
        
        for account in all_accounts:
            is_locked = False
            
            if account.db_type == "mysql":
                # MySQL使用is_locked字段
                if account.type_specific and "is_locked" in account.type_specific:
                    is_locked = account.type_specific["is_locked"]
            elif account.db_type == "postgresql":
                # PostgreSQL使用can_login字段，can_login=False表示锁定
                if account.type_specific and "can_login" in account.type_specific:
                    is_locked = not account.type_specific["can_login"]
            elif account.db_type == "oracle":
                # Oracle使用account_status字段，LOCKED表示锁定
                if account.type_specific and "account_status" in account.type_specific:
                    is_locked = account.type_specific["account_status"] == "LOCKED"
            elif account.db_type == "sqlserver":
                # SQL Server使用is_locked字段
                if account.type_specific and "is_locked" in account.type_specific:
                    is_locked = account.type_specific["is_locked"]
            
            if is_locked:
                locked_accounts += 1
            else:
                active_accounts += 1

        superuser_accounts = CurrentAccountSyncData.query.filter_by(is_superuser=True, is_deleted=False).count()
        database_instances = len(instances)  # 数据库实例数

        # 最近7天新增账户趋势
        end_date = time_utils.now()
        start_date = end_date - timedelta(days=7)

        trend_data = []
        for i in range(7):
            date = start_date + timedelta(days=i)
            next_date = date + timedelta(days=1)

            count = CurrentAccountSyncData.query.filter(
                CurrentAccountSyncData.sync_time >= date,
                CurrentAccountSyncData.sync_time < next_date,
                CurrentAccountSyncData.is_deleted.is_(False),
            ).count()

            trend_data.append({"date": date.strftime("%Y-%m-%d"), "count": count})

        # 最近账户活动 - 获取最近同步的10个账户
        recent_accounts_query = (
            CurrentAccountSyncData.query.join(Instance)
            .filter(CurrentAccountSyncData.is_deleted.is_(False))
            .order_by(CurrentAccountSyncData.sync_time.desc())
            .limit(10)
            .all()
        )

        # 转换为字典格式
        recent_accounts = []
        for account in recent_accounts_query:
            recent_accounts.append(
                {
                    "id": account.id,
                    "username": account.username,
                    "instance_name": (account.instance.name if account.instance else "Unknown"),
                    "db_type": (account.instance.db_type if account.instance else "Unknown"),
                    "is_locked": account.is_locked_display,  # 使用计算字段
                    "created_at": (account.sync_time.isoformat() if account.sync_time else None),
                    "last_login": None,  # CurrentAccountSyncData模型中没有last_login字段
                }
            )

        # 按权限类型统计 - 使用新的优化同步模型
        permission_stats = defaultdict(int)

        # 从CurrentAccountSyncData获取权限统计
        sync_data_with_permissions = CurrentAccountSyncData.query.filter(
            CurrentAccountSyncData.is_deleted.is_(False)
        ).all()

        for sync_data in sync_data_with_permissions:
            # 根据数据库类型统计权限
            if sync_data.db_type == "mysql":
                if sync_data.global_privileges:
                    permission_stats["global_privileges"] += 1
                if sync_data.database_privileges:
                    permission_stats["database_privileges"] += 1
            elif sync_data.db_type == "postgresql":
                if sync_data.role_attributes:
                    permission_stats["role_attributes"] += 1
                if sync_data.database_privileges_pg:
                    permission_stats["database_privileges"] += 1
            elif sync_data.db_type == "sqlserver":
                if sync_data.server_roles:
                    permission_stats["server_roles"] += 1
                if sync_data.database_roles:
                    permission_stats["database_roles"] += 1
            elif sync_data.db_type == "oracle":
                if sync_data.oracle_roles:
                    permission_stats["roles"] += 1
                if sync_data.system_privileges:
                    permission_stats["system_privileges"] += 1

        # 统计CurrentAccountSyncData模型中的基础权限字段
        superuser_count = CurrentAccountSyncData.query.filter_by(is_superuser=True, is_deleted=False).count()
        # can_grant字段在CurrentAccountSyncData中不存在，跳过

        permission_stats["superuser"] = superuser_count
        permission_stats["can_grant"] = 0  # CurrentAccountSyncData模型中没有can_grant字段

        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "locked_accounts": locked_accounts,
            "database_instances": database_instances,
            "total_instances": database_instances,  # 添加别名以兼容模板
            "db_type_stats": db_type_stats,
            "instance_stats": instance_stats,
            "classification_stats": classification_stats,
            "superuser_accounts": superuser_accounts,
            "trend_data": trend_data,
            "recent_accounts": recent_accounts,
            "permission_stats": dict(permission_stats),
            "accounts_with_permissions": len(sync_data_with_permissions),
        }

    except Exception as e:
        logging.error("获取账户统计信息失败: %s", e)
        return {
            "total_accounts": 0,
            "active_accounts": 0,
            "locked_accounts": 0,
            "database_instances": 0,
            "total_instances": 0,  # 添加别名以兼容模板
            "db_type_stats": {},
            "instance_stats": [],
            "classification_stats": {},
            "superuser_accounts": 0,
            "trend_data": [],
            "recent_accounts": [],
            "permission_stats": {},
            "accounts_with_permissions": 0,
        }


