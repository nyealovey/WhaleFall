"""账户统计 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, case, distinct, func, or_

from app import db
from app.constants import DatabaseType
from app.models.account_classification import AccountClassification, AccountClassificationAssignment
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount


class AccountStatisticsRepository:
    """账户统计读模型 Repository."""

    @staticmethod
    def fetch_summary(*, instance_id: int | None = None, db_type: str | None = None) -> dict[str, int]:
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
        total_accounts = int(getattr(counts_row, "total_accounts", 0) or 0)
        active_accounts = int(getattr(counts_row, "active_accounts", 0) or 0)
        locked_accounts = int(getattr(counts_row, "locked_accounts", 0) or 0)

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

    @staticmethod
    def fetch_db_type_stats() -> dict[str, dict[str, int]]:
        db_type_stats: dict[str, dict[str, int]] = {}
        for db_type in ["mysql", "postgresql", "oracle", "sqlserver"]:
            accounts = (
                AccountPermission.query.join(InstanceAccount, AccountPermission.instance_account_id == InstanceAccount.id)
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
                    if AccountStatisticsRepository._is_account_locked(account, db_type):
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

    @staticmethod
    def fetch_classification_stats() -> dict[str, dict[str, Any]]:
        rows = AccountStatisticsRepository._query_classification_rows()
        classification_stats: dict[str, dict[str, Any]] = {}
        for row in rows:
            classification_stats[row["name"]] = {
                "account_count": row["count"],
                "color": row.get("color"),
                "display_name": row.get("display_name", row["name"]),
            }
        return classification_stats

    @staticmethod
    def _is_account_locked(account: AccountPermission, db_type: str) -> bool:
        is_locked = getattr(account, "is_locked", None)
        if is_locked is not None:
            return bool(is_locked)

        type_specific = getattr(account, "type_specific", None)
        if db_type == DatabaseType.MYSQL:
            return bool(type_specific and type_specific.get("is_locked"))
        if db_type == DatabaseType.POSTGRESQL:
            return bool(type_specific and not type_specific.get("can_login", True))
        if db_type == DatabaseType.ORACLE:
            return bool(type_specific and type_specific.get("account_status") == "LOCKED")
        if db_type == DatabaseType.SQLSERVER:
            return bool(type_specific and type_specific.get("is_locked"))
        return False

    @staticmethod
    def _query_classification_rows() -> list[dict[str, Any]]:
        display_name_column: Any = getattr(
            AccountClassification,
            "display_name",
            AccountClassification.name.label("display_name"),
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
                "name": name,
                "color": color,
                "display_name": display_name or name,
                "priority": priority,
                "count": count or 0,
            }
            for name, color, display_name, priority, count in rows
        ]
