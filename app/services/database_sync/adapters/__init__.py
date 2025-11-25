"""容量同步适配器模块。

提供各种数据库类型的容量同步适配器实现。

主要组件：
- BaseCapacityAdapter: 容量同步适配器基类
- MySQLCapacityAdapter: MySQL 容量同步适配器
- PostgreSQLCapacityAdapter: PostgreSQL 容量同步适配器
- OracleCapacityAdapter: Oracle 容量同步适配器
- SQLServerCapacityAdapter: SQL Server 容量同步适配器
- get_capacity_adapter: 适配器工厂函数
"""

from .base_adapter import BaseCapacityAdapter
from .factory import get_capacity_adapter

__all__ = ["BaseCapacityAdapter", "get_capacity_adapter"]
