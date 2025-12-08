"""鲸落 - 安全查询构建器
提供安全的SQL查询构建功能，防止SQL注入攻击
支持MySQL、PostgreSQL、SQL Server、Oracle等多种数据库.
"""

from typing import Any

from app.constants import DatabaseType


class SafeQueryBuilder:
    """安全查询构建器 - 多数据库支持版。.

    提供安全的 SQL 查询构建功能，防止 SQL 注入攻击。
    根据不同数据库类型使用相应的参数占位符和参数格式。

    支持的数据库类型：
    - MySQL: 使用 %s 占位符，返回 list 参数
    - PostgreSQL: 使用 %s 占位符，返回 list 参数
    - SQL Server: 使用 %s 占位符，返回 list 参数
    - Oracle: 使用 :name 占位符，返回 dict 参数

    Attributes:
        db_type: 数据库类型。
        conditions: 查询条件列表。
        parameters: 参数列表（MySQL/PostgreSQL/SQL Server）或参数字典（Oracle）。

    Example:
        >>> builder = SafeQueryBuilder('mysql')
        >>> builder.add_condition('username = %s', 'admin')
        >>> builder.add_in_condition('status', ['active', 'pending'])
        >>> where_clause, params = builder.build_where_clause()

    """

    def __init__(self, db_type: str = "mysql") -> None:
        """初始化查询构建器。.

        Args:
            db_type: 数据库类型，可选值：'mysql'、'postgresql'、'sqlserver'、'oracle'。
                默认为 'mysql'。

        """
        self.db_type = db_type.lower()
        self.conditions: list[str] = []

        # 根据数据库类型选择参数存储方式
        if self.db_type == DatabaseType.ORACLE:
            self.parameters: dict[str, Any] = {}
            self._param_counter = 0
        else:
            self.parameters: list[Any] = []

    def add_condition(self, condition: str, *params: Any) -> "SafeQueryBuilder":
        """添加查询条件。.

        根据数据库类型自动转换占位符格式。MySQL/PostgreSQL/SQL Server 使用 %s，
        Oracle 使用 :param_N 格式。

        Args:
            condition: SQL 条件字符串，使用 %s 作为占位符。
                例如：'username = %s' 或 'age > %s AND status = %s'。
            *params: 参数值，按顺序对应条件中的占位符。

        Returns:
            返回自身以支持链式调用。

        Example:
            >>> builder.add_condition('username = %s', 'admin')
            >>> builder.add_condition('age > %s AND status = %s', 18, 'active')

        """
        if self.db_type == DatabaseType.ORACLE:
            # Oracle使用命名参数，需要转换占位符
            oracle_condition = condition
            param_dict = {}

            for _, param in enumerate(params):
                param_name = f"param_{self._param_counter}"
                self._param_counter += 1

                # 替换%s为Oracle格式的:param_name
                oracle_condition = oracle_condition.replace("%s", f":{param_name}", 1)
                param_dict[param_name] = param

            self.conditions.append(oracle_condition)
            self.parameters.update(param_dict)
        else:
            # MySQL, PostgreSQL, SQL Server使用位置参数
            self.conditions.append(condition)
            self.parameters.extend(params)

        return self

    def _generate_placeholder(self, count: int = 1) -> str:
        """生成数据库特定的占位符。.

        根据数据库类型生成相应格式的占位符字符串。

        Args:
            count: 占位符数量，默认为 1。

        Returns:
            占位符字符串，多个占位符用逗号分隔。
            例如：'%s, %s, %s' 或 ':param_0, :param_1, :param_2'。

        """
        if self.db_type == DatabaseType.ORACLE:
            placeholders = []
            for _ in range(count):
                param_name = f"param_{self._param_counter}"
                self._param_counter += 1
                placeholders.append(f":{param_name}")
            return ", ".join(placeholders)
        if self.db_type == DatabaseType.SQLSERVER:
            # SQL Server使用%s占位符
            return ", ".join(["%s"] * count)
        # MySQL, PostgreSQL使用%s
        return ", ".join(["%s"] * count)

    def add_in_condition(self, field: str, values: list[str]) -> "SafeQueryBuilder":
        """添加 IN 条件。.

        生成安全的 IN 查询条件，防止 SQL 注入。

        Args:
            field: 字段名，例如 'status' 或 'user_id'。
            values: 值列表，例如 ['active', 'pending'] 或 [1, 2, 3]。
                如果列表为空，不添加任何条件。

        Returns:
            返回自身以支持链式调用。

        Example:
            >>> builder.add_in_condition('status', ['active', 'pending'])
            # 生成: status IN (%s, %s)

        """
        if values:
            if self.db_type == DatabaseType.ORACLE:
                placeholders = []
                param_dict = {}
                for value in values:
                    param_name = f"param_{self._param_counter}"
                    self._param_counter += 1
                    placeholders.append(f":{param_name}")
                    param_dict[param_name] = value

                condition = f"{field} IN ({', '.join(placeholders)})"
                self.conditions.append(condition)
                self.parameters.update(param_dict)
            else:
                placeholders = ", ".join(["%s"] * len(values))
                condition = f"{field} IN ({placeholders})"
                self.conditions.append(condition)
                self.parameters.extend(values)
        return self

    def add_not_in_condition(self, field: str, values: list[str]) -> "SafeQueryBuilder":
        """添加 NOT IN 条件。.

        生成安全的 NOT IN 查询条件，防止 SQL 注入。

        Args:
            field: 字段名，例如 'username' 或 'role_id'。
            values: 值列表，例如 ['admin', 'root'] 或 [1, 2]。
                如果列表为空，不添加任何条件。

        Returns:
            返回自身以支持链式调用。

        Example:
            >>> builder.add_not_in_condition('username', ['admin', 'root'])
            # 生成: username NOT IN (%s, %s)

        """
        if values:
            if self.db_type == DatabaseType.ORACLE:
                placeholders = []
                param_dict = {}
                for value in values:
                    param_name = f"param_{self._param_counter}"
                    self._param_counter += 1
                    placeholders.append(f":{param_name}")
                    param_dict[param_name] = value

                condition = f"{field} NOT IN ({', '.join(placeholders)})"
                self.conditions.append(condition)
                self.parameters.update(param_dict)
            else:
                placeholders = ", ".join(["%s"] * len(values))
                condition = f"{field} NOT IN ({placeholders})"
                self.conditions.append(condition)
                self.parameters.extend(values)
        return self

    def add_like_condition(self, field: str, pattern: str) -> "SafeQueryBuilder":
        """添加 LIKE 条件。.

        生成安全的 LIKE 查询条件，防止 SQL 注入。

        Args:
            field: 字段名，例如 'username' 或 'email'。
            pattern: 模式字符串，例如 '%admin%' 或 'test_%'。
                需要包含通配符 % 或 _。

        Returns:
            返回自身以支持链式调用。

        Example:
            >>> builder.add_like_condition('username', '%admin%')
            # 生成: username LIKE %s

        """
        if self.db_type == DatabaseType.ORACLE:
            param_name = f"param_{self._param_counter}"
            self._param_counter += 1
            condition = f"{field} LIKE :{param_name}"
            self.conditions.append(condition)
            self.parameters[param_name] = pattern
        else:
            condition = f"{field} LIKE %s"
            self.conditions.append(condition)
            self.parameters.append(pattern)
        return self

    def add_not_like_condition(self, field: str, pattern: str) -> "SafeQueryBuilder":
        """添加 NOT LIKE 条件。.

        生成安全的 NOT LIKE 查询条件，防止 SQL 注入。

        Args:
            field: 字段名，例如 'username' 或 'email'。
            pattern: 模式字符串，例如 'test_%' 或 '%_backup'。
                需要包含通配符 % 或 _。

        Returns:
            返回自身以支持链式调用。

        Example:
            >>> builder.add_not_like_condition('username', 'test_%')
            # 生成: username NOT LIKE %s

        """
        if self.db_type == DatabaseType.ORACLE:
            param_name = f"param_{self._param_counter}"
            self._param_counter += 1
            condition = f"{field} NOT LIKE :{param_name}"
            self.conditions.append(condition)
            self.parameters[param_name] = pattern
        else:
            condition = f"{field} NOT LIKE %s"
            self.conditions.append(condition)
            self.parameters.append(pattern)
        return self

    def build_where_clause(self) -> tuple[str, list[Any]] | tuple[str, dict[str, Any]]:
        """构建 WHERE 子句。.

        将所有添加的条件组合成完整的 WHERE 子句，并返回对应的参数。

        Returns:
            根据数据库类型返回不同格式：
            - MySQL/PostgreSQL/SQL Server: (WHERE 子句字符串, 参数列表)
            - Oracle: (WHERE 子句字符串, 参数字典)
            如果没有条件，返回 ('1=1', []) 或 ('1=1', {})。

        Example:
            >>> builder.add_condition('status = %s', 'active')
            >>> where, params = builder.build_where_clause()
            >>> print(where)  # 'status = %s'
            >>> print(params)  # ['active']

        """
        if not self.conditions:
            if self.db_type == DatabaseType.ORACLE:
                return "1=1", {}
            return "1=1", []

        where_clause = " AND ".join(self.conditions)

        if self.db_type == DatabaseType.ORACLE:
            return where_clause, self.parameters.copy()
        return where_clause, self.parameters.copy()

    def add_database_specific_condition(
        self, field: str, values: list[str], patterns: list[str], db_specific_rules: dict[str, Any] | None = None,
    ) -> "SafeQueryBuilder":
        """添加数据库特定的过滤条件。.

        根据数据库类型应用特定的过滤规则。例如 PostgreSQL 会保留 postgres 用户。

        Args:
            field: 字段名，例如 'username'。
            values: 排除的值列表，例如 ['admin', 'root']。
            patterns: 排除的模式列表，例如 ['test_%', '%_backup']。
            db_specific_rules: 数据库特定规则字典，默认为 None。

        Returns:
            返回自身以支持链式调用。

        Example:
            >>> builder.add_database_specific_condition(
            ...     'username',
            ...     ['admin', 'root'],
            ...     ['test_%']
            ... )

        """
        db_specific_rules = db_specific_rules or {}

        # 处理排除用户
        if values:
            # PostgreSQL特殊处理：保留postgres用户
            if self.db_type == DatabaseType.POSTGRESQL and "postgres" in values:
                filtered_values = [v for v in values if v != "postgres"]
                if filtered_values:
                    self.add_not_in_condition(field, filtered_values)
            else:
                self.add_not_in_condition(field, values)

        # 处理排除模式
        for pattern in patterns:
            # PostgreSQL特殊处理：pg_%模式不排除postgres用户
            if self.db_type == DatabaseType.POSTGRESQL and pattern == "pg_%":
                self.add_condition(f"({field} NOT LIKE %s OR {field} = %s)", pattern, "postgres")
            else:
                self.add_not_like_condition(field, pattern)

        return self

    def reset(self) -> "SafeQueryBuilder":
        """重置构建器。.

        清空所有条件和参数，恢复到初始状态。

        Returns:
            返回自身以支持链式调用。

        Example:
            >>> builder.add_condition('status = %s', 'active')
            >>> builder.reset()  # 清空所有条件
            >>> builder.add_condition('username = %s', 'admin')

        """
        self.conditions.clear()
        if self.db_type == DatabaseType.ORACLE:
            self.parameters.clear()
            self._param_counter = 0
        else:
            self.parameters.clear()
        return self


def build_safe_filter_conditions(
    db_type: str, username_field: str, filter_rules: dict[str, Any],
) -> tuple[str, list[Any]] | tuple[str, dict[str, Any]]:
    """构建安全的过滤条件 - 统一入口函数。.

    根据数据库类型和过滤规则构建安全的 WHERE 子句。

    Args:
        db_type: 数据库类型，可选值：'mysql'、'postgresql'、'sqlserver'、'oracle'。
        username_field: 用户名字段名，例如 'username' 或 'account_name'。
        filter_rules: 过滤规则字典，格式如下：
            {
                'mysql': {
                    'exclude_users': ['root', 'admin'],
                    'exclude_patterns': ['test_%']
                }
            }

    Returns:
        根据数据库类型返回不同格式：
        - MySQL/PostgreSQL/SQL Server: (WHERE 子句, 参数列表)
        - Oracle: (WHERE 子句, 参数字典)

    Example:
        >>> rules = {'mysql': {'exclude_users': ['root'], 'exclude_patterns': ['test_%']}}
        >>> where, params = build_safe_filter_conditions('mysql', 'username', rules)

    """
    builder = SafeQueryBuilder(db_type)
    rules = filter_rules.get(db_type, {})

    exclude_users = rules.get("exclude_users", [])
    exclude_patterns = rules.get("exclude_patterns", [])

    # 使用统一的数据库特定条件构建方法
    builder.add_database_specific_condition(username_field, exclude_users, exclude_patterns)

    return builder.build_where_clause()


# 为了向后兼容，添加一个便捷函数返回list格式的参数
def build_safe_filter_conditions_list(
    db_type: str, username_field: str, filter_rules: dict[str, Any],
) -> tuple[str, list[Any]]:
    """构建安全的过滤条件 - 返回 list 格式参数（向后兼容）。.

    与 build_safe_filter_conditions 功能相同，但始终返回列表格式的参数。
    用于向后兼容不支持字典参数的代码。

    Args:
        db_type: 数据库类型，可选值：'mysql'、'postgresql'、'sqlserver'、'oracle'。
        username_field: 用户名字段名，例如 'username' 或 'account_name'。
        filter_rules: 过滤规则字典。

    Returns:
        (WHERE 子句, 参数列表)。注意：Oracle 的命名参数会被转换为列表。

    Example:
        >>> rules = {'mysql': {'exclude_users': ['root']}}
        >>> where, params = build_safe_filter_conditions_list('mysql', 'username', rules)
        >>> print(type(params))  # <class 'list'>

    """
    where_clause, params = build_safe_filter_conditions(db_type, username_field, filter_rules)

    # 如果是Oracle返回的dict，转换为list（虽然会丢失命名信息，但保持兼容性）
    if isinstance(params, dict):
        return where_clause, list(params.values())
    return where_clause, params
