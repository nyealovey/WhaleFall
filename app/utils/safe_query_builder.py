"""鲸落 - 安全查询构建器.

提供安全的SQL查询构建功能,防止SQL注入攻击.
支持MySQL、PostgreSQL、SQL Server、Oracle等多种数据库.
"""

from collections.abc import Mapping, Sequence
from typing import cast

from app.core.constants import DatabaseType
from app.core.types import JsonValue


class SafeQueryBuilder:
    """安全查询构建器 - 多数据库支持版.

    提供安全的 SQL 查询构建功能,防止 SQL 注入攻击.
    根据不同数据库类型使用相应的参数占位符和参数格式.

    支持的数据库类型:
    - MySQL: 使用 %s 占位符,返回 list 参数
    - PostgreSQL: 使用 %s 占位符,返回 list 参数
    - SQL Server: 使用 %s 占位符,返回 list 参数
    - Oracle: 使用 :name 占位符,返回 dict 参数

    Attributes:
        db_type: 数据库类型.
        conditions: 查询条件列表.
        parameters: 参数列表(MySQL/PostgreSQL/SQL Server)或参数字典(Oracle).

    Example:
        >>> builder = SafeQueryBuilder('mysql')
        >>> builder.add_condition('username = %s', 'admin')
        >>> builder.add_in_condition('status', ['active', 'pending'])
        >>> where_clause, params = builder.build_where_clause()

    """

    def __init__(self, db_type: str = "mysql") -> None:
        """初始化查询构建器.

        Args:
            db_type: 数据库类型,可选值:'mysql'、'postgresql'、'sqlserver'、'oracle'.
                默认为 'mysql'.

        """
        self.db_type = db_type.lower()
        self.conditions: list[str] = []
        self._param_counter = 0

        # 根据数据库类型选择参数存储方式
        if self.db_type == DatabaseType.ORACLE:
            self.parameters: dict[str, JsonValue] | list[JsonValue] = {}
        else:
            self.parameters = []

    def add_condition(self, condition: str, *params: JsonValue) -> "SafeQueryBuilder":
        """添加查询条件.

        根据数据库类型自动转换占位符格式.MySQL/PostgreSQL/SQL Server 使用 %s,
        Oracle 使用 :param_N 格式.

        Args:
            condition: SQL 条件字符串,使用 %s 作为占位符.
                例如:'username = %s' 或 'age > %s AND status = %s'.
            *params: 参数值,按顺序对应条件中的占位符.

        Returns:
            返回自身以支持链式调用.

        Example:
            >>> builder.add_condition('username = %s', 'admin')
            >>> builder.add_condition('age > %s AND status = %s', 18, 'active')

        """
        if self.db_type == DatabaseType.ORACLE:
            # Oracle使用命名参数,需要转换占位符
            oracle_condition = condition
            param_dict = cast(dict[str, JsonValue], self.parameters)

            for param in params:
                param_name = f"param_{self._param_counter}"
                self._param_counter += 1

                # 替换%s为Oracle格式的:param_name
                oracle_condition = oracle_condition.replace("%s", f":{param_name}", 1)
                param_dict[param_name] = param

            self.conditions.append(oracle_condition)
        else:
            # MySQL, PostgreSQL, SQL Server使用位置参数
            self.conditions.append(condition)
            cast(list[JsonValue], self.parameters).extend(params)

        return self

    def add_in_condition(self, field: str, values: Sequence[str]) -> "SafeQueryBuilder":
        """添加 IN 条件.

        生成安全的 IN 查询条件,防止 SQL 注入.

        Args:
            field: 字段名,例如 'status' 或 'user_id'.
            values: 值列表,例如 ['active', 'pending'] 或 [1, 2, 3].
                如果列表为空,不添加任何条件.

        Returns:
            返回自身以支持链式调用.

        Example:
            >>> builder.add_in_condition('status', ['active', 'pending'])
            # 生成: status IN (%s, %s)

        """
        if not values:
            return self

        if self.db_type == DatabaseType.ORACLE:
            placeholders = []
            param_dict = cast(dict[str, JsonValue], self.parameters)
            for value in values:
                param_name = f"param_{self._param_counter}"
                self._param_counter += 1
                placeholders.append(f":{param_name}")
                param_dict[param_name] = value

            condition = f"{field} IN ({', '.join(placeholders)})"
            self.conditions.append(condition)
            return self

        placeholders = ", ".join(["%s"] * len(values))
        condition = f"{field} IN ({placeholders})"
        self.conditions.append(condition)
        cast(list[JsonValue], self.parameters).extend(values)
        return self

    def add_not_in_condition(self, field: str, values: Sequence[str]) -> "SafeQueryBuilder":
        """添加 NOT IN 条件.

        生成安全的 NOT IN 查询条件,防止 SQL 注入.

        Args:
            field: 字段名,例如 'username' 或 'role_id'.
            values: 值列表,例如 ['admin', 'root'] 或 [1, 2].
                如果列表为空,不添加任何条件.

        Returns:
            返回自身以支持链式调用.

        Example:
            >>> builder.add_not_in_condition('username', ['admin', 'root'])
            # 生成: username NOT IN (%s, %s)

        """
        if not values:
            return self

        if self.db_type == DatabaseType.ORACLE:
            placeholders = []
            param_dict = cast(dict[str, JsonValue], self.parameters)
            for value in values:
                param_name = f"param_{self._param_counter}"
                self._param_counter += 1
                placeholders.append(f":{param_name}")
                param_dict[param_name] = value

            condition = f"{field} NOT IN ({', '.join(placeholders)})"
            self.conditions.append(condition)
            return self

        placeholders = ", ".join(["%s"] * len(values))
        condition = f"{field} NOT IN ({placeholders})"
        self.conditions.append(condition)
        cast(list[JsonValue], self.parameters).extend(values)
        return self

    def add_like_condition(self, field: str, pattern: str) -> "SafeQueryBuilder":
        """添加 LIKE 条件.

        生成安全的 LIKE 查询条件,防止 SQL 注入.

        Args:
            field: 字段名,例如 'username' 或 'email'.
            pattern: 模式字符串,例如 '%admin%' 或 'test_%'.
                需要包含通配符 % 或 _.

        Returns:
            返回自身以支持链式调用.

        Example:
            >>> builder.add_like_condition('username', '%admin%')
            # 生成: username LIKE %s

        """
        if self.db_type == DatabaseType.ORACLE:
            param_name = f"param_{self._param_counter}"
            self._param_counter += 1
            condition = f"{field} LIKE :{param_name}"
            self.conditions.append(condition)
            cast(dict[str, JsonValue], self.parameters)[param_name] = pattern
        else:
            condition = f"{field} LIKE %s"
            self.conditions.append(condition)
            cast(list[JsonValue], self.parameters).append(pattern)
        return self

    def add_not_like_condition(self, field: str, pattern: str) -> "SafeQueryBuilder":
        """添加 NOT LIKE 条件.

        生成安全的 NOT LIKE 查询条件,防止 SQL 注入.

        Args:
            field: 字段名,例如 'username' 或 'email'.
            pattern: 模式字符串,例如 'test_%' 或 '%_backup'.
                需要包含通配符 % 或 _.

        Returns:
            返回自身以支持链式调用.

        Example:
            >>> builder.add_not_like_condition('username', 'test_%')
            # 生成: username NOT LIKE %s

        """
        if self.db_type == DatabaseType.ORACLE:
            param_name = f"param_{self._param_counter}"
            self._param_counter += 1
            condition = f"{field} NOT LIKE :{param_name}"
            self.conditions.append(condition)
            cast(dict[str, JsonValue], self.parameters)[param_name] = pattern
        else:
            condition = f"{field} NOT LIKE %s"
            self.conditions.append(condition)
            cast(list[JsonValue], self.parameters).append(pattern)
        return self

    def build_where_clause(self) -> tuple[str, list[JsonValue]] | tuple[str, dict[str, JsonValue]]:
        """构建 WHERE 子句.

        将所有添加的条件组合成完整的 WHERE 子句,并返回对应的参数.

        Returns:
            根据数据库类型返回不同格式:
            - MySQL/PostgreSQL/SQL Server: (WHERE 子句字符串, 参数列表)
            - Oracle: (WHERE 子句字符串, 参数字典)
            如果没有条件,返回 ('1=1', []) 或 ('1=1', {}).

        Example:
            >>> builder.add_condition('status = %s', 'active')
            >>> where, params = builder.build_where_clause()
            >>> print(where)  # 'status = %s'
            >>> print(params)  # ['active']

        """
        if not self.conditions:
            if self.db_type == DatabaseType.ORACLE:
                return "1=1", cast(dict[str, JsonValue], {})
            return "1=1", cast(list[JsonValue], [])

        where_clause = " AND ".join(self.conditions)

        if self.db_type == DatabaseType.ORACLE:
            return where_clause, cast(dict[str, JsonValue], self.parameters.copy())
        return where_clause, cast(list[JsonValue], self.parameters.copy())

    def add_database_specific_condition(
        self,
        field: str,
        values: Sequence[str],
        patterns: Sequence[str],
    ) -> "SafeQueryBuilder":
        """添加数据库特定的过滤条件.

        根据数据库类型应用特定的过滤规则.例如 PostgreSQL 会保留 postgres 用户.

        Args:
            field: 字段名,例如 'username'.
            values: 排除的值列表,例如 ['admin', 'root'].
            patterns: 排除的模式列表,例如 ['test_%', '%_backup'].

        Returns:
            返回自身以支持链式调用.

        Example:
            >>> builder.add_database_specific_condition(
            ...     'username',
            ...     ['admin', 'root'],
            ...     ['test_%']
            ... )

        """
        if values:
            if self.db_type == DatabaseType.POSTGRESQL and "postgres" in values:
                filtered_values = [v for v in values if v != "postgres"]
                if filtered_values:
                    self.add_not_in_condition(field, filtered_values)
            else:
                self.add_not_in_condition(field, values)

        for pattern in patterns:
            if self.db_type == DatabaseType.POSTGRESQL and pattern == "pg_%":
                self.add_condition(f"({field} NOT LIKE %s OR {field} = %s)", pattern, "postgres")
            else:
                self.add_not_like_condition(field, pattern)

        return self

    def reset(self) -> "SafeQueryBuilder":
        """重置构建器.

        清空所有条件和参数,恢复到初始状态.

        Returns:
            返回自身以支持链式调用.

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
    db_type: str,
    username_field: str,
    filter_rules: Mapping[str, Mapping[str, Sequence[str]]],
) -> tuple[str, list[JsonValue]] | tuple[str, dict[str, JsonValue]]:
    """构建安全的过滤条件 - 统一入口函数.

    根据数据库类型和过滤规则构建安全的 WHERE 子句.

    Args:
        db_type: 数据库类型,可选值:'mysql'、'postgresql'、'sqlserver'、'oracle'.
        username_field: 用户名字段名,例如 'username' 或 'account_name'.
        filter_rules: 过滤规则字典,格式如下:
            {
                'mysql': {
                    'exclude_users': ['root', 'admin'],
                    'exclude_patterns': ['test_%']
                }
            }

    Returns:
        根据数据库类型返回不同格式:
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
