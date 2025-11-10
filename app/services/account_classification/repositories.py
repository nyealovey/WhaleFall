"""Data-access helpers for account classification."""

from __future__ import annotations

from typing import Iterable, Sequence

from sqlalchemy.orm import joinedload

from app import db
from app.models.account_classification import (
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils


class ClassificationRepository:
    """Encapsulates DB interactions for account classification."""

    def fetch_active_rules(self) -> list[ClassificationRule]:
        return (
            ClassificationRule.query.options(joinedload(ClassificationRule.classification))
            .filter_by(is_active=True)
            .order_by(ClassificationRule.created_at.asc())
            .all()
        )

    def fetch_accounts(self, instance_id: int | None = None) -> list[AccountPermission]:
        query = (
            AccountPermission.query.join(Instance)
            .join(InstanceAccount, AccountPermission.instance_account)
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                InstanceAccount.is_active.is_(True),
            )
        )
        if instance_id:
            query = query.filter(AccountPermission.instance_id == instance_id)
        return query.all()

    def cleanup_all_assignments(self) -> int:
        """Remove all existing assignments prior to re-classification."""
        try:
            deleted = db.session.query(AccountClassificationAssignment).delete()
            if deleted:
                log_info(
                    "清理所有旧分配记录",
                    module="account_classification",
                    deleted_count=deleted,
                )
            db.session.commit()
            return deleted
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            log_error("清理旧分配记录失败", module="account_classification", error=str(exc))
            raise

    def upsert_assignments(
        self,
        matched_accounts: Sequence[AccountPermission],
        classification_id: int,
    ) -> int:
        """Replace assignments for the provided accounts."""
        if not matched_accounts:
            return 0

        account_ids = [account.id for account in matched_accounts]
        try:
            deleted_count = (
                db.session.query(AccountClassificationAssignment)
                .filter(
                    AccountClassificationAssignment.classification_id == classification_id,
                    AccountClassificationAssignment.account_id.in_(account_ids),
                )
                .delete(synchronize_session=False)
            )
            if deleted_count:
                log_info(
                    "清理分类旧分配记录",
                    module="account_classification",
                    classification_id=classification_id,
                    deleted_count=deleted_count,
                    account_ids=account_ids,
                )

            new_assignments = [
                {
                    "account_id": account.id,
                    "classification_id": classification_id,
                    "assigned_by": None,
                    "assignment_type": "auto",
                    "notes": None,
                    "is_active": True,
                    "created_at": time_utils.now(),
                    "updated_at": time_utils.now(),
                }
                for account in matched_accounts
            ]

            if new_assignments:
                db.session.bulk_insert_mappings(AccountClassificationAssignment, new_assignments)
                db.session.commit()

            return len(new_assignments)
        except Exception as exc:  # noqa: BLE001
            log_error(
                "批量写入分类分配失败",
                module="account_classification",
                error=str(exc),
                classification_id=classification_id,
            )
            db.session.rollback()
            return 0

    # --------- Cache serialization helpers ---------------------------------
    @staticmethod
    def serialize_rules(rules: Iterable[ClassificationRule]) -> list[dict]:
        payload: list[dict] = []
        for rule in rules:
            payload.append(
                {
                    "id": rule.id,
                    "classification_id": rule.classification_id,
                    "db_type": rule.db_type,
                    "rule_name": rule.rule_name,
                    "rule_expression": rule.rule_expression,
                    "is_active": rule.is_active,
                    "created_at": rule.created_at.isoformat() if rule.created_at else None,
                    "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
                }
            )
        return payload

    @staticmethod
    def hydrate_rules(rules_data: Iterable[dict]) -> list[ClassificationRule]:
        hydrated: list[ClassificationRule] = []
        for data in rules_data:
            try:
                rule = ClassificationRule()
                rule.id = data.get("id")
                rule.classification_id = data.get("classification_id")
                rule.db_type = data.get("db_type")
                rule.rule_name = data.get("rule_name")
                rule.rule_expression = data.get("rule_expression")
                rule.is_active = data.get("is_active", True)
                hydrated.append(rule)
            except Exception as exc:  # noqa: BLE001
                log_error("反序列化规则缓存失败", module="account_classification", error=str(exc))
        return hydrated
