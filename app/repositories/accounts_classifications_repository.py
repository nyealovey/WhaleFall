"""账户分类管理 Repository.

职责:
- 负责 Query 组装与数据库读取（read）
- 负责写操作的数据落库（add/delete/flush）（write）
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import distinct, func
from sqlalchemy.orm import Query, joinedload

from app import db
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.models.permission_config import PermissionConfig


class AccountsClassificationsRepository:
    """账户分类管理查询 Repository."""

    def fetch_active_classifications(self) -> list[AccountClassification]:
        return (
            AccountClassification.query.filter_by(is_active=True)
            .order_by(
                AccountClassification.priority.desc(),
                AccountClassification.created_at.desc(),
            )
            .all()
        )

    def fetch_rule_counts(self, classification_ids: Sequence[int]) -> dict[int, int]:
        if not classification_ids:
            return {}

        rows = (
            db.session.query(
                ClassificationRule.classification_id,
                func.count(ClassificationRule.id),
            )
            .filter(
                ClassificationRule.is_active.is_(True),
                ClassificationRule.classification_id.in_(classification_ids),
            )
            .group_by(ClassificationRule.classification_id)
            .all()
        )
        return {classification_id: int(count) for classification_id, count in rows}

    def fetch_active_rules(
        self,
        *,
        classification_id: int | None = None,
        db_type: str | None = None,
    ) -> list[ClassificationRule]:
        query = ClassificationRule.query.options(
            joinedload(cast("Any", ClassificationRule.classification)),
        ).filter(ClassificationRule.is_active.is_(True))

        if classification_id is not None:
            query = query.filter(ClassificationRule.classification_id == classification_id)
        if db_type:
            query = query.filter(ClassificationRule.db_type == db_type)

        return query.order_by(ClassificationRule.created_at.desc()).all()

    def fetch_active_assignments(self) -> list[tuple[AccountClassificationAssignment, AccountClassification]]:
        query = db.session.query(AccountClassificationAssignment, AccountClassification)
        typed_query = cast(Query[tuple[AccountClassificationAssignment, AccountClassification]], query)
        return (
            typed_query.join(
                AccountClassification,
                AccountClassificationAssignment.classification_id == AccountClassification.id,
            )
            .filter(AccountClassificationAssignment.is_active.is_(True))
            .all()
        )

    def fetch_rule_match_stats(self, rule_ids: Sequence[int] | None = None) -> dict[int, int]:
        rule_query = ClassificationRule.query.filter(ClassificationRule.is_active.is_(True))
        if rule_ids:
            rule_query = rule_query.filter(ClassificationRule.id.in_(rule_ids))
        rules = rule_query.order_by(ClassificationRule.id.asc()).all()
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

        return {rule.id: int(assignment_map.get(rule.id, 0) or 0) for rule in rules}

    def fetch_permissions_by_db_type(self, db_type: str) -> dict[str, list[dict[str, str | None]]]:
        return PermissionConfig.get_permissions_by_db_type(db_type)

    @staticmethod
    def delete_classification(classification: AccountClassification) -> None:
        db.session.delete(classification)

    @staticmethod
    def delete_rule(rule: ClassificationRule) -> None:
        db.session.delete(rule)

    @staticmethod
    def add_assignment(assignment: AccountClassificationAssignment) -> AccountClassificationAssignment:
        db.session.add(assignment)
        db.session.flush()
        return assignment
