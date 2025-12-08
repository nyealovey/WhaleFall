"""账户同步适配器模块..

提供各种数据库类型的账户同步适配器实现.

主要组件:
- BaseAccountAdapter: 账户同步适配器基类
- MySQLAccountAdapter: MySQL 账户同步适配器
- PostgreSQLAccountAdapter: PostgreSQL 账户同步适配器
- OracleAccountAdapter: Oracle 账户同步适配器
- SQLServerAccountAdapter: SQL Server 账户同步适配器
- get_account_adapter: 适配器工厂函数
"""

from .base_adapter import BaseAccountAdapter
from .factory import get_account_adapter

__all__ = [
    "BaseAccountAdapter",
    "get_account_adapter",
]
