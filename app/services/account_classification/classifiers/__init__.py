"""数据库特定规则分类器模块..

提供各种数据库类型的账户分类规则评估器.

主要组件:
- ClassifierFactory: 分类器工厂
- BaseRuleClassifier: 分类器基类
- MySQLRuleClassifier: MySQL 规则分类器
- PostgreSQLRuleClassifier: PostgreSQL 规则分类器
- OracleRuleClassifier: Oracle 规则分类器
- SQLServerRuleClassifier: SQL Server 规则分类器
"""

from .factory import ClassifierFactory

__all__ = ["ClassifierFactory"]
