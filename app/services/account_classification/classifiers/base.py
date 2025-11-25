"""分类器基类。

定义数据库特定规则评估器的通用接口，所有数据库类型的分类器都需要继承此基类。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.account_permission import AccountPermission


class BaseRuleClassifier(ABC):
    """数据库特定规则评估器的通用接口。

    所有数据库类型的分类器都需要继承此基类并实现 evaluate 方法。

    Attributes:
        db_type: 数据库类型标识符。

    Example:
        >>> class MySQLClassifier(BaseRuleClassifier):
        ...     db_type = 'mysql'
        ...     def evaluate(self, account, rule_expression):
        ...         return True
    """

    db_type: str

    @abstractmethod
    def evaluate(self, account: AccountPermission, rule_expression: dict[str, Any]) -> bool:
        """评估账户是否满足规则表达式。

        Args:
            account: 账户权限对象。
            rule_expression: 规则表达式字典。

        Returns:
            如果账户满足规则返回 True，否则返回 False。
        """

    def supports(self, db_type: str) -> bool:
        """检查是否支持指定的数据库类型。

        Args:
            db_type: 数据库类型。

        Returns:
            如果支持该数据库类型返回 True，否则返回 False。
        """
        return db_type.lower() == self.db_type.lower()
