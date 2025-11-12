"""分类器工厂。"""

from __future__ import annotations

from typing import Dict

from .base import BaseRuleClassifier
from .mysql_classifier import MySQLRuleClassifier
from .oracle_classifier import OracleRuleClassifier
from .postgresql_classifier import PostgreSQLRuleClassifier
from .sqlserver_classifier import SQLServerRuleClassifier


class ClassifierFactory:
    """提供数据库类型专属的分类器实例。"""

    def __init__(self) -> None:
        self._registry: Dict[str, BaseRuleClassifier] = {
            "mysql": MySQLRuleClassifier(),
            "postgresql": PostgreSQLRuleClassifier(),
            "sqlserver": SQLServerRuleClassifier(),
            "oracle": OracleRuleClassifier(),
        }

    def get(self, db_type: str) -> BaseRuleClassifier | None:
        if not db_type:
            return None
        return self._registry.get(db_type.lower())
