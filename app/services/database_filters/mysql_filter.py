"""
鲸落 - MySQL数据库过滤规则
"""

from .base_filter import BaseDatabaseFilter


class MySQLDatabaseFilter(BaseDatabaseFilter):
    """MySQL数据库过滤规则"""

    def get_database_type(self) -> str:
        return "mysql"
