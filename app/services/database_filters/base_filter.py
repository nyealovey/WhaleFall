"""
泰摸鱼吧 - 数据库过滤规则基类
定义所有数据库过滤规则的通用接口和基础实现
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class BaseDatabaseFilter(ABC):
    """数据库过滤规则基类"""
    
    def __init__(self, config_data: Dict[str, Any] = None):
        self.db_type = self.get_database_type()
        self.config_data = config_data or {}
        self.exclude_users = self.get_exclude_users()
        self.exclude_patterns = self.get_exclude_patterns()
        self.exclude_roles = self.get_exclude_roles()
        self.include_only = self.get_include_only()
        self.custom_rules = self.get_custom_rules()
    
    @abstractmethod
    def get_database_type(self) -> str:
        """获取数据库类型"""
        pass
    
    def get_exclude_users(self) -> List[str]:
        """获取要排除的用户列表"""
        return self.config_data.get("exclude_users", [])
    
    def get_exclude_patterns(self) -> List[str]:
        """获取要排除的用户名模式列表"""
        return self.config_data.get("exclude_patterns", [])
    
    def get_exclude_roles(self) -> List[str]:
        """获取要排除的角色列表"""
        return self.config_data.get("exclude_roles", [])
    
    def get_include_only(self) -> bool:
        """是否只包含指定用户（默认False）"""
        return self.config_data.get("include_only", False)
    
    def get_custom_rules(self) -> List[Dict[str, Any]]:
        """获取自定义规则（默认空列表）"""
        return self.config_data.get("custom_rules", [])
    
    def should_include_user(self, username: str) -> bool:
        """
        判断是否应该包含指定用户
        
        Args:
            username: 用户名
            
        Returns:
            bool: True表示应该包含，False表示应该排除
        """
        # 检查排除用户列表
        if username in self.exclude_users:
            return False
        
        # 检查排除模式
        for pattern in self.exclude_patterns:
            if self._match_pattern(username, pattern):
                return False
        
        # 应用自定义规则
        for rule in self.custom_rules:
            if not self._apply_custom_rule(username, rule):
                return False
        
        return True
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """
        模式匹配（支持SQL LIKE语法）
        
        Args:
            text: 要匹配的文本
            pattern: SQL LIKE模式
            
        Returns:
            bool: 是否匹配
        """
        try:
            # 将SQL LIKE模式转换为正则表达式
            # % 匹配任意字符，_ 匹配单个字符
            regex_pattern = pattern.replace("%", ".*").replace("_", ".")
            # 添加行首和行尾锚点
            regex_pattern = f"^{regex_pattern}$"
            return bool(re.match(regex_pattern, text, re.IGNORECASE))
        except Exception:
            return False
    
    def _apply_custom_rule(self, username: str, rule: Dict[str, Any]) -> bool:
        """
        应用自定义规则
        
        Args:
            username: 用户名
            rule: 自定义规则
            
        Returns:
            bool: True表示通过规则，False表示被规则排除
        """
        # 默认实现：所有自定义规则都通过
        # 子类可以重写此方法来实现特定的自定义规则逻辑
        return True
    
    def build_where_clause(self, username_field: str) -> Tuple[str, List[Any]]:
        """
        构建WHERE子句
        
        Args:
            username_field: 用户名字段名
            
        Returns:
            Tuple[str, List[Any]]: WHERE子句和参数列表
        """
        conditions = []
        params = []
        
        # 处理排除用户
        if self.exclude_users:
            placeholders = ", ".join(["%s"] * len(self.exclude_users))
            conditions.append(f"{username_field} NOT IN ({placeholders})")
            params.extend(self.exclude_users)
        
        # 处理排除模式
        for pattern in self.exclude_patterns:
            conditions.append(f"{username_field} NOT LIKE %s")
            params.append(pattern)
        
        # 应用自定义规则
        for rule in self.custom_rules:
            custom_condition, custom_params = self._build_custom_condition(username_field, rule)
            if custom_condition:
                conditions.append(custom_condition)
                params.extend(custom_params)
        
        if conditions:
            where_clause = " AND ".join(conditions)
        else:
            where_clause = "1=1"  # 如果没有条件，返回恒真条件
        
        return where_clause, params
    
    def _build_custom_condition(self, username_field: str, rule: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        构建自定义规则的WHERE条件
        
        Args:
            username_field: 用户名字段名
            rule: 自定义规则
            
        Returns:
            Tuple[str, List[Any]]: 条件字符串和参数列表
        """
        # 默认实现：返回空条件
        # 子类可以重写此方法来实现特定的自定义规则条件
        return "", []
    
    def get_filter_info(self) -> Dict[str, Any]:
        """获取过滤规则信息"""
        return {
            "db_type": self.db_type,
            "exclude_users": self.exclude_users,
            "exclude_patterns": self.exclude_patterns,
            "exclude_roles": self.exclude_roles,
            "include_only": self.include_only,
            "custom_rules": self.custom_rules
        }
