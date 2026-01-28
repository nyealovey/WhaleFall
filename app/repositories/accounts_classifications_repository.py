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

    def get_classification_by_id(self, classification_id: int) -> AccountClassification | None:
        """按ID获取账户分类."""
        return cast("AccountClassification | None", AccountClassification.query.get(classification_id))

    def get_rule_by_id(self, rule_id: int) -> ClassificationRule | None:
        """按ID获取分类规则."""
        return cast("ClassificationRule | None", ClassificationRule.query.get(rule_id))

    def get_assignment_by_id(self, assignment_id: int) -> AccountClassificationAssignment | None:
        """按ID获取分类分配记录."""
        return cast("AccountClassificationAssignment | None", AccountClassificationAssignment.query.get(assignment_id))

    @staticmethod
    def exists_classification_code(code: str, *, exclude_classification_id: int | None = None) -> bool:
        """判断分类 code 是否已存在(可排除指定分类 ID)."""
        normalized = code.strip()
        if not normalized:
            return False
        query = AccountClassification.query.filter(AccountClassification.code == normalized)
        if exclude_classification_id is not None:
            query = query.filter(AccountClassification.id != exclude_classification_id)
        return bool(db.session.query(query.exists()).scalar())

    @staticmethod
    def exists_rule_name(
        *,
        classification_id: int,
        db_type: str,
        rule_name: str,
        exclude_rule_id: int | None = None,
    ) -> bool:
        """判断规则名称是否已存在(同分类 + 同 db_type, 可排除指定 rule ID)."""
        query = ClassificationRule.query.filter_by(
            classification_id=classification_id,
            db_type=db_type,
            rule_name=rule_name,
        ).filter(ClassificationRule.is_active.is_(True))
        if exclude_rule_id is not None:
            query = query.filter(ClassificationRule.id != exclude_rule_id)
        return bool(db.session.query(query.exists()).scalar())

    @staticmethod
    def exists_rule_expression(
        *,
        classification_id: int,
        rule_expression: str,
        exclude_rule_id: int | None = None,
    ) -> bool:
        """判断规则表达式是否已存在(同分类, 可排除指定 rule ID)."""
        query = ClassificationRule.query.filter_by(
            classification_id=classification_id,
            rule_expression=rule_expression,
        ).filter(ClassificationRule.is_active.is_(True))
        if exclude_rule_id is not None:
            query = query.filter(ClassificationRule.id != exclude_rule_id)
        return bool(db.session.query(query.exists()).scalar())

    def fetch_classification_usage(self, classification_id: int) -> tuple[int, int]:
        """统计分类的规则数量与启用分配数量."""
        rule_count = int(ClassificationRule.query.filter_by(classification_id=classification_id).count())
        assignment_count = int(
            AccountClassificationAssignment.query.filter_by(
                classification_id=classification_id,
                is_active=True,
            ).count(),
        )
        return rule_count, assignment_count

    def fetch_active_classifications(self) -> list[AccountClassification]:
        """查询启用的账户分类."""
        return (
            AccountClassification.query.filter_by(is_active=True)
            .order_by(
                AccountClassification.priority.desc(),
                AccountClassification.created_at.desc(),
            )
            .all()
        )

    def fetch_rule_counts(self, classification_ids: Sequence[int]) -> dict[int, int]:
        """按分类ID统计规则数量."""
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
        """查询启用的分类规则."""
        query = ClassificationRule.query.options(
            joinedload(cast("Any", ClassificationRule.classification)),
        ).filter(ClassificationRule.is_active.is_(True))

        if classification_id is not None:
            query = query.filter(ClassificationRule.classification_id == classification_id)
        if db_type:
            query = query.filter(ClassificationRule.db_type == db_type)

        return query.order_by(ClassificationRule.created_at.desc()).all()

    def fetch_rules_for_overview(
        self,
        *,
        classification_id: int,
        db_type: str | None,
        is_active: bool | None,
    ) -> list[ClassificationRule]:
        """按条件获取规则列表(支持 active/archived/all)."""
        query = ClassificationRule.query.filter(ClassificationRule.classification_id == classification_id)
        if db_type:
            query = query.filter(ClassificationRule.db_type == db_type)
        if is_active is True:
            query = query.filter(ClassificationRule.is_active.is_(True))
        elif is_active is False:
            query = query.filter(ClassificationRule.is_active.is_(False))
        return query.order_by(ClassificationRule.created_at.desc()).all()

    def fetch_rules_by_ids(self, rule_ids: Sequence[int]) -> list[ClassificationRule]:
        """按规则 ID 批量获取规则."""
        if not rule_ids:
            return []
        return ClassificationRule.query.filter(ClassificationRule.id.in_(list(rule_ids))).all()

    def fetch_active_assignments(self) -> list[tuple[AccountClassificationAssignment, AccountClassification]]:
        """查询启用的分类分配."""
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
        """统计规则命中账户数量."""
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

        return {rule.id: int(assignment_map.get(rule.id, 0)) for rule in rules}

    def fetch_permissions_by_db_type(self, db_type: str) -> dict[str, list[dict[str, str | None]]]:
        """获取指定数据库类型的权限配置."""
        return PermissionConfig.get_permissions_by_db_type(db_type)

    @staticmethod
    def delete_classification(classification: AccountClassification) -> None:
        """删除账户分类."""
        db.session.delete(classification)

    @staticmethod
    def add_classification(classification: AccountClassification) -> AccountClassification:
        """新增账户分类并 flush."""
        db.session.add(classification)
        db.session.flush()
        return classification

    @staticmethod
    def delete_rule(rule: ClassificationRule) -> None:
        """删除分类规则."""
        db.session.delete(rule)

    @staticmethod
    def add_rule(rule: ClassificationRule) -> ClassificationRule:
        """新增分类规则并 flush."""
        db.session.add(rule)
        db.session.flush()
        return rule

    @staticmethod
    def add_assignment(assignment: AccountClassificationAssignment) -> AccountClassificationAssignment:
        """新增分类分配并 flush."""
        db.session.add(assignment)
        db.session.flush()
        return assignment
