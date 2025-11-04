"""
账户统计服务

将账户统计页面使用到的统计逻辑拆分为可复用的服务函数。
"""

from __future__ import annotations

from typing import Any

from app.errors import SystemError
from app.constants import DatabaseType
from app.models.account_classification import AccountClassification, AccountClassificationAssignment
from app.models.account_permission import AccountPermission
from app.models.instance_account import InstanceAccount
from app.models.instance import Instance
from app.utils.structlog_config import log_error


def _is_account_locked(account: AccountPermission, db_type: str) -> bool:
    """根据数据库类型判断账户是否锁定"""
    if account.instance_account and account.instance_account.is_active is False:
        return True
    if db_type == DatabaseType.MYSQL:
        return bool(account.type_specific and account.type_specific.get("is_locked"))
    if db_type == DatabaseType.POSTGRESQL:
        return bool(account.type_specific and not account.type_specific.get("can_login", True))
    if db_type == DatabaseType.ORACLE:
        return bool(account.type_specific and account.type_specific.get("account_status") == "LOCKED")
    if db_type == DatabaseType.SQLSERVER:
        return bool(account.type_specific and account.type_specific.get("is_locked"))
    return False


def fetch_summary(*, instance_id: int | None = None, db_type: str | None = None) -> dict[str, int]:
    """
    获取汇总统计信息。

    Args:
        instance_id: 可选的实例过滤条件。
        db_type: 可选的数据库类型过滤条件。
    """
    try:
        query = AccountPermission.query.join(InstanceAccount, AccountPermission.instance_account)
        query = query.filter(InstanceAccount.is_active.is_(True))

        if instance_id is not None:
            query = query.filter(AccountPermission.instance_id == instance_id)

        if db_type:
            query = query.filter(AccountPermission.db_type == db_type)

        accounts = query.all()

        active_accounts = 0
        locked_accounts = 0
        for account in accounts:
            if _is_account_locked(account, account.db_type):
                locked_accounts += 1
            else:
                active_accounts += 1

        instance_query = Instance.query.filter_by(is_active=True)
        if db_type:
            instance_query = instance_query.filter(Instance.db_type == db_type)

        if instance_id is not None:
            instance_query = instance_query.filter(Instance.id == instance_id)

        instances = instance_query.all()

        return {
            "total_accounts": len(accounts),
            "active_accounts": active_accounts,
            "locked_accounts": locked_accounts,
            "total_instances": len(instances),
        }
    except Exception as exc:  # noqa: BLE001
        log_error("获取账户统计汇总失败", module="account_statistics", exception=exc)
        raise SystemError("获取账户统计汇总失败") from exc


def fetch_db_type_stats() -> dict[str, dict[str, int]]:
    """按数据库类型返回账户统计信息。"""
    try:
        db_type_stats: dict[str, dict[str, int]] = {}
        for db_type in ["mysql", "postgresql", "oracle", "sqlserver"]:
            accounts = (
                AccountPermission.query.join(InstanceAccount, AccountPermission.instance_account)
                .filter(InstanceAccount.is_active.is_(True))
                .filter(AccountPermission.db_type == db_type)
                .all()
            )
            total_count = len(accounts)
            active_count = 0
            locked_count = 0

            for account in accounts:
                if _is_account_locked(account, db_type):
                    locked_count += 1
                else:
                    active_count += 1

            db_type_stats[db_type] = {
                "total": total_count,
                "active": active_count,
                "locked": locked_count,
            }

        return db_type_stats
    except Exception as exc:  # noqa: BLE001
        log_error("获取数据库类型统计失败", module="account_statistics", exception=exc)
        raise SystemError("获取数据库类型统计失败") from exc


def fetch_classification_stats() -> dict[str, dict[str, Any]]:
    """按账户分类返回统计信息。"""
    try:
        classification_stats: dict[str, dict[str, Any]] = {}
        classifications = AccountClassification.query.filter_by(is_active=True).all()

        for classification in classifications:
            assignment_count = AccountClassificationAssignment.query.filter_by(
                classification_id=classification.id,
                is_active=True,
            ).count()

            classification_stats[classification.name] = {
                "account_count": assignment_count,
                "color": getattr(classification, "color", None),
                "display_name": getattr(classification, "display_name", classification.name),
            }

        return classification_stats
    except Exception as exc:  # noqa: BLE001
        log_error("获取账户分类统计失败", module="account_statistics", exception=exc)
        raise SystemError("获取账户分类统计失败") from exc


def build_aggregated_statistics() -> dict[str, Any]:
    """
    组装账户统计页面需要的完整数据。

    供模板渲染使用，内部调用细分的统计函数。
    """
    summary = fetch_summary()
    db_type_stats = fetch_db_type_stats()
    classification_stats = fetch_classification_stats()

    return {
        **summary,
        "database_instances": summary.get("total_instances", 0),
        "db_type_stats": db_type_stats,
        "classification_stats": classification_stats,
    }


def empty_statistics() -> dict[str, Any]:
    """构造空的统计结果，保证模板渲染不出错。"""
    return {
        "total_accounts": 0,
        "active_accounts": 0,
        "locked_accounts": 0,
        "database_instances": 0,
        "total_instances": 0,
        "db_type_stats": {},
        "classification_stats": {},
    }
