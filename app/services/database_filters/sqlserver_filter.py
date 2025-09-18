"""
泰摸鱼吧 - SQL Server数据库过滤规则
"""

from .base_filter import BaseDatabaseFilter


class SQLServerDatabaseFilter(BaseDatabaseFilter):
    """SQL Server数据库过滤规则"""

    def get_database_type(self) -> str:
        return "sqlserver"
