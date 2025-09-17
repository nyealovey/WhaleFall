"""
泰摸鱼吧 - 安全查询构建器
提供安全的SQL查询构建功能，防止SQL注入攻击
支持MySQL、PostgreSQL、SQL Server、Oracle等多种数据库
"""

from typing import Any, Dict, List, Tuple, Union


class SafeQueryBuilder:
    """
    安全查询构建器 - 多数据库支持版
    
    支持的数据库类型：
    - MySQL: 使用 %s 占位符，返回 list 参数
    - PostgreSQL: 使用 %s 占位符，返回 list 参数  
    - SQL Server: 使用 %s 占位符，返回 list 参数
    - Oracle: 使用 :name 占位符，返回 dict 参数
    """

    def __init__(self, db_type: str = "mysql"):
        """
        初始化查询构建器
        
        Args:
            db_type: 数据库类型 ('mysql', 'postgresql', 'sqlserver', 'oracle')
        """
        self.db_type = db_type.lower()
        self.conditions: List[str] = []
        
        # 根据数据库类型选择参数存储方式
        if self.db_type == "oracle":
            self.parameters: Dict[str, Any] = {}
            self._param_counter = 0
        else:
            self.parameters: List[Any] = []

    def add_condition(self, condition: str, *params: Any) -> "SafeQueryBuilder":
        """
        添加查询条件
        
        Args:
            condition: SQL条件字符串，根据数据库类型使用不同占位符
            *params: 参数值
            
        Returns:
            SafeQueryBuilder: 返回自身以支持链式调用
        """
        if self.db_type == "oracle":
            # Oracle使用命名参数，需要转换占位符
            oracle_condition = condition
            param_dict = {}
            
            for i, param in enumerate(params):
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
        """
        生成数据库特定的占位符
        
        Args:
            count: 占位符数量
            
        Returns:
            str: 占位符字符串
        """
        if self.db_type == "oracle":
            placeholders = []
            for _ in range(count):
                param_name = f"param_{self._param_counter}"
                self._param_counter += 1
                placeholders.append(f":{param_name}")
            return ", ".join(placeholders)
        elif self.db_type == "sqlserver":
            # SQL Server使用?占位符
            return ", ".join(["?"] * count)
        else:
            # MySQL, PostgreSQL使用%s
            return ", ".join(["%s"] * count)

    def add_in_condition(self, field: str, values: List[str]) -> "SafeQueryBuilder":
        """
        添加IN条件
        
        Args:
            field: 字段名
            values: 值列表
            
        Returns:
            SafeQueryBuilder: 返回自身以支持链式调用
        """
        if values:
            if self.db_type == "oracle":
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

    def add_not_in_condition(self, field: str, values: List[str]) -> "SafeQueryBuilder":
        """
        添加NOT IN条件
        
        Args:
            field: 字段名
            values: 值列表
            
        Returns:
            SafeQueryBuilder: 返回自身以支持链式调用
        """
        if values:
            if self.db_type == "oracle":
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
        """
        添加LIKE条件
        
        Args:
            field: 字段名
            pattern: 模式字符串
            
        Returns:
            SafeQueryBuilder: 返回自身以支持链式调用
        """
        if self.db_type == "oracle":
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
        """
        添加NOT LIKE条件
        
        Args:
            field: 字段名
            pattern: 模式字符串
            
        Returns:
            SafeQueryBuilder: 返回自身以支持链式调用
        """
        if self.db_type == "oracle":
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

    def build_where_clause(self) -> Union[Tuple[str, List[Any]], Tuple[str, Dict[str, Any]]]:
        """
        构建WHERE子句
        
        Returns:
            Union[Tuple[str, List[Any]], Tuple[str, Dict[str, Any]]]: 
            - MySQL/PostgreSQL/SQL Server: (WHERE子句, 参数列表)
            - Oracle: (WHERE子句, 参数字典)
        """
        if not self.conditions:
            if self.db_type == "oracle":
                return "1=1", {}
            else:
                return "1=1", []

        where_clause = " AND ".join(self.conditions)
        
        if self.db_type == "oracle":
            return where_clause, self.parameters.copy()
        else:
            return where_clause, self.parameters.copy()

    def add_database_specific_condition(self, field: str, values: List[str], patterns: List[str], db_specific_rules: Dict[str, Any] = None) -> "SafeQueryBuilder":
        """
        添加数据库特定的过滤条件
        
        Args:
            field: 字段名
            values: 排除的值列表
            patterns: 排除的模式列表
            db_specific_rules: 数据库特定规则
            
        Returns:
            SafeQueryBuilder: 返回自身以支持链式调用
        """
        db_specific_rules = db_specific_rules or {}
        
        # 处理排除用户
        if values:
            # PostgreSQL特殊处理：保留postgres用户
            if self.db_type == "postgresql" and "postgres" in values:
                filtered_values = [v for v in values if v != "postgres"]
                if filtered_values:
                    self.add_not_in_condition(field, filtered_values)
            else:
                self.add_not_in_condition(field, values)
        
        # 处理排除模式
        for pattern in patterns:
            # PostgreSQL特殊处理：pg_%模式不排除postgres用户
            if self.db_type == "postgresql" and pattern == "pg_%":
                self.add_condition(f"({field} NOT LIKE %s OR {field} = %s)", pattern, "postgres")
            else:
                self.add_not_like_condition(field, pattern)
        
        return self
    
    def reset(self) -> "SafeQueryBuilder":
        """重置构建器"""
        self.conditions.clear()
        if self.db_type == "oracle":
            self.parameters.clear()
            self._param_counter = 0
        else:
            self.parameters.clear()
        return self


def build_safe_filter_conditions(
    db_type: str, username_field: str, filter_rules: Dict[str, Any]
) -> Union[Tuple[str, List[Any]], Tuple[str, Dict[str, Any]]]:
    """
    构建安全的过滤条件 - 统一入口函数
    
    Args:
        db_type: 数据库类型
        username_field: 用户名字段名
        filter_rules: 过滤规则
        
    Returns:
        Union[Tuple[str, List[Any]], Tuple[str, Dict[str, Any]]]: WHERE子句和参数
    """
    builder = SafeQueryBuilder(db_type)
    rules = filter_rules.get(db_type, {})
    
    exclude_users = rules.get("exclude_users", [])
    exclude_patterns = rules.get("exclude_patterns", [])
    
    # 使用统一的数据库特定条件构建方法
    builder.add_database_specific_condition(
        username_field, 
        exclude_users, 
        exclude_patterns
    )
    
    return builder.build_where_clause()


# 为了向后兼容，添加一个便捷函数返回list格式的参数
def build_safe_filter_conditions_list(
    db_type: str, username_field: str, filter_rules: Dict[str, Any]
) -> Tuple[str, List[Any]]:
    """
    构建安全的过滤条件 - 返回list格式参数（向后兼容）
    
    Args:
        db_type: 数据库类型
        username_field: 用户名字段名
        filter_rules: 过滤规则
        
    Returns:
        Tuple[str, List[Any]]: WHERE子句和参数列表
    """
    where_clause, params = build_safe_filter_conditions(db_type, username_field, filter_rules)
    
    # 如果是Oracle返回的dict，转换为list（虽然会丢失命名信息，但保持兼容性）
    if isinstance(params, dict):
        return where_clause, list(params.values())
    else:
        return where_clause, params
