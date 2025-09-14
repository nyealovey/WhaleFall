"""
泰摸鱼吧 - 安全查询构建器
提供安全的SQL查询构建功能，防止SQL注入攻击
"""

from typing import Any


class SafeQueryBuilder:
    """安全查询构建器"""

    def __init__(self):
        self.conditions: list[str] = []
        self.parameters: list[Any] = []

    def add_condition(self, condition: str, *params: Any) -> "SafeQueryBuilder":
        """
        添加查询条件

        Args:
            condition: SQL条件字符串，使用%s作为参数占位符
            *params: 参数值

        Returns:
            SafeQueryBuilder: 返回自身以支持链式调用
        """
        self.conditions.append(condition)
        self.parameters.extend(params)
        return self

    def add_in_condition(self, field: str, values: list[str]) -> "SafeQueryBuilder":
        """
        添加IN条件

        Args:
            field: 字段名
            values: 值列表

        Returns:
            SafeQueryBuilder: 返回自身以支持链式调用
        """
        if values:
            placeholders = ", ".join(["%s"] * len(values))
            condition = f"{field} NOT IN ({placeholders})"
            self.add_condition(condition, *values)
        return self

    def add_like_condition(self, field: str, pattern: str) -> "SafeQueryBuilder":
        """
        添加LIKE条件

        Args:
            field: 字段名
            pattern: 模式字符串

        Returns:
            SafeQueryBuilder: 返回自身以支持链式调用
        """
        condition = f"{field} NOT LIKE %s"
        self.add_condition(condition, pattern)
        return self

    def build_where_clause(self) -> tuple[str, list[Any]]:
        """
        构建WHERE子句

        Returns:
            Tuple[str, List[Any]]: WHERE子句和参数列表
        """
        if not self.conditions:
            return "1=1", []

        where_clause = " AND ".join(self.conditions)
        return where_clause, self.parameters.copy()

    def reset(self) -> "SafeQueryBuilder":
        """重置构建器"""
        self.conditions.clear()
        self.parameters.clear()
        return self


def build_safe_filter_conditions(
    db_type: str, username_field: str, filter_rules: dict[str, Any]
) -> tuple[str, list[Any]]:
    """
    构建安全的过滤条件

    Args:
        db_type: 数据库类型
        username_field: 用户名字段名
        filter_rules: 过滤规则

    Returns:
        Tuple[str, List[Any]]: WHERE子句和参数列表
    """
    builder = SafeQueryBuilder()
    rules = filter_rules.get(db_type, {})

    # 排除特定用户
    exclude_users = rules.get("exclude_users", [])
    if exclude_users:
        # 特殊处理：PostgreSQL的postgres用户不应该被排除
        if db_type == "postgresql" and "postgres" not in exclude_users:
            # 排除指定用户，但包含postgres
            builder.add_condition(
                f"({username_field} NOT IN ({', '.join(['%s'] * len(exclude_users))}) OR {username_field} = %s)",
                *exclude_users,
                "postgres",
            )
        else:
            builder.add_in_condition(username_field, exclude_users)

    # 排除模式匹配
    exclude_patterns = rules.get("exclude_patterns", [])
    for pattern in exclude_patterns:
        # 特殊处理：PostgreSQL的postgres用户不应该被pg_%模式排除
        if db_type == "postgresql" and pattern == "pg_%":
            # 使用更复杂的条件：排除pg_%模式但包含postgres
            builder.add_condition(f"({username_field} NOT LIKE %s OR {username_field} = %s)", pattern, "postgres")
        else:
            builder.add_like_condition(username_field, pattern)

    return builder.build_where_clause()
