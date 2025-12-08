"""鲸落 - 连接适配器模块
集中提供数据库连接工厂与连接测试服务.
"""

from .connection_factory import ConnectionFactory
from .connection_test_service import ConnectionTestService

__all__ = ["ConnectionFactory", "ConnectionTestService"]
