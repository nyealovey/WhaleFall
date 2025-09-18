"""
泰摸鱼吧 - 账户统计路由
"""

import logging
from collections import defaultdict
from datetime import timedelta

from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import login_required

from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
)
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.instance import Instance

# 移除SyncData导入，使用新的同步会话模型
from app.utils.timezone import now

# 创建蓝图
account_static_bp = Blueprint("account_static", __name__)


@account_static_bp.route("/")
@login_required
def index() -> str:
    """账户统计首页"""
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


@account_static_bp.route("/account-statistics")
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


@account_static_bp.route("/api/statistics")
@login_required
def api_statistics() -> "Response":
    """API: 获取账户统计信息"""
    try:
        stats = get_account_statistics()
        return jsonify(stats)
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
        end_date = now()
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
