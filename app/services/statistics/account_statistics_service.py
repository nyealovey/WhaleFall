"""
账户统计服务

将账户统计页面使用到的统计逻辑拆分为可复用的服务函数。
"""

from __future__ import annotations

from typing import Any
from collections.abc import Sequence

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
    """根据数据库类型判断账户是否锁定。

    Args:
        account: 账户权限对象。
        db_type: 数据库类型。

    Returns:
        如果账户被锁定返回 True，否则返回 False。

    """
    if account.is_locked is not None:
        return bool(account.is_locked)
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
    """获取账户汇总统计信息。

    统计账户总数、活跃数、锁定数、正常数、已删除数，以及关联的实例统计。
    可选择性地只统计指定实例或数据库类型的账户。

    Args:
        instance_id: 可选的实例 ID 筛选。
        db_type: 可选的数据库类型筛选，如 'mysql'、'postgresql'。

    Returns:
        包含账户和实例统计信息的字典，格式如下：
        {
            'total_accounts': 100,       # 账户总数
            'active_accounts': 85,       # 活跃账户数
            'locked_accounts': 10,       # 锁定账户数
            'normal_accounts': 75,       # 正常账户数
            'deleted_accounts': 15,      # 已删除账户数
            'total_instances': 10,       # 实例总数
            'active_instances': 8,       # 活跃实例数
            'disabled_instances': 2,     # 禁用实例数
            'normal_instances': 8,       # 正常实例数
            'deleted_instances': 0       # 已删除实例数
        }

    Raises:
        SystemError: 当数据库查询失败时抛出。

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
    except Exception as exc:
        log_error("获取账户统计汇总失败", module="account_statistics", exception=exc)
        raise SystemError("获取账户统计汇总失败") from exc


def fetch_db_type_stats() -> dict[str, dict[str, int]]:
    """按数据库类型返回账户统计信息。

    Returns:
        以数据库类型为键的字典，每个值包含该类型的账户统计，格式如下：
        {
            'mysql': {
                'total': 50,
                'active': 45,
                'normal': 40,
                'locked': 5,
                'deleted': 5
            },
            'postgresql': {...},
            ...
        }

    Raises:
        SystemError: 当数据库查询失败时抛出。

    """
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
    except Exception as exc:
        log_error("获取数据库类型统计失败", module="account_statistics", exception=exc)
        raise SystemError("获取数据库类型统计失败") from exc


def fetch_classification_stats() -> dict[str, dict[str, Any]]:
    """按账户分类返回统计信息。

    Returns:
        以分类名称为键的字典，每个值包含该分类的统计信息，格式如下：
        {
            'admin': {
                'account_count': 10,
                'color': '#ff0000',
                'display_name': '管理员'
            },
            'readonly': {...},
            ...
        }

    Raises:
        SystemError: 当数据库查询失败时抛出。

    """
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
    except Exception as exc:
        log_error("获取账户分类统计失败", module="account_statistics", exception=exc)
        raise SystemError("获取账户分类统计失败") from exc


def fetch_classification_overview() -> dict[str, Any]:
    """获取分类账户概览。

    Returns:
        包含分类账户概览的字典，格式如下：
        {
            'total': 100,              # 已分类账户总数
            'auto': 80,                # 自动分类账户数
            'classifications': [...]   # 分类详情列表
        }

    Raises:
        SystemError: 当数据库查询失败时抛出。

    """
    try:
        rows = _query_classification_rows()
        total_classified_accounts = sum(row["count"] for row in rows)
        auto_classified_accounts = _query_auto_classified_count()
        return {
            "total": total_classified_accounts,
            "auto": auto_classified_accounts,
            "classifications": rows,
        }
    except Exception as exc:
        log_error("获取账户分类概览失败", module="account_statistics", exception=exc)
        raise SystemError("获取账户分类概览失败") from exc

def fetch_rule_match_stats(rule_ids: Sequence[int] | None = None) -> dict[int, int]:
    """统计每条规则所关联的账户数量。

    Args:
        rule_ids: 可选的规则 ID 列表，如果提供则只统计这些规则。

    Returns:
        以规则 ID 为键、账户数量为值的字典，格式如下：
        {
            1: 50,   # 规则 1 关联 50 个账户
            2: 30,   # 规则 2 关联 30 个账户
            ...
        }

    Raises:
        SystemError: 当数据库查询失败时抛出。

    """
    try:
        rule_query = ClassificationRule.query.filter(ClassificationRule.is_active.is_(True))
        if rule_ids:
            rule_query = rule_query.filter(ClassificationRule.id.in_(rule_ids))
        rules = rule_query.all()
        if not rules:
            return {}

        assignment_query = (
            db.session.query(
                AccountClassificationAssignment.rule_id,
                func.count(distinct(AccountClassificationAssignment.account_id)).label("count"),
            )
            .filter(
                AccountClassificationAssignment.is_active.is_(True),
                AccountClassificationAssignment.rule_id.isnot(None),
            )
        )

        if rule_ids:
            assignment_query = assignment_query.filter(AccountClassificationAssignment.rule_id.in_(rule_ids))

        assignment_rows = assignment_query.group_by(AccountClassificationAssignment.rule_id).all()
        assignment_map = {row.rule_id: row.count for row in assignment_rows if row.rule_id is not None}

        return {rule.id: assignment_map.get(rule.id, 0) for rule in rules}
    except Exception as exc:
        log_error("获取规则匹配统计失败", module="account_statistics", exception=exc)
        raise SystemError("获取规则匹配统计失败") from exc


def build_aggregated_statistics() -> dict[str, Any]:
    """组装账户统计页面的完整数据。

    汇总账户的基本统计、数据库类型分布和分类统计。

    Returns:
        包含完整统计信息的字典，包含 fetch_summary、fetch_db_type_stats
        和 fetch_classification_stats 的所有字段。

    Raises:
        SystemError: 当数据库查询失败时抛出。

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
    """构造空的统计结果。

    Returns:
        所有统计值为 0 或空字典的字典，格式与 build_aggregated_statistics 返回值相同。

    """
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
    """查询账户分类统计行。

    查询所有活跃分类及其关联的账户数量，按优先级降序排列。

    Returns:
        分类统计行列表，每行包含分类名称、颜色、显示名称、优先级和账户数量。

    Raises:
        DatabaseError: 当数据库查询失败时抛出。

    """
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
    """查询自动分类的账户数量。

    统计通过规则自动分类的活跃账户数量。

    Returns:
        自动分类的账户数量。

    Raises:
        DatabaseError: 当数据库查询失败时抛出。

    """
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
