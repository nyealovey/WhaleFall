"""分类器工厂。

提供数据库类型专属的分类器实例，支持 MySQL、PostgreSQL、SQL Server 和 Oracle。
"""

from __future__ import annotations


from .base import BaseRuleClassifier
from .mysql_classifier import MySQLRuleClassifier
from .oracle_classifier import OracleRuleClassifier
from .postgresql_classifier import PostgreSQLRuleClassifier
from .sqlserver_classifier import SQLServerRuleClassifier


class ClassifierFactory:
    """分类器工厂。

    提供数据库类型专属的分类器实例，根据数据库类型返回对应的规则分类器。

    Attributes:
        _registry: 数据库类型到分类器实例的映射字典。

    Example:
        >>> factory = ClassifierFactory()
        >>> classifier = factory.get('mysql')
        >>> classifier is not None
        True

    """

    def __init__(self) -> None:
        """初始化分类器工厂。

        创建并注册所有支持的数据库类型分类器。
        """
        self._registry: dict[str, BaseRuleClassifier] = {
            "mysql": MySQLRuleClassifier(),
            "postgresql": PostgreSQLRuleClassifier(),
            "sqlserver": SQLServerRuleClassifier(),
            "oracle": OracleRuleClassifier(),
        }

    def get(self, db_type: str) -> BaseRuleClassifier | None:
        """获取指定数据库类型的分类器。

        Args:
            db_type: 数据库类型（mysql、postgresql、sqlserver、oracle）。

        Returns:
            对应的分类器实例，如果数据库类型不支持则返回 None。

        Example:
            >>> factory = ClassifierFactory()
            >>> classifier = factory.get('mysql')
            >>> type(classifier).__name__
            'MySQLRuleClassifier'

        """
        if not db_type:
            return None
        return self._registry.get(db_type.lower())
