"""账户分类管理 write API Service.

职责:
- 编排账户分类/规则/分配的写操作
- 调用 repository 执行 add/delete/flush
- 不返回 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import DatabaseError
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.repositories.accounts_classifications_repository import AccountsClassificationsRepository
from app.utils.structlog_config import log_info


@dataclass(slots=True)
class AccountClassificationDeleteOutcome:
    classification_id: int
    classification_name: str


@dataclass(slots=True)
class ClassificationRuleDeleteOutcome:
    rule_id: int
    rule_name: str


@dataclass(slots=True)
class AccountClassificationAssignmentDeactivateOutcome:
    assignment_id: int
    account_id: int
    classification_id: int


class AccountClassificationsWriteService:
    """账户分类管理写操作服务."""

    def __init__(self, repository: AccountsClassificationsRepository | None = None) -> None:
        self._repository = repository or AccountsClassificationsRepository()

    def delete_classification(
        self,
        classification: AccountClassification,
        *,
        operator_id: int | None = None,
    ) -> AccountClassificationDeleteOutcome:
        outcome = AccountClassificationDeleteOutcome(
            classification_id=classification.id,
            classification_name=classification.name,
        )

        try:
            self._repository.delete_classification(classification)
            db.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "删除账户分类失败",
                extra={
                    "exception": str(exc),
                    "classification_id": classification.id,
                },
            ) from exc

        log_info(
            "删除账户分类成功",
            module="accounts_classifications",
            classification_id=outcome.classification_id,
            operator_id=operator_id,
        )
        return outcome

    def delete_rule(
        self,
        rule: ClassificationRule,
        *,
        operator_id: int | None = None,
    ) -> ClassificationRuleDeleteOutcome:
        outcome = ClassificationRuleDeleteOutcome(rule_id=rule.id, rule_name=rule.rule_name)

        try:
            self._repository.delete_rule(rule)
            db.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "删除分类规则失败",
                extra={
                    "exception": str(exc),
                    "rule_id": rule.id,
                },
            ) from exc

        log_info(
            "删除分类规则成功",
            module="accounts_classifications",
            rule_id=outcome.rule_id,
            operator_id=operator_id,
        )
        return outcome

    def deactivate_assignment(
        self,
        assignment: AccountClassificationAssignment,
        *,
        operator_id: int | None = None,
    ) -> AccountClassificationAssignmentDeactivateOutcome:
        assignment.is_active = False
        outcome = AccountClassificationAssignmentDeactivateOutcome(
            assignment_id=assignment.id,
            account_id=assignment.account_id,
            classification_id=assignment.classification_id,
        )

        try:
            self._repository.add_assignment(assignment)
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "移除分配失败",
                extra={
                    "exception": str(exc),
                    "assignment_id": assignment.id,
                },
            ) from exc

        log_info(
            "移除账户分类分配成功",
            module="accounts_classifications",
            assignment_id=outcome.assignment_id,
            operator_id=operator_id,
        )
        return outcome

