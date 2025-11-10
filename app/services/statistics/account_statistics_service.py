"""
账户统计服务

将账户统计页面使用到的统计逻辑拆分为可复用的服务函数。
"""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import and_, distinct, func, or_

from app import db
from app.errors import SystemError
from app.constants import DatabaseType
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
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
        account_query = (
            AccountPermission.query.join(InstanceAccount, AccountPermission.instance_account)
            .join(Instance, Instance.id == AccountPermission.instance_id)
            .filter(Instance.is_active.is_(True), Instance.deleted_at.is_(None))
        )

        if instance_id is not None:
            account_query = account_query.filter(AccountPermission.instance_id == instance_id)

        if db_type:
            account_query = account_query.filter(AccountPermission.db_type == db_type)

        accounts = account_query.all()

        total_accounts = len(accounts)
        active_accounts = 0
        locked_accounts = 0
        for account in accounts:
            instance_account = account.instance_account
            if instance_account and instance_account.is_active:
                active_accounts += 1
                if _is_account_locked(account, account.db_type):
                    locked_accounts += 1
            # 非活跃账户视为已删除/停用，计入 total 但不计入 active

        deleted_accounts = total_accounts - active_accounts
        normal_accounts = max(active_accounts - locked_accounts, 0)

        base_instance_query = Instance.query
        deleted_query = Instance.query
        active_instance_query = base_instance_query.filter(Instance.deleted_at.is_(None))
        if db_type:
            active_instance_query = active_instance_query.filter(Instance.db_type == db_type)
            deleted_query = deleted_query.filter(Instance.db_type == db_type)

        if instance_id is not None:
            active_instance_query = active_instance_query.filter(Instance.id == instance_id)
            deleted_query = deleted_query.filter(Instance.id == instance_id)

        active_instances = active_instance_query.filter(Instance.is_active.is_(True)).count()
        disabled_instances = (
            active_instance_query.filter(Instance.is_active.is_(False)).count()
        )
        deleted_instances = deleted_query.filter(Instance.deleted_at.isnot(None)).count()
        total_instances = active_instances

        normal_instances = max(active_instances - disabled_instances, 0)

        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "locked_accounts": locked_accounts,
            "normal_accounts": normal_accounts,
            "deleted_accounts": deleted_accounts,
            "total_instances": total_instances,
            "active_instances": active_instances,
            "disabled_instances": disabled_instances,
            "normal_instances": normal_instances,
            "deleted_instances": deleted_instances,
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
                .join(Instance, Instance.id == AccountPermission.instance_id)
                .filter(Instance.is_active.is_(True), Instance.deleted_at.is_(None))
                .filter(AccountPermission.db_type == db_type)
                .all()
            )
            total_count = len(accounts)
            active_count = 0
            locked_count = 0
            for account in accounts:
                instance_account = account.instance_account
                if instance_account and instance_account.is_active:
                    active_count += 1
                    if _is_account_locked(account, db_type):
                        locked_count += 1

            deleted_count = total_count - active_count
            normal_count = max(active_count - locked_count, 0)

            db_type_stats[db_type] = {
                "total": total_count,
                "active": active_count,
                "normal": normal_count,
                "locked": locked_count,
                "deleted": deleted_count,
            }

        return db_type_stats
    except Exception as exc:  # noqa: BLE001
        log_error("获取数据库类型统计失败", module="account_statistics", exception=exc)
        raise SystemError("获取数据库类型统计失败") from exc


def fetch_classification_stats() -> dict[str, dict[str, Any]]:
    """按账户分类返回统计信息。"""
    try:
        rows = _query_classification_rows()
        classification_stats: dict[str, dict[str, Any]] = {}
        for row in rows:
            classification_stats[row["name"]] = {
                "account_count": row["count"],
                "color": row.get("color"),
                "display_name": row.get("display_name", row["name"]),
            }
        return classification_stats
    except Exception as exc:  # noqa: BLE001
        log_error("获取账户分类统计失败", module="account_statistics", exception=exc)
        raise SystemError("获取账户分类统计失败") from exc


def fetch_classification_overview() -> dict[str, Any]:
    """获取分类账户概览，供仪表盘等场景复用。"""
    try:
        rows = _query_classification_rows()
        total_classified_accounts = sum(row["count"] for row in rows)
        auto_classified_accounts = _query_auto_classified_count()
        return {
            "total": total_classified_accounts,
            "auto": auto_classified_accounts,
            "classifications": rows,
        }
    except Exception as exc:  # noqa: BLE001
        log_error("获取账户分类概览失败", module="account_statistics", exception=exc)
        raise SystemError("获取账户分类概览失败") from exc

def fetch_rule_match_stats(rule_ids: Sequence[int] | None = None) -> dict[int, int]:
    """
    统计每条规则所关联分类的账户数量。

    由于当前分配记录未直接存储 rule_id，统计基于
    AccountClassificationAssignment 中同分类的活跃记录。
    """
    try:
        query = (
            db.session.query(
                ClassificationRule.id.label("rule_id"),
                func.count(distinct(AccountClassificationAssignment.account_id)).label("count"),
            )
            .outerjoin(
                AccountClassificationAssignment,
                and_(
                    AccountClassificationAssignment.classification_id == ClassificationRule.classification_id,
                    AccountClassificationAssignment.is_active.is_(True),
                ),
            )
            .filter(ClassificationRule.is_active.is_(True))
        )

        if rule_ids:
            query = query.filter(ClassificationRule.id.in_(rule_ids))

        rows = query.group_by(ClassificationRule.id).all()
        stats = {row.rule_id: row.count for row in rows}

        if rule_ids:
            for rid in rule_ids:
                stats.setdefault(rid, 0)

        return stats
    except Exception as exc:  # noqa: BLE001
        log_error("获取规则匹配统计失败", module="account_statistics", exception=exc)
        raise SystemError("获取规则匹配统计失败") from exc


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
        "normal_accounts": 0,
        "deleted_accounts": 0,
        "database_instances": 0,
        "total_instances": 0,
        "active_instances": 0,
        "disabled_instances": 0,
        "normal_instances": 0,
        "deleted_instances": 0,
        "db_type_stats": {},
        "classification_stats": {},
    }


def _query_classification_rows() -> list[dict[str, Any]]:
    display_name_column = (
        AccountClassification.display_name
        if hasattr(AccountClassification, "display_name")
        else AccountClassification.name.label("display_name")
    )

    rows = (
        db.session.query(
            AccountClassification.name,
            AccountClassification.color,
            display_name_column,
            AccountClassification.priority,
            func.count(distinct(AccountClassificationAssignment.account_id)).label("count"),
        )
        .outerjoin(
            AccountClassificationAssignment,
            and_(
                AccountClassificationAssignment.classification_id == AccountClassification.id,
                AccountClassificationAssignment.is_active.is_(True),
            ),
        )
        .outerjoin(
            AccountPermission,
            AccountPermission.id == AccountClassificationAssignment.account_id,
        )
        .outerjoin(
            InstanceAccount,
            AccountPermission.instance_account,
        )
        .outerjoin(
            Instance,
            and_(
                Instance.id == AccountPermission.instance_id,
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
            ),
        )
        .filter(AccountClassification.is_active.is_(True))
        .filter(or_(InstanceAccount.is_active.is_(True), InstanceAccount.id.is_(None)))
        .group_by(AccountClassification.id)
        .order_by(AccountClassification.priority.desc())
        .all()
    )
    return [
        {
            "name": name,
            "color": color,
            "display_name": display_name or name,
            "priority": priority,
            "count": count or 0,
        }
        for name, color, display_name, priority, count in rows
    ]


def _query_auto_classified_count() -> int:
    return (
        db.session.query(func.count(distinct(AccountClassificationAssignment.account_id)))
        .join(AccountPermission, AccountPermission.id == AccountClassificationAssignment.account_id)
        .join(InstanceAccount, AccountPermission.instance_account)
        .join(
            Instance,
            and_(
                Instance.id == AccountPermission.instance_id,
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
            ),
        )
        .filter(
            AccountClassificationAssignment.is_active.is_(True),
            AccountClassificationAssignment.assignment_type == "auto",
        )
        .filter(InstanceAccount.is_active.is_(True))
        .scalar()
        or 0
    )
