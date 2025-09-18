"""
鲸落 - PostgreSQL数据库过滤规则
"""

from .base_filter import BaseDatabaseFilter


class PostgreSQLDatabaseFilter(BaseDatabaseFilter):
    """PostgreSQL数据库过滤规则"""

    def get_database_type(self) -> str:
        return "postgresql"

    def should_include_user(self, username: str) -> bool:
        """
        重写用户包含判断，特殊处理postgres用户
        """
        # postgres用户是PostgreSQL的默认超级用户，应该被包含
        if username == "postgres":
            return True

        # 调用父类方法进行常规检查
        return super().should_include_user(username)

    def build_where_clause(self, username_field: str) -> str:
        """
        重写WHERE子句构建，特殊处理postgres用户
        """

        conditions = []
        params = []

        # 处理排除用户
        if self.exclude_users:
            placeholders = ", ".join(["%s"] * len(self.exclude_users))
            conditions.append(f"{username_field} NOT IN ({placeholders})")
            params.extend(self.exclude_users)

        # 处理排除模式，特殊处理pg_%模式
        for pattern in self.exclude_patterns:
            if pattern == "pg_%":
                # pg_%模式不排除postgres用户
                conditions.append(f"({username_field} NOT LIKE %s OR {username_field} = %s)")
                params.extend([pattern, "postgres"])
            else:
                conditions.append(f"{username_field} NOT LIKE %s")
                params.append(pattern)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        return where_clause, params
