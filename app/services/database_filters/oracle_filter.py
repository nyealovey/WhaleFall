"""
鲸落 - Oracle数据库过滤规则
"""

from .base_filter import BaseDatabaseFilter


class OracleDatabaseFilter(BaseDatabaseFilter):
    """Oracle数据库过滤规则"""

    def get_database_type(self) -> str:
        return "oracle"
