"""Base classifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.account_permission import AccountPermission


class BaseRuleClassifier(ABC):
    """Common interface for database-specific rule evaluators."""

    db_type: str

    @abstractmethod
    def evaluate(self, account: AccountPermission, rule_expression: dict[str, Any]) -> bool:
        """Return True if the account matches the rule."""

    def supports(self, db_type: str) -> bool:
        return db_type.lower() == self.db_type.lower()
