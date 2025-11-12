"""分类器基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.account_permission import AccountPermission


class BaseRuleClassifier(ABC):
    """数据库特定规则评估器的通用接口。"""

    db_type: str

    @abstractmethod
    def evaluate(self, account: AccountPermission, rule_expression: dict[str, Any]) -> bool:
        """账户满足规则时返回 True。"""

    def supports(self, db_type: str) -> bool:
        return db_type.lower() == self.db_type.lower()
