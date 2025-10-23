"""
账户统计相关路由
"""

from collections import defaultdict
from datetime import timedelta
from typing import Any

from flask import Response, flash, render_template
from flask_login import login_required

from app.errors import SystemError
from app.models.account_classification import AccountClassification, AccountClassificationAssignment
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.instance import Instance
from app.routes.account import account_bp
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils


@account_bp.route("/statistics")
@login_required
@view_required
def statistics() -> str:
    """账户统计页面"""
    try:
        stats = get_account_statistics()
    except SystemError:
        stats = _empty_account_statistics()
        flash("获取账户统计信息失败，请稍后重试", "error")

    from app.models.sync_session import SyncSession

    recent_syncs = SyncSession.query.order_by(SyncSession.created_at.desc()).limit(10).all()
    instances = Instance.query.filter_by(is_active=True).all()

    return render_template(
        "accounts/statistics.html",
        stats=stats,
        recent_syncs=recent_syncs,
        recent_accounts=stats.get("recent_accounts", []),
        instances=instances,
    )


@account_bp.route("/api/statistics")
@login_required
@view_required
def statistics_api() -> tuple[Response, int]:
    """账户统计API"""
    try:
        stats = get_account_statistics()

        from app.models.sync_session import SyncSession

        recent_syncs = SyncSession.query.order_by(SyncSession.created_at.desc()).limit(10).all()
        instances = Instance.query.filter_by(is_active=True).all()

        return jsonify_unified_success(
            data={
                "stats": stats,
                "recent_syncs": [sync.to_dict() for sync in recent_syncs],
                "instances": [instance.to_dict() for instance in instances],
            },
            message="获取账户统计信息成功",
        )
    except SystemError:
        raise
    except Exception as exc:  # noqa: BLE001
        log_error("获取账户统计信息失败", module="account", exception=exc)
        raise SystemError("获取账户统计信息失败") from exc


def _empty_account_statistics() -> dict[str, Any]:
    """构建账户统计信息的空状态结果"""
    return {
        "total_accounts": 0,
        "active_accounts": 0,
        "locked_accounts": 0,
        "database_instances": 0,
        "total_instances": 0,
        "db_type_stats": {},
        "instance_stats": [],
        "classification_stats": {},
        "superuser_accounts": 0,
        "trend_data": [],
        "recent_accounts": [],
        "permission_stats": {},
        "accounts_with_permissions": 0,
    }


def get_account_statistics() -> dict[str, Any]:
    """获取账户统计信息"""
    try:
        total_accounts = CurrentAccountSyncData.query.filter_by(is_deleted=False).count()

        db_type_stats: dict[str, dict[str, int]] = {}
        for db_type in ["mysql", "postgresql", "oracle", "sqlserver"]:
            accounts = CurrentAccountSyncData.query.filter_by(db_type=db_type, is_deleted=False).all()
            total_count = len(accounts)
            active_count = 0
            locked_count = 0

            for account in accounts:
                is_locked = _is_account_locked(account, db_type)
                if is_locked:
                    locked_count += 1
                else:
                    active_count += 1

            db_type_stats[db_type] = {
                "total": total_count,
                "active": active_count,
                "locked": locked_count,
            }

        instance_stats = []
        instances = Instance.query.filter_by(is_active=True).all()
        for instance in instances:
            accounts = CurrentAccountSyncData.query.filter_by(instance_id=instance.id, is_deleted=False).all()
            total_count = len(accounts)
            active_count = 0
            locked_count = 0

            for account in accounts:
                is_locked = _is_account_locked(account, instance.db_type)
                if is_locked:
                    locked_count += 1
                else:
                    active_count += 1

            instance_stats.append(
                {
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                    "db_type": instance.db_type,
                    "total": total_count,
                    "active": active_count,
                    "locked": locked_count,
                }
            )

        classification_stats: dict[str, int] = {}
        classifications = AccountClassification.query.filter_by(is_active=True).all()
        for classification in classifications:
            assignment_count = AccountClassificationAssignment.query.filter_by(
                classification_id=classification.id,
                is_active=True,
            ).count()
            classification_stats[classification.name] = assignment_count

        all_accounts = CurrentAccountSyncData.query.filter_by(is_deleted=False).all()
        active_accounts = 0
        locked_accounts = 0
        for account in all_accounts:
            if _is_account_locked(account, account.db_type):
                locked_accounts += 1
            else:
                active_accounts += 1

        superuser_accounts = CurrentAccountSyncData.query.filter_by(is_superuser=True, is_deleted=False).count()
        database_instances = len(instances)

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

            trend_data.append({"date": time_utils.format_china_time(date, "%Y-%m-%d"), "count": count})

        recent_accounts_query = (
            CurrentAccountSyncData.query.join(Instance)
            .filter(CurrentAccountSyncData.is_deleted.is_(False))
            .order_by(CurrentAccountSyncData.sync_time.desc())
            .limit(10)
            .all()
        )

        recent_accounts = []
        for account in recent_accounts_query:
            recent_accounts.append(
                {
                    "id": account.id,
                    "username": account.username,
                    "instance_name": (account.instance.name if account.instance else "Unknown"),
                    "db_type": (account.instance.db_type if account.instance else "Unknown"),
                    "is_locked": account.is_locked_display,
                    "created_at": (account.sync_time.isoformat() if account.sync_time else None),
                    "last_login": None,
                }
            )

        permission_stats: defaultdict[str, int] = defaultdict(int)
        sync_data_with_permissions = CurrentAccountSyncData.query.filter(
            CurrentAccountSyncData.is_deleted.is_(False)
        ).all()

        for sync_data in sync_data_with_permissions:
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

        accounts_with_permissions = sum(permission_stats.values())

        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "locked_accounts": locked_accounts,
            "database_instances": database_instances,
            "total_instances": len(instances),
            "db_type_stats": db_type_stats,
            "instance_stats": instance_stats,
            "classification_stats": classification_stats,
            "superuser_accounts": superuser_accounts,
            "trend_data": trend_data,
            "recent_accounts": recent_accounts,
            "permission_stats": dict(permission_stats),
            "accounts_with_permissions": accounts_with_permissions,
        }

    except Exception as exc:  # noqa: BLE001
        log_error("获取账户统计信息失败", module="account", exception=exc)
        raise SystemError("获取账户统计信息失败") from exc


def _is_account_locked(account: CurrentAccountSyncData, db_type: str) -> bool:
    """根据数据库类型判断账户是否锁定"""
    if db_type == "mysql":
        return bool(account.type_specific and account.type_specific.get("is_locked"))
    if db_type == "postgresql":
        return bool(account.type_specific and not account.type_specific.get("can_login", True))
    if db_type == "oracle":
        return bool(account.type_specific and account.type_specific.get("account_status") == "LOCKED")
    if db_type == "sqlserver":
        return bool(account.type_specific and account.type_specific.get("is_locked"))
    return False
