"""账户统计 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, case, distinct, func, or_

from app import db
from app.models.account_classification import AccountClassification, AccountClassificationAssignment, ClassificationRule
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount


class AccountStatisticsRepository:
    """账户统计读模型 Repository."""

    @staticmethod
    def fetch_classification_overview() -> dict[str, Any]:
        """获取账户分类概览统计."""
        rows = AccountStatisticsRepository._query_classification_rows()
        total_classified_accounts = 0
        for row in rows:
            count_value = row.get("count", 0)
            total_classified_accounts += int(count_value) if count_value is not None else 0
        auto_classified_accounts = AccountStatisticsRepository._query_auto_classified_count()
        return {
            "total": total_classified_accounts,
            "auto": auto_classified_accounts,
            "classifications": rows,
        }

    @staticmethod
    def fetch_summary(*, instance_id: int | None = None, db_type: str | None = None) -> dict[str, int]:
        """获取账户与实例汇总统计."""
        counts_query = (
            db.session.query(
                func.count(AccountPermission.id).label("total_accounts"),
                func.coalesce(
                    func.sum(case((InstanceAccount.is_active.is_(True), 1), else_=0)),
                    0,
                ).label("active_accounts"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    InstanceAccount.is_active.is_(True),
                                    AccountPermission.is_locked.is_(True),
                                ),
                                1,
                            ),
                            else_=0,
                        ),
                    ),
                    0,
                ).label("locked_accounts"),
            )
            .join(InstanceAccount, AccountPermission.instance_account_id == InstanceAccount.id)
            .join(Instance, Instance.id == AccountPermission.instance_id)
            .filter(Instance.is_active.is_(True), Instance.deleted_at.is_(None))
        )

        if instance_id is not None:
            counts_query = counts_query.filter(AccountPermission.instance_id == instance_id)

        if db_type:
            counts_query = counts_query.filter(AccountPermission.db_type == db_type)

        counts_row = counts_query.one()
        total_value = getattr(counts_row, "total_accounts", None)
        total_accounts = int(total_value) if total_value is not None else 0

        active_value = getattr(counts_row, "active_accounts", None)
        active_accounts = int(active_value) if active_value is not None else 0

        locked_value = getattr(counts_row, "locked_accounts", None)
        locked_accounts = int(locked_value) if locked_value is not None else 0

        deleted_accounts = max(total_accounts - active_accounts, 0)
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
        disabled_instances = active_instance_query.filter(Instance.is_active.is_(False)).count()
        deleted_instances = deleted_query.filter(Instance.deleted_at.isnot(None)).count()
        total_instances = active_instances + disabled_instances
        normal_instances = active_instances

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

    @staticmethod
    def fetch_db_type_stats() -> dict[str, dict[str, int]]:
        """获取按数据库类型统计."""
        target_db_types = ["mysql", "postgresql", "oracle", "sqlserver"]

        stats_query = (
            db.session.query(
                AccountPermission.db_type.label("db_type"),
                func.count(AccountPermission.id).label("total"),
                func.coalesce(
                    func.sum(case((InstanceAccount.is_active.is_(True), 1), else_=0)),
                    0,
                ).label("active"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    InstanceAccount.is_active.is_(True),
                                    AccountPermission.is_locked.is_(True),
                                ),
                                1,
                            ),
                            else_=0,
                        ),
                    ),
                    0,
                ).label("locked"),
            )
            .join(InstanceAccount, AccountPermission.instance_account_id == InstanceAccount.id)
            .join(Instance, Instance.id == AccountPermission.instance_id)
            .filter(Instance.is_active.is_(True), Instance.deleted_at.is_(None))
            .group_by(AccountPermission.db_type)
        )

        db_type_stats: dict[str, dict[str, int]] = {
            db_type: {"total": 0, "active": 0, "normal": 0, "locked": 0, "deleted": 0}
            for db_type in target_db_types
        }

        for row in stats_query.all():
            db_type = getattr(row, "db_type", None)
            if db_type not in db_type_stats:
                continue
            total = int(getattr(row, "total", 0) or 0)
            active = int(getattr(row, "active", 0) or 0)
            locked = int(getattr(row, "locked", 0) or 0)
            deleted = max(total - active, 0)
            normal = max(active - locked, 0)
            db_type_stats[db_type] = {
                "total": total,
                "active": active,
                "normal": normal,
                "locked": locked,
                "deleted": deleted,
            }

        return db_type_stats

    @staticmethod
    def fetch_classification_stats() -> dict[str, dict[str, Any]]:
        """获取按分类统计."""
        rows = AccountStatisticsRepository._query_classification_rows()
        classification_stats: dict[str, dict[str, Any]] = {}
        for row in rows:
            classification_stats[row["name"]] = {
                "account_count": row["count"],
                "display_name": row.get("display_name", row["name"]),
            }
        return classification_stats

    @staticmethod
    def fetch_rule_match_stats(rule_ids: Sequence[int] | None = None) -> dict[int, int]:
        """获取规则命中统计."""
        rule_query = ClassificationRule.query.filter(ClassificationRule.is_active.is_(True))
        if rule_ids:
            rule_query = rule_query.filter(ClassificationRule.id.in_(rule_ids))
        rules = rule_query.all()
        if not rules:
            return {}

        assignment_query = db.session.query(
            AccountClassificationAssignment.rule_id,
            func.count(distinct(AccountClassificationAssignment.account_id)).label("count"),
        ).filter(
            AccountClassificationAssignment.is_active.is_(True),
            AccountClassificationAssignment.rule_id.isnot(None),
        )

        if rule_ids:
            assignment_query = assignment_query.filter(AccountClassificationAssignment.rule_id.in_(rule_ids))

        assignment_rows = assignment_query.group_by(AccountClassificationAssignment.rule_id).all()
        assignment_map = {row.rule_id: row.count for row in assignment_rows if row.rule_id is not None}
        return {rule.id: int(assignment_map.get(rule.id, 0)) for rule in rules}

    @staticmethod
    def _query_classification_rows() -> list[dict[str, Any]]:
        display_name_column: Any = getattr(
            AccountClassification,
            "display_name",
            AccountClassification.code.label("display_name"),
        )

        rows = (
            db.session.query(
                AccountClassification.code,
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
                AccountPermission.instance_account_id == InstanceAccount.id,
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
                "name": code,
                "display_name": code if display_name in (None, "") else display_name,
                "priority": priority,
                "count": int(count),
            }
            for code, display_name, priority, count in rows
        ]

    @staticmethod
    def _query_auto_classified_count() -> int:
        scalar_value = (
            db.session.query(func.count(distinct(AccountClassificationAssignment.account_id)))
            .join(AccountPermission, AccountPermission.id == AccountClassificationAssignment.account_id)
            .join(InstanceAccount, AccountPermission.instance_account_id == InstanceAccount.id)
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
        )
        return int(scalar_value) if scalar_value is not None else 0
